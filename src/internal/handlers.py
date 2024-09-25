from abc import ABC, abstractmethod
from typing import Optional
import os
import random


class Handler(ABC):
    @abstractmethod
    def output(self, value: str) -> None:
        """Output to designated handler destination"""

    @abstractmethod
    def random(self) -> int:
        """Request randomness from handler"""


class LocalHandler(Handler):

    LOCAL_OUTPUT_ENV_VAR: str = "ANTITHESIS_SDK_LOCAL_OUTPUT"

    def __init__(self, file: str):
        abs_path = os.path.abspath(file)
        print(f'Assertion output will be sent to: "{abs_path}"\n')

        # Clear file
        open(abs_path, "w").close()

        self.file = file

    @staticmethod
    def get() -> Optional[LocalHandler]:
        file = os.getenv(LocalHandler.LOCAL_OUTPUT_ENV_VAR)
        if file is None:
            return None
        return LocalHandler(file)

    def output(self, value: str) -> None:
        with open(self.file, "a") as file:
            file.write(value)

    def random(self) -> int:
        return random.getrandbits(64)
