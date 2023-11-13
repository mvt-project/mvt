import json


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle non-standard types.

    Some modules are storing non-UTF-8 bytes in their results dictionaries.
    This causes exceptions when the results are being encoded as JSON.

    Of course this means that when MVT is run via `check-iocs` with existing
    results, the encoded version will be loaded back into the dictionary.
    Modules should ensure they encode anything that needs to be compared
    against an indicator in a JSON-friendly type.
    """

    def default(self, o):
        if isinstance(o, bytes):
            # If it's utf-8, try and use that first
            try:
                return o.decode("utf-8")
            except UnicodeError:
                # Otherwise use a hex representation for any byte type
                return "0x" + o.hex()

        # For all other types try to use the string representation.
        return str(o)
