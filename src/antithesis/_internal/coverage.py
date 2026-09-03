"""Consumes a pre-generated, version-independent AST-span edge table (see the
build-side generator) and drives coverage via ``sys.monitoring``.
"""

from __future__ import annotations

import dis
import json
import os
import sys
import weakref
from pathlib import PurePath
from typing import Dict, Iterator, List, Optional, Tuple

_Span = Tuple[int, int, int, int]

# `function`-column label descriptors written by the build-side generator
# (coverage_edges.write_table). Entry edges carry the co_qualname followed by
# ``(entry)``; branch arcs carry the enclosing-scope name followed by the arc
# descriptor. Kept in sync with coverage_edges.py.
_ENTRY_SUFFIX = " (method entry)"
_FALLTHROUGH_SUFFIX = " (branch fall-through)"
_JUMP_SUFFIX = " (branch jump)"

# The instrumentor appends this comment to each instrumented .py so a module's
# catalog identity travels with its source (copy-invariant), letting us resolve the
# catalog without inferring it from the launch path. Kept in sync with the build
# side (antithesis-instrumentor _internal.MODULE_MARKER_PREFIX).
_MODULE_MARKER_PREFIX = "# antithesis-module: "

# Lease-word packing, from instrumentation.h ("Coverage leases")
_LEASE_EPOCH_SHIFT = 40
_LEASE_GRANTED_SHIFT = 20
_LEASE_FIELD_MASK = 0xFFFFF
_LEASE_EPOCH_MASK = 0xFFFFFF


def _iter_sym_rows(sym_path: str) -> Iterator[Tuple[str, str, _Span, int]]:
    try:
        f = open(sym_path, "r", encoding="utf-8")
    except OSError:
        return
    with f:
        for line in f:
            if line.startswith("#"):
                continue  # `# key = value` preamble
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 7 or not parts[6].isdigit():
                continue  # column header / malformed
            try:
                span = (int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5]))
                addr = int(parts[6])
            except ValueError:
                continue
            yield parts[0], parts[1], span, addr


def _warn(message: str) -> None:
    print(message, file=sys.stderr)
    try:
        from antithesis._internal import dispatch_output

        dispatch_output(json.dumps({"antithesis_error": {"message": message}}))
    except Exception:
        pass

_ACTIVE: Optional["_Resolver"] = None

# Distinguishes "not yet resolved" from "resolved to not-ours (None)" in the
# per-code branch caches.
_UNRESOLVED = object()

_INSTRUMENTATION_MODULE: Optional[str] = None


def get_instrumentation_module() -> Optional[str]:
    """Module identity recorded by activate_module, or None if coverage has not been
    activated in this process."""
    return _INSTRUMENTATION_MODULE


def resolve_module_from_marker(source_file: str) -> Optional[str]:
    """The module named by the `# antithesis-module: <name>` marker the instrumentor
    appends to each instrumented .py. Read statically (never executes the file), so it
    works before/while the module runs and is unaffected by where the file now lives —
    the identity travels with the source. Returns the module name, or None if absent.

    Preferred over the marker-less importability vote (assertions._get_instrumentation_folder):
    it resolves the catalog even when the code was copied to a path different from
    where it was cataloged."""
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    module: Optional[str] = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(_MODULE_MARKER_PREFIX):
            module = stripped[len(_MODULE_MARKER_PREFIX):].strip()  # last one wins
    return module or None


def _contains(outer: _Span, inner: _Span) -> bool:
    return (outer[0], outer[1]) <= (inner[0], inner[1]) and (inner[2], inner[3]) <= (
        outer[2],
        outer[3],
    )


