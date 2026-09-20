from agent import tools


def test_format_leg_without_airport():
    leg = {"scheduledTime": {"local": "2026-09-25 06:00+02:00"}}
    assert tools._format_leg(leg) == "2026-09-25 06:00+02:00"


def test_format_leg_with_airport():
    leg = {
        "scheduledTime": {"local": "2026-09-25 09:30+02:00"},
        "airport": {"icao": "EPWA", "iata": "WAW", "name": "Warsaw"},
    }
    assert tools._format_leg(leg) == "2026-09-25 09:30+02:00 @ WAW (Warsaw)"


def test_format_leg_falls_back_to_icao_without_iata():
    leg = {
        "scheduledTime": {"local": "2026-09-25 09:30+02:00"},
        "airport": {"icao": "EPWA", "iata": None, "name": "Warsaw"},
    }
    assert "@ EPWA" in tools._format_leg(leg)


def test_format_flight_basic():
    flight = {
        "number": "LO 432",
        "status": "Expected",
        "airline": {"name": "LOT - Polish"},
        "aircraft": {"model": "Boeing 737"},
        "isCargo": False,
        "departure": {"scheduledTime": {"local": "2026-09-25 06:00+02:00"}},
        "arrival": {
            "scheduledTime": {"local": "2026-09-25 09:30+02:00"},
            "airport": {"icao": "EPWA", "iata": "WAW", "name": "Warsaw"},
        },
    }
    line = tools._format_flight(flight)
    assert "LO 432" in line
    assert "LOT - Polish" in line
    assert "Boeing 737" in line
    assert "Expected" in line
    assert "dep 2026-09-25 06:00+02:00" in line
    assert "arr 2026-09-25 09:30+02:00 @ WAW (Warsaw)" in line
    assert "cargo" not in line


def test_format_flight_marks_cargo():
    flight = {
        "number": "CX 99",
        "airline": {"name": "Cargolux"},
        "aircraft": {"model": "Boeing 747F"},
        "status": "Expected",
        "isCargo": True,
        "departure": {"scheduledTime": {"local": "2026-09-25 06:00+02:00"}},
        "arrival": {"scheduledTime": {"local": "2026-09-25 09:30+02:00"}},
    }
    assert tools._format_flight(flight).endswith("cargo")


def _make_flight(number, codeshare_status="IsOperator"):
    return {
        "number": number,
        "status": "Expected",
        "airline": {"name": "Test Air"},
        "aircraft": {"model": "A320"},
        "isCargo": False,
        "codeshareStatus": codeshare_status,
        "departure": {"scheduledTime": {"local": "2026-09-25 06:00+02:00"}},
        "arrival": {"scheduledTime": {"local": "2026-09-25 07:00+02:00"}},
    }


def test_search_flights_propagates_api_error(monkeypatch):
    monkeypatch.setattr(tools, "get_airport_flights", lambda *a, **k: {"error": "bad window"})
    result = tools.search_flights("icao", "LEMD", "2026-09-25T06:00", "2026-09-25T20:00")
    assert result == "search_flights failed: bad window"


def test_search_flights_filters_marketing_codeshares(monkeypatch):
    data = {
        "departures": [
            _make_flight("LO 432", "IsOperator"),
            _make_flight("BA 9999", "IsCodeshared"),
        ],
        "arrivals": [],
    }
    monkeypatch.setattr(tools, "get_airport_flights", lambda *a, **k: data)
    result = tools.search_flights("icao", "LEMD", "2026-09-25T06:00", "2026-09-25T12:00", direction="departures")
    assert "LO 432" in result
    assert "BA 9999" not in result
    assert "showing 1 of 1" in result


def test_search_flights_direction_only_departures(monkeypatch):
    data = {"departures": [_make_flight("LO 432")], "arrivals": [_make_flight("LO 999")]}
    monkeypatch.setattr(tools, "get_airport_flights", lambda *a, **k: data)
    result = tools.search_flights("icao", "LEMD", "2026-09-25T06:00", "2026-09-25T12:00", direction="departures")
    assert "departures" in result
    assert "arrivals" not in result
    assert "LO 999" not in result


def test_search_flights_splits_cap_across_both_directions(monkeypatch):
    departures = [_make_flight(f"DEP{i}") for i in range(tools.MAX_FLIGHTS_TOTAL)]
    arrivals = [_make_flight(f"ARR{i}") for i in range(tools.MAX_FLIGHTS_TOTAL)]
    monkeypatch.setattr(tools, "get_airport_flights", lambda *a, **k: {"departures": departures, "arrivals": arrivals})
    result = tools.search_flights("icao", "LEMD", "2026-09-25T06:00", "2026-09-25T12:00", direction="both")
    per_direction_cap = tools.MAX_FLIGHTS_TOTAL // 2
    assert f"showing {per_direction_cap} of {tools.MAX_FLIGHTS_TOTAL}" in result


def test_search_flights_no_flights_shows_none(monkeypatch):
    monkeypatch.setattr(tools, "get_airport_flights", lambda *a, **k: {"departures": [], "arrivals": []})
    result = tools.search_flights("icao", "ZZZZ", "2026-09-25T06:00", "2026-09-25T12:00")
    assert "departures (showing 0 of 0): none" in result
    assert "arrivals (showing 0 of 0): none" in result


def test_search_airport_trims_fields(monkeypatch):
    raw = {
        "items": [
            {
                "icao": "LEBL",
                "iata": "BCN",
                "name": "Barcelona",
                "shortName": "Barcelona",
                "municipalityName": "Barcelona",
                "location": {"lat": 41.29, "lon": 2.07},
                "countryCode": "ES",
                "timeZone": "Europe/Madrid",
            }
        ]
    }
    monkeypatch.setattr(tools, "_search_airport_raw", lambda query: raw)
    result = tools.search_airport("barcelona")
    assert result == {
        "items": [
            {"icao": "LEBL", "iata": "BCN", "name": "Barcelona", "city": "Barcelona", "country": "ES"}
        ]
    }


def test_search_regulations_joins_chunks(monkeypatch):
    monkeypatch.setattr(tools, "query_regulations", lambda question: ["chunk one", "chunk two"])
    assert tools.search_regulations("rest period?") == "chunk one\n\nchunk two"


def test_tools_schema_names_match_available_tools():
    schema_names = {tool["function"]["name"] for tool in tools.TOOLS}
    assert schema_names == set(tools.AVAILABLE_TOOLS.keys())
