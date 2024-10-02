"""Lifecycle
The lifecycle module contains functions that inform the Antithesis 
environment that particular test phases or milestones have been 
reached.
"""

from typing import Mapping, Any
import json
import sys
from internal import (
    dispatch_output, 
    requires_antithesis_output,
    ANTITHESIS_SDK_VERSION,
    ANTITHESIS_PROTOCOL_VERSION,
)


# @requires_antithesis_output
def setup_complete(details: Mapping[str, Any]) -> None:
    """setup_complete indicates to Antithesis that setup has completed.
    Call this function when your system and workload are fully
    initialized. After this function is called, Antithesis will
    take a snapshot of your system and begin [injecting faults].

    Args:
        details (Mapping[str, Any]): Additional details that are
            associated with the system and workload under test.
    """
    the_dict = {"status": "complete", "details": details}
    wrapped_setup = {"antithesis_setup": the_dict}
    dispatch_output(json.dumps(wrapped_setup, indent=2))

# @requires_antithesis_output
def send_event(event_name: str, details: Mapping[str, Any]) -> None:
    """send_event indicates to Antithesis that a certain event
    has been reached. It provides greater information about the
    ordering of events during the course of testing in Antithesis.

    Args:
        event_name (str): The top-level name to associate with the event
        details (Mapping[str, Any]): Additional details that are
            associated with the event
    """
    wrapped_event = {event_name: details}
    dispatch_output(json.dumps(wrapped_event, indent=2))

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

# ----------------------------------------------------------------------
# For project.scripts support
# ----------------------------------------------------------------------
def cmd_version():
    """Smoke-test for emit_version_message().

    Examples:
        Should be executed from a devshell

        >>> $ versionx
        FUZZ_JSON_DATA(207 bytes): {
          "antithesis_sdk": {
            "language": {
              "name": "Python",
              "version": "3.12.5 (main, Aug  6 2024, 19:08:49) [GCC 13.3.0]"
            },
            "sdk_version": "0.1.2",
            "protocol_version": "1.0.0"
          }
        }
        FLUSH
    """
    emit_version_message()

def cmd_event():
    """Smoke-test for send_event().

    Examples:
        Should be executed from a devshell

        >>> $ eventx tree leaf_color green 
        FUZZ_JSON_DATA(45 bytes): {
          "tree": {
            "leaf_color": "green"
          }
        }
        FLUSH
    """
    name = "tree"
    tag = "leaf_color"
    val = "green"
    lx = len(sys.argv)
    if lx > 1:
        name = sys.argv[1]
    if lx > 2:
        tag = sys.argv[2]
    if lx > 3:
        val = sys.argv[3]
    send_event(name, {tag: val})

def cmd_setup():
    """Smoke-test for send_event().

    Examples:
        Should be executed from a devshell

        >>> $ eventx tree leaf_color green 
        FUZZ_JSON_DATA(77 bytes): {
          "antithesis_setup": {
            "status": "complete",
            "details": null
          }
        }
        FLUSH
    """
    setup_complete(None)
