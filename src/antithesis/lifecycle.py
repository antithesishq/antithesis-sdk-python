""" This module contains functions that inform the Antithesis
environment that particular test phases or milestones have been
reached. Both functions take the parameter `details`: Optional
additional information provided by the user to add context for
assertion failures. 
The information that is logged will appear in the logs section 
of a [triage report](https://antithesis.com/docs/reports/). 
Normally the values passed to `details` are evaluated at runtime.
"""

from typing import Mapping, Any
import json
from antithesis._internal import dispatch_output


def setup_complete(details: Mapping[str, Any]) -> None:
    """setup_complete indicates to Antithesis that setup has completed.
    Call this function when your system and workload are fully
    initialized. After this function is called, Antithesis will
    take a snapshot of your system and begin
    [injecting faults](https://antithesis.com/docs/applications/reliability/fault_injection/).

    Args:
        details (Mapping[str, Any]): Additional details that are
            associated with the system and workload under test.
    """
    the_dict = {"status": "complete", "details": details}
    wrapped_setup = {"antithesis_setup": the_dict}
    dispatch_output(json.dumps(wrapped_setup))


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
    dispatch_output(json.dumps(wrapped_event))
