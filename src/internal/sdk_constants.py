"""SDK Constants
Contains constants and version info for the language, SDK, and protocol
"""

import importlib.metadata
import json
import sys
from internal import dispatch_output

ANTITHESIS_PROTOCOL_VERSION: str = "1.0.0"
ANTITHESIS_SDK_VERSION: str = importlib.metadata.version("antithesis-sdk")
