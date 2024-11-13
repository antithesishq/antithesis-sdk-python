"""Lifecycle
The lifecycle module contains functions that inform the Antithesis
environment that particular test phases or milestones have been
reached. Both functions take the parameter details: Optional
additional information provided by the user to add context for
assertion failures. 
The information that is logged will appear in the logs section 
of a [triage report](https://antithesis.com/docs/reports/triage/). 
Normally the values passed to details are evaluated at runtime.
"""

from typing import Mapping, Any
import json
import sys
from antithesis_sdk._internal import dispatch_output


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


def send_event(event_name: str, details: Mapping[str, Any]) -> None:
    """send_event indicates to Antithesis that a certain event
    has been reached. It provides more information about the 
    ordering of events during Antithesis test runs.

    Args:
        event_name (str): The top-level name to associate with the event
        details (Mapping[str, Any]): Additional details that are
            associated with the event
    """
    wrapped_event = {event_name: details}
    dispatch_output(json.dumps(wrapped_event, indent=2))


def _cmd_event():
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


def _cmd_setup():
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
