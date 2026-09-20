import requests
from dotenv import load_dotenv
import os

load_dotenv()

CONFIG_API_KEY = os.getenv("AERODATABOX_API_KEY")
CONFIG_API_HOST = os.getenv("AERODATABOX_HOST")

url = "https://aerodatabox.p.rapidapi.com/airports/search/term"


headers = {
	"x-rapidapi-key": CONFIG_API_KEY,
	"x-rapidapi-host": CONFIG_API_HOST
}

def search_airport(query: str) -> dict:
    querystring = {"withSearchByCode":"true","limit":"10","q":query}
    response = requests.get(url, headers=headers, params=querystring)
    return response.json()

def get_airport_flights(code_type: str, code: str, from_local: str, to_local: str) -> dict:
    flight_url = f"https://aerodatabox.p.rapidapi.com/flights/airports/{code_type}/{code}/{from_local}/{to_local}"
    querystring = {
        "withCargo": "true",
        "withCodeshared": "true",
        "withCancelled": "true",
        "withLeg": "true",
        "withPrivate": "true",
        "withLocation": "false",
    }
    response = requests.get(flight_url, headers=headers, params=querystring)

    if response.status_code == 204:
        return {"departures": [], "arrivals": []}

    if not response.ok:
        try:
            message = response.json().get("message", response.text)
        except ValueError:
            message = response.text or f"HTTP {response.status_code}"
        return {"error": message}

    return response.json()


if __name__ == "__main__":
    res=search_airport("barcelona")
    print(res)
    vuelos = get_airport_flights("icao", "LEMD", "2026-09-16T06:00", "2026-09-16T12:00")
    print(vuelos["departures"][0])
