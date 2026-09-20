from rag.vector_store import query_regulations
from data_pipeline.aerodatabox_client import get_airport_flights
from data_pipeline.aerodatabox_client import search_airport as _search_airport_raw


def search_regulations(question: str) -> str:
    chunks = query_regulations(question)
    return "\n\n".join(chunks)


def _format_leg(leg: dict) -> str:
    time = leg.get("scheduledTime", {}).get("local", "?")
    airport = leg.get("airport")
    if airport:
        code = airport.get("iata") or airport.get("icao")
        return f"{time} @ {code} ({airport.get('name')})"
    return time


def _format_flight(flight: dict) -> str:
    parts = [
        flight.get("number"),
        flight.get("airline", {}).get("name"),
        flight.get("aircraft", {}).get("model"),
        flight.get("status"),
        f"dep {_format_leg(flight.get('departure', {}))}",
        f"arr {_format_leg(flight.get('arrival', {}))}",
    ]
    if flight.get("isCargo"):
        parts.append("cargo")
    return " | ".join(str(part) for part in parts if part)


MAX_FLIGHTS_TOTAL = 50


def search_flights(code_type: str, code: str, from_local: str, to_local: str, direction: str = "both") -> str:
    data = get_airport_flights(code_type, code, from_local, to_local)

    if "error" in data:
        return f"search_flights failed: {data['error']}"

    directions = []
    if direction in ("departures", "both"):
        directions.append("departures")
    if direction in ("arrivals", "both"):
        directions.append("arrivals")

    per_direction_cap = MAX_FLIGHTS_TOTAL // len(directions)
    sections = []

    for key in directions:
        flights = [flight for flight in data.get(key, []) if flight.get("codeshareStatus") != "IsCodeshared"]
        shown = flights[:per_direction_cap]
        lines = [_format_flight(flight) for flight in shown]
        header = f"{key} (showing {len(shown)} of {len(flights)}):"
        sections.append("\n".join([header] + lines) if lines else f"{header} none")

    return "\n\n".join(sections)


def _trim_airport(item: dict) -> dict:
    return {
        "icao": item.get("icao"),
        "iata": item.get("iata"),
        "name": item.get("name"),
        "city": item.get("municipalityName"),
        "country": item.get("countryCode"),
    }


def search_airport(query: str) -> dict:
    data = _search_airport_raw(query)
    return {"items": [_trim_airport(item) for item in data.get("items", [])]}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_regulations",
            "description": "Search the EASA Flight Time Limitations (FTL) regulation text for rules about crew duty periods, flight time limits, and rest requirements. Use this for any question about what is legally allowed or required regarding pilot/crew duty and rest times.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The regulation question to search for, in natural language, e.g. 'minimum rest period after a flight duty period'.",
                    },
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Get scheduled flights for an airport within a time window of at most 12 hours. Returns one line per flight (number, airline, aircraft, status, departure/arrival time and airport), capped at 50 flights combined across the requested directions. Each direction's header shows how many are being shown out of the real total - if it's truncated, narrow the time window or request a single direction to see the rest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code_type": {
                        "type": "string",
                        "enum": ["icao", "iata"],
                        "description": "Type of the airport code given in 'code'. Use 'icao' for 4-letter codes (e.g. LEMD) or 'iata' for 3-letter codes (e.g. MAD).",
                    },
                    "code": {
                        "type": "string",
                        "description": "Airport code matching code_type, e.g. 'LEMD' for icao or 'MAD' for iata.",
                    },
                    "from_local": {
                        "type": "string",
                        "description": "Start of the search window, in the airport's LOCAL time, format 'YYYY-MM-DDTHH:MM' (no seconds, no UTC offset), e.g. '2026-09-25T06:00'.",
                    },
                    "to_local": {
                        "type": "string",
                        "description": "End of the search window, same format as from_local. Must be strictly after from_local and no more than 12 hours later - the API rejects wider or negative windows.",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["departures", "arrivals", "both"],
                        "description": "Which flights to return. Defaults to 'both' if omitted. Use 'departures' or 'arrivals' alone when you don't need the other side - this reduces response size for busy airports.",
                    },
                },
                "required": ["code_type", "code", "from_local", "to_local"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_airport",
            "description": "Resolve a city or airport name to its ICAO and IATA codes. Call this first whenever the user refers to a place by name (e.g. 'Barcelona') instead of an airport code, then use the resulting icao or iata code with search_flights. Returns up to 10 matches, since names can be ambiguous across cities or countries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "City or airport name to search for, e.g. 'Barcelona' or 'Heathrow'.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

AVAILABLE_TOOLS = {
    "search_regulations": search_regulations,
    "search_flights": search_flights,
    "search_airport": search_airport,
}