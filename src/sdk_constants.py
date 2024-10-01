"""SDK Constants
Contains constants and version info for the language, SDK, and protocol
"""

import importlib.metadata
import json
import sys
from internal import dispatch_output

ANTITHESIS_PROTOCOL_VERSION = "1.0.0"
ANTITHESIS_SDK_VERSION = importlib.metadata.version("antithesis-sdk")


def emit_version_message():
    """Emits the version info for this SDK"""
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
    dispatch_output(json.dumps(wrapped_version, indent=2))
