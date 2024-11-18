"""SDK Constants
Contains constants and version info for the language, SDK, and protocol
"""

import importlib.metadata

ANTITHESIS_PROTOCOL_VERSION: str = "1.0.0"
ANTITHESIS_SDK_VERSION: str = importlib.metadata.version("antithesis")

LOCAL_OUTPUT_ENV_VAR: str = "ANTITHESIS_SDK_LOCAL_OUTPUT"
ASSERTION_CATALOG_ENV_VAR: str = "ANTITHESIS_ASSERTION_CATALOG"

ASSERTION_CATALOG_NAME: str = "assertion_catalog"
COVERAGE_MODULE_LIST: str = "coverage_modules"
