"""Lifecycle
The lifecycle module contains functions that inform the Antithesis 
environment that particular test phases or milestones have been 
reached.
"""

from typing import Mapping, Any
import json
from internal import dispatch_output, requires_antithesis_output

@requires_antithesis_output
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

@requires_antithesis_output
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
