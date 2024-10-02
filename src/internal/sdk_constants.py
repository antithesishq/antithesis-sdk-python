"""SDK Constants
Contains constants and version info for the language, SDK, and protocol
"""

import importlib.metadata

ANTITHESIS_PROTOCOL_VERSION: str = "1.0.0"
ANTITHESIS_SDK_VERSION: str = importlib.metadata.version("antithesis-sdk")