class _Resolver:
    def __init__(self, lib, sym_path: str):
        self._lib = lib
        # relative posix path -> list of (span, addr_F, addr_T)  [branch edges]
        self._by_relpath: Dict[str, List[Tuple[_Span, Optional[int], Optional[int]]]] = {}
        # relative posix path -> {(co_firstlineno, co_qualname) -> addr}  [method entry edges]
        self._by_relpath_start: Dict[str, Dict[Tuple[int, str], int]] = {}
        # basename -> relpaths ending with it (suffix-match index)
        self._by_basename: Dict[str, List[str]] = {}
        edge_count = self._parse(sym_path)

        # A zero-edge table has nothing to register (register() declines below),
        # so skip init_coverage_module rather than announce an empty module.
        if edge_count > 0:
            self._module_offset = int(
                lib.init_coverage_module(
                    edge_count, os.path.basename(sym_path).encode("ascii")
                )
            )
        else:
            self._module_offset = 0

        self._leases: Optional[List[int]] = None
        self._notify_v2 = None
        self._lease_generation = None
        if edge_count > 0:
            try:
                self._notify_v2 = lib.notify_coverage_v2
                self._lease_generation = lib.coverage_lease_generation_addr()
                # 1-based edge addresses: index edge_count is reachable.
                self._leases = [0] * (edge_count + 1)
            except AttributeError:
                self._notify_v2 = None
                self._lease_generation = None
        self._retired: set[int] = set()
        # Keyed by the code object itself, NOT id(code), as ids can be recycled
        #
        # NB: Code objects are only weakly referenceable on CPython 3.12+. If we add
        # settrace support in order to instrument code runner on older Python
        # interpreters, this will need to be reworked
        self._armed: "weakref.WeakSet" = weakref.WeakSet()
        self._code_cache: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
        # code -> {offset: (fall-through, F addr, T addr) | None}, resolved
        # lazily per branch location (see _branch).
        self._branch_cache: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()
        # co_filename -> resolved relpath key (or None if the file isn't ours)
        self._resolve_cache: Dict[str, Optional[str]] = {}
        self._tool_id: Optional[int] = None
        self._branch_mask = 0
        self._arm_mask = 0
        self._split = False
        self.edge_count = edge_count

    def _parse(self, sym_path: str) -> int:
        max_addr = -1
        grouped: Dict[Tuple[str, _Span], Dict[str, int]] = {}
        for relpath, func, span, addr_i in _iter_sym_rows(sym_path):
            if addr_i > max_addr:
                max_addr = addr_i
            if func.endswith(_ENTRY_SUFFIX):
                # Method-entry edge, keyed by (co_firstlineno, co_qualname). The
                # qualname (label minus the descriptor) is the runtime match key.
                qual = func[: -len(_ENTRY_SUFFIX)]
                self._by_relpath_start.setdefault(relpath, {})[(span[0], qual)] = addr_i
            elif func.endswith(_JUMP_SUFFIX):
                grouped.setdefault((relpath, span), {})["T"] = addr_i
            elif func.endswith(_FALLTHROUGH_SUFFIX):
                grouped.setdefault((relpath, span), {})["F"] = addr_i
            else:
                return 0 # unrecognized label -> the file was corrupted or is otherwise not a valid edge table
        for (relpath, span), arcs in grouped.items():
            self._by_relpath.setdefault(relpath, []).append(
                (span, arcs.get("F"), arcs.get("T"))
            )
        # Suffix index spans both edge classes: a file may have entry edges only.
        for relpath in set(self._by_relpath) | set(self._by_relpath_start):
            self._by_basename.setdefault(relpath.rsplit("/", 1)[-1], []).append(relpath)

        return max(max_addr, 0)

    def register(self) -> bool:
        if self.edge_count <= 0:
            return False
        mon = sys.monitoring
        tid = mon.COVERAGE_ID
        try:
            mon.use_tool_id(tid, "antithesis-coverage")
        except ValueError:
            return False
        self._tool_id = tid
        ev = mon.events
        el = getattr(ev, "BRANCH_LEFT", None)
        if el is not None:
            # 3.14 splits BRANCH into BRANCH_LEFT/BRANCH_RIGHT
            self._split = True
            mon.register_callback(tid, el, self._on_branch_left)
            self._branch_mask |= el

            er = getattr(ev, "BRANCH_RIGHT", None)
            if er is not None:
                mon.register_callback(tid, er, self._on_branch_right)
                self._branch_mask |= er
        else:
            # 3.12/3.13: one BRANCH event; the arc is derived from the destination.
            self._split = False
            eb = getattr(ev, "BRANCH", None)
            if eb is not None:
                mon.register_callback(tid, eb, self._on_branch_combined)
                self._branch_mask |= eb
        self._arm_mask = self._branch_mask
        mon.register_callback(tid, ev.PY_START, self._on_py_start)
        mon.set_events(tid, ev.PY_START)
        return True

    def unregister(self) -> None:
        if self._tool_id is None:
            return
        sys.monitoring.set_events(self._tool_id, 0)
        sys.monitoring.free_tool_id(self._tool_id)
        self._tool_id = None

    def _resolve_key(self, co_filename: str) -> Optional[str]:
        # Map a runtime co_filename to a table relpath key by longest-suffix match
        if co_filename in self._resolve_cache:
            return self._resolve_cache[co_filename]
        try:
            norm = PurePath(os.path.realpath(co_filename)).as_posix()
        except OSError:
            norm = PurePath(co_filename).as_posix()
        base = norm.rsplit("/", 1)[-1]
        best: Optional[str] = None
        for rel in self._by_basename.get(base, ()):
            if norm == rel or norm.endswith("/" + rel):
                if best is None or len(rel) > len(best):
                    best = rel  # most specific suffix wins
        self._resolve_cache[co_filename] = best
        return best

    def _code_map(self, code) -> Dict[int, Tuple[int, Optional[_Span]]]:
        m = self._code_cache.get(code)
        if m is None:
            m = {}
            instrs = list(dis.get_instructions(code))
            for i, ins in enumerate(instrs):
                ft = instrs[i + 1].offset if i + 1 < len(instrs) else -1
                p = ins.positions
                if p and p.lineno is not None:
                    span = (
                        p.lineno,
                        (p.col_offset or 0) + 1,
                        p.end_lineno or p.lineno,
                        (p.end_col_offset or 0) + 1,
                    )
                else:
                    span = None
                m[ins.offset] = (ft, span)
            self._code_cache[code] = m
        return m

    def _match(
        self, relkey: str, span: _Span
    ) -> Optional[Tuple[_Span, Optional[int], Optional[int]]]:
        cands = self._by_relpath.get(relkey)
        if not cands:
            return None
        best = None
        best_key = None
        for sp, aF, aT in cands:
            if _contains(sp, span):
                key = (sp[0], sp[1], -sp[2], -sp[3])  # innermost: latest start, earliest end
                if best_key is None or key > best_key:
                    best_key, best = key, (sp, aF, aT)
        return best

    def _notify(self, addr: Optional[int]) -> None:
        if addr is None:
            return
        leases = self._leases
        if leases is None:
            # v1 library: cache the "never call again" return.
            if addr in self._retired:
                return
            if not self._lib.notify_coverage(addr + self._module_offset):
                self._retired.add(addr)
            return
        # Per-edge lease fast path: if the cached lease's epoch is current
        # and `remaining` is nonzero, count the hit locally; otherwise call.
        word = leases[addr]
        remaining = word & _LEASE_FIELD_MASK
        if remaining != 0 and (word >> _LEASE_EPOCH_SHIFT) & _LEASE_EPOCH_MASK == (
            self._lease_generation[0] & _LEASE_EPOCH_MASK
        ):
            leases[addr] = word - 1
            return
        granted = (word >> _LEASE_GRANTED_SHIFT) & _LEASE_FIELD_MASK
        leases[addr] = self._notify_v2(
            addr + self._module_offset, granted - remaining
        )

    # -- callbacks ---------------------------------------------------------
    def _on_py_start(self, code, _off):
        DIS = sys.monitoring.DISABLE
        relkey = self._resolve_key(code.co_filename)
        if relkey is None:
            return DIS  # not part of the program -> retire PY_START for this code
        if code not in self._armed:
            self._armed.add(code)
            sys.monitoring.set_local_events(self._tool_id, code, self._arm_mask)
        # Method-entry edge, keyed by (co_firstlineno, co_qualname). Keying on the
        # qualname rejects compiler scopes that share a co_firstlineno with a real
        # def -- PEP 695 `<generic parameters of ...>`, PEP 649 `__annotate__`, a
        # generator expression -- so reification/annotation never counts as a call.
        addr = self._by_relpath_start.get(relkey, {}).get(
            (code.co_firstlineno, code.co_qualname)
        )
        if addr is None:
            return DIS  # armed; no entry edge for this code object
        self._notify(addr)
        # Keep PY_START live while the edge is unretired so EPS / pause-injection
        # mode reports every entry; retire it once notify_coverage has stopped
        # wanting it (see-edges-once mode -> fire once, then DISABLE).
        return DIS if addr in self._retired else None

    # In the combined (3.12/3.13) regime one BRANCH callback fires and the arc is
    # derived from the destination; in the split (3.14) regime the arc is the
    # event identity, since dest==fall-through no longer holds (3.14 makes both
    # arcs explicit jump targets, so neither equals the next-instruction offset).
    def _on_branch_combined(self, code, off, dest):
        return self._branch(code, off, dest, arc_left=None)

    def _on_branch_left(self, code, off, _dest):
        return self._branch(code, off, _dest, arc_left=True)

    def _on_branch_right(self, code, off, _dest):
        return self._branch(code, off, _dest, arc_left=False)

    def _branch(self, code, off, dest, arc_left):
        DIS = sys.monitoring.DISABLE
        per_code = self._branch_cache.get(code)
        if per_code is None:
            per_code = {}
            self._branch_cache[code] = per_code
        entry = per_code.get(off, _UNRESOLVED)
        if entry is _UNRESOLVED:
            entry = self._resolve_branch(code, off)
            per_code[off] = entry
        if entry is None:
            return DIS
        ft, aF, aT = entry
        if aF is not None and aT is not None:
            if arc_left is None:  # combined: fall-through arc vs jump arc
                addr = aF if dest == ft else aT
            else:  # split: BRANCH_LEFT -> F arc, BRANCH_RIGHT -> T arc
                addr = aF if arc_left else aT
        else:  # coarsened single edge (both arcs share one address)
            addr = aF if aF is not None else aT
            aF = aT = addr
        # _notify's lease fast path, inlined for performance reasons.
        leases = self._leases
        if leases is not None:
            word = leases[addr]
            if (word & 0xFFFFF) != 0 and (word >> 40) & 0xFFFFFF == (
                self._lease_generation[0] & 0xFFFFFF
            ):
                leases[addr] = word - 1
            else:
                self._notify(addr)
            return None  # leases: never disable — see _notify
        self._notify(addr)
        done = (aF in self._retired) and (aT in self._retired)
        if self._split:
            # Split arcs retire independently, so disable this arc's location alone.
            return DIS if (addr in self._retired) else None
        return DIS if done else None

    def _resolve_branch(self, code, off):
        """(fall-through offset, F addr, T addr) for a branch location, or
        None if it is not one of ours."""
        relkey = self._resolve_key(code.co_filename)
        if relkey is None:
            return None
        entry = self._code_map(code).get(off)
        if entry is None:
            return None
        ft, span = entry
        if span is None:
            return None
        m = self._match(relkey, span)
        if m is None:
            return None
        _sp, aF, aT = m
        return (ft, aF, aT)


