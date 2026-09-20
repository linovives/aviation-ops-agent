import json
from data_pipeline import aerodatabox_client as client


class FakeResponse:
    def __init__(self, status_code, body=None, text=""):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._body = body
        self.text = text if body is None else json.dumps(body)

    def json(self):
        if self._body is None:
            raise json.JSONDecodeError("Expecting value", self.text or "", 0)
        return self._body


def test_get_airport_flights_returns_json_on_200(monkeypatch):
    payload = {"departures": [{"number": "LO 432"}], "arrivals": []}
    monkeypatch.setattr(client.requests, "get", lambda *a, **k: FakeResponse(200, payload))
    result = client.get_airport_flights("icao", "LEMD", "2026-09-25T06:00", "2026-09-25T12:00")
    assert result == payload


def test_get_airport_flights_handles_204_no_content(monkeypatch):
    monkeypatch.setattr(client.requests, "get", lambda *a, **k: FakeResponse(204, body=None, text=""))
    result = client.get_airport_flights("icao", "ZZZZ", "2026-09-25T06:00", "2026-09-25T12:00")
    assert result == {"departures": [], "arrivals": []}


def test_get_airport_flights_handles_400_with_json_message(monkeypatch):
    body = {"message": "The requested period of time be positive and must not be more than 12 hours in duration"}
    monkeypatch.setattr(client.requests, "get", lambda *a, **k: FakeResponse(400, body))
    result = client.get_airport_flights("icao", "LEMD", "2026-09-25T00:00", "2026-09-26T00:00")
    assert result == {"error": body["message"]}


def test_get_airport_flights_handles_404_empty_body(monkeypatch):
    monkeypatch.setattr(client.requests, "get", lambda *a, **k: FakeResponse(404, body=None, text=""))
    result = client.get_airport_flights("bogus", "LEMD", "2026-09-25T06:00", "2026-09-25T12:00")
    assert result == {"error": "HTTP 404"}
