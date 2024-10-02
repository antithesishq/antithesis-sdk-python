from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
import os
import random

import cffi

LOCAL_OUTPUT_ENV_VAR: str = "ANTITHESIS_SDK_LOCAL_OUTPUT"
VOIDSTAR_PATH = "/usr/lib/libvoidstar.so"

class Handler(ABC):
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

    def __init__(self, file: str):
        abs_path = os.path.abspath(file)
        print(f'Assertion output will be sent to: "{abs_path}"\n')
        self.file = file

    @staticmethod
    def get() -> Optional[LocalHandler]:
        file = os.getenv(LOCAL_OUTPUT_ENV_VAR)
        if file is None:
            return None
        return LocalHandler(file)

    def output(self, value: str) -> None:
        with open(self.file, "a") as file:
            file.write(value)

    def random(self) -> int:
        return random.getrandbits(64)
    
    @property
    def handles_output(self) -> bool:
        return True 


class NoopHandler(Handler):
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

CDEF_VOIDSTAR='''\
uint64_t fuzz_get_random();
void fuzz_json_data(const char* message, size_t length);
void fuzz_flush();
size_t init_coverage_module(size_t edge_count, const char* symbol_file_name);
bool notify_coverage(size_t edge_plus_module);
'''

class VoidstarHandler(Handler):
    def __init__(self):
        self._ffi = cffi.FFI()
        self._ffi.cdef(CDEF_VOIDSTAR)
        self._lib = None
        try:
            self._lib = self._ffi.dlopen(VOIDSTAR_PATH)
        except OSError:
            self._lib = None

    @staticmethod
    def get() -> Optional[VoidstarHandler]:
        vsh = VoidstarHandler()
        if vsh._lib is None:
            return None
        return vsh

    def output(self, value: str) -> None:
        self._lib.fuzz_json_data(value.encode('ascii'), len(value))
        self._lib.fuzz_flush()

    def random(self) -> int:
        return self._lib.fuzz_get_random()
    
    @property
    def handles_output(self) -> bool:
        return self._lib is not None 
