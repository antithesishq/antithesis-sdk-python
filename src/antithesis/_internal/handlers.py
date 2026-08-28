"""Handlers
Provides implementations for the Voidstar, Local,
and No-Op handlers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import ctypes
from io import FileIO
import json
import os
import random
import sys
from typing import Optional

from .sdk_constants import (
    LOCAL_OUTPUT_ENV_VAR,
    ANTITHESIS_SDK_VERSION,
    ANTITHESIS_PROTOCOL_VERSION,
)

_VOIDSTAR_PATH = "/usr/lib/libvoidstar.so"


class Handler(ABC):
    """The common base class for all handlers.
    Handlers must provide a static constructor
    as well as methods for returning random integers,
    and forwarding JSON data.  To minimize unnecessary
    processing, handlers are also required to indicate
    if they are able to forward JSON data, or not.
    """

    @abstractmethod
    def output(self, value: str) -> None:
        """Output to designated handler destination"""

    @abstractmethod
    def random(self) -> int:
        """Request randomness from handler"""

    @staticmethod
    @abstractmethod
    def get() -> Optional[Handler]:
        """Static method to retrieve an instance of the handler"""

    @property
    @abstractmethod
    def handles_output(self) -> bool:
        """Indicates whether this handler is capable of handling output"""


class LocalHandler(Handler):
    """The LocalHandler conforms to the Handler 'interface' and
    can return random integers and write JSON data to a local file,
    if a path to a local file has been provided (via the environment
    var: ANTITHESIS_SDK_LOCAL_OUTPUT)
    """

    def __init__(self, filename: str, file: FileIO):
        abs_path = os.path.abspath(filename)
        print(f'Assertion output will be sent to: "{abs_path}"\n')
        self.file = file

    @staticmethod
    def get() -> Optional[LocalHandler]:
        filename = os.getenv(LOCAL_OUTPUT_ENV_VAR)
        if filename is None:
            return None
        try:
            # Unbuffered binary append so that concurrent writers do not trample
            # each other and each line is a single, self-contained syscall
            # pylint: disable-next=consider-using-with
            file = open(filename, "ab", buffering=0)
        except IOError:
            return None
        return LocalHandler(filename, file)

    def output(self, value: str) -> None:
        self.file.write(value.encode("utf-8") + b"\n")

    def random(self) -> int:
        return random.getrandbits(64)

    @property
    def handles_output(self) -> bool:
        return True


class NoopHandler(Handler):
    """The NoopHandler conforms to the Handler 'interface' and
    performs as little work as possible.
    """

    @staticmethod
    def get() -> NoopHandler:
        return NoopHandler()

    def output(self, value: str) -> None:
        return

    def random(self) -> int:
        return random.getrandbits(64)

    @property
    def handles_output(self) -> bool:
        return False


def _load_voidstar(path):
    """Symbols the loaded library lacks (a pre-lease build without the v2
    coverage entry points) are simply left untyped; accessing them raises
    AttributeError, which is how coverage negotiates the ABI version."""
    lib = ctypes.CDLL(path)

    def fx(name, argtypes, restype=None):
        try:
            f = getattr(lib, name)
        except AttributeError:
            return
        f.argtypes = argtypes
        f.restype = restype

    fx("fuzz_get_random", [], ctypes.c_uint64)
    fx("fuzz_json_data", [ctypes.c_char_p, ctypes.c_size_t])
    fx("fuzz_flush", [])
    fx("init_coverage_module", [ctypes.c_size_t, ctypes.c_char_p], ctypes.c_size_t)
    fx("notify_coverage", [ctypes.c_size_t], ctypes.c_bool)
    fx(
        "notify_coverage_v2",
        [ctypes.c_size_t, ctypes.c_uint64],
        ctypes.c_uint64,
    )
    fx("coverage_lease_generation_addr", [], ctypes.POINTER(ctypes.c_uint64))
    return lib


class VoidstarHandler(Handler):
    """The VoidstarHandler conforms to the Handler 'interface' and
    uses libvoidstar to obtain and return random integers, and forwards
    JSON data to the Antithesis fuzzer.
    """

    def __init__(self):
        try:
            self._lib = _load_voidstar(_VOIDSTAR_PATH)
        except OSError:
            self._lib = None

    @staticmethod
    def get() -> Optional[VoidstarHandler]:
        vsh = VoidstarHandler()
        if not vsh.handles_output:
            return None
        return vsh

    def output(self, value: str) -> None:
        encoded = value.encode("utf-8")
        self._lib.fuzz_json_data(encoded, len(encoded))
        self._lib.fuzz_flush()

    def random(self) -> int:
        return self._lib.fuzz_get_random()

    @property
    def handles_output(self) -> bool:
        return self._lib is not None


def _setup_handler() -> Handler:
    return VoidstarHandler.get() or LocalHandler.get() or NoopHandler.get()


def _version_message() -> str:
    """Format the version info for this SDK"""
    language_info = {
        "name": "Python",
        "version": sys.version,
    }

    version_info = {
        "language": language_info,
        "sdk_version": ANTITHESIS_SDK_VERSION,
        "protocol_version": ANTITHESIS_PROTOCOL_VERSION,
    }
    wrapped_version = {"antithesis_sdk": version_info}
    return json.dumps(wrapped_version)
