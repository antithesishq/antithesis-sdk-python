""" This module contains functions that inform the Antithesis
environment that particular test phases or milestones have been
reached. Both functions take the parameter `details`: Optional
additional information provided by the user to add context for
assertion failures. 
The information that is logged will appear in the logs section 
of a [triage report](https://antithesis.com/docs/reports/). 
Argument expressions are evaluated on every call. Omitted or `None` details
are absent from setup records and become `{}` for events. Explicit empty mappings
are preserved; other values are wrapped under `value`. Serialization failures
produce `antithesis_error` with the setup/event context and the original record
with no details (or `{}` for an event).
"""

from typing import Mapping, Any, Optional, Dict
from antithesis._internal import dispatch_output
from antithesis._details import SerializationFailure, details_object, dispatch_with_details


def setup_complete(details: Optional[Mapping[str, Any]] = None) -> None:
    """setup_complete indicates to Antithesis that setup has completed.
    Call this function when your system and workload are fully
    initialized. After this function is called, Antithesis will
    take a snapshot of your system and begin
    [injecting faults](https://antithesis.com/docs/environment/fault_injection/).

    Args:
        details (Optional[Mapping[str, Any]]): Additional details that are
            associated with the system and workload under test.
    """
    the_dict: Dict[str, Any] = {"status": "complete"}
    if details is not None:
        the_dict["details"] = details_object(details)
    wrapped_setup = {"antithesis_setup": the_dict}
    dispatch_with_details(
        wrapped_setup, the_dict, "details", "setup_complete", dispatch_output,
    )


def send_event(event_name: str, details: Optional[Mapping[str, Any]] = None) -> None:
    """send_event indicates to Antithesis that a certain event
    has been reached. It provides more information about the
    ordering of events during Antithesis test runs.

    Args:
        event_name (str): The top-level name to associate with the event
        details (Optional[Mapping[str, Any]]): Additional details that are
            associated with the event
    """
    wrapped_event = {event_name: {} if details is None else details_object(details)}
    dispatch_with_details(
        wrapped_event, wrapped_event, event_name, event_name, dispatch_output,
        on_error=SerializationFailure.EMPTY_DETAILS,
    )
