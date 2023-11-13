import json
from datetime import datetime

from mvt.common.encoding import CustomJSONEncoder


class TestCustomJSONEncoder:
    def test__normal_input(self):
        assert json.dumps({"a": "b"}, cls=CustomJSONEncoder) == '{"a": "b"}'

    def test__datetime_object(self):
        assert (
            json.dumps(
                {"timestamp": datetime(2023, 11, 13, 12, 21, 49, 727467)},
                cls=CustomJSONEncoder,
            )
            == '{"timestamp": "2023-11-13 12:21:49.727467"}'
        )

    def test__bytes_non_utf_8(self):
        assert (
            json.dumps({"identifier": b"\xa8\xa9"}, cls=CustomJSONEncoder)
            == '{"identifier": "0xa8a9"}'
        )

    def test__bytes_valid_utf_8(self):
        assert (
            json.dumps({"name": "家".encode()}, cls=CustomJSONEncoder)
            == '{"name": "\\u5bb6"}'
        )