_OUTPUT_DIR_ENV = "ANTITHESIS_OUTPUT_DIR"


def _in_antithesis() -> bool:
    return os.getenv(_OUTPUT_DIR_ENV) is not None


def activate(sym_path: str, handler=None) -> Optional[_Resolver]:
    """Register coverage from a pre-generated .sym.tsv. Idempotent; best-effort.

    A no-op (returns None) unless running under Antithesis, on Python 3.12+, 
    with a libvoidstar-backed handler."""
    global _ACTIVE
    if _ACTIVE is not None:
        return _ACTIVE
    if not _in_antithesis():
        return None
    if sys.version_info < (3, 12):
        return None
    if handler is None:
        try:
            import antithesis._internal as _internal

            handler = getattr(_internal, "_HANDLER", None)
        except Exception:
            handler = None
    lib = getattr(handler, "_lib", None)
    if lib is None:  # Local/Noop handler or libvoidstar absent -> no coverage
        return None
    try:
        resolver = _Resolver(lib, sym_path)
        if resolver.register():
            _ACTIVE = resolver
            return resolver
    except Exception as exc:  # pragma: no cover - never break startup
        _warn(f"Antithesis coverage skipped: {exc!r}")
    return None


_CATALOG_ENV = "ANTITHESIS_ASSERTION_CATALOG"


def _resolve_sym_path(module_name: str) -> Optional[str]:
    # An absolute path passed directly (explicit override / tests).
    if os.path.isabs(module_name) and os.path.isfile(module_name):
        return module_name
    sym_name = f"{module_name}.sym.tsv"
    catalog = os.getenv(_CATALOG_ENV)
    if catalog:
        cand = os.path.join(catalog, module_name, sym_name)
        if os.path.isfile(cand):
            return cand
    # Fallbacks: the module dir (or its parent) present on sys.path.
    for root in sys.path:
        for cand in (
            os.path.join(root, module_name, sym_name),
            os.path.join(root, sym_name),
        ):
            if os.path.isfile(cand):
                return cand
    return None


def activate_module(module_name: str) -> None:
    global _INSTRUMENTATION_MODULE
    _INSTRUMENTATION_MODULE = module_name
    try:
        sym_path = _resolve_sym_path(module_name)
        if sym_path is not None:
            activate(sym_path)
    except Exception as exc:  # pragma: no cover
        _warn(f"Antithesis coverage activation skipped: {exc!r}")
