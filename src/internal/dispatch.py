"""Dispatch
The dispatch module contains functions that proxy 
requests for JSON output and random integer generation
from the active handler.
"""
# from internal import _HANDLER
#
# def dispatch_output(json: str):
#     """dispatch_output forwards the provided string
#     to the active HANDLER.  There is no validation that
#     the forwarded string is in valid JSON format.
#
#     Args:
#         json (str): String that will be forwarded to
#             the active handler.
#     """
#     return _HANDLER.output(json)
#
#
# def dispatch_random() -> int:
#     """dispatch_random requests a random 64-bit
#            integer from the active handler.
#
#     Returns:
#         int: A random 64 bit int
#     """
#     return _HANDLER.random()
