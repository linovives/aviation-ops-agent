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

def search_airport(query):
    querystring = {"withSearchByCode":"true","limit":"10","q":query}

    response = requests.get(url, headers=headers, params=querystring)
    return response

if __name__ == "__main__":
    res=search_airport("barcelona")
    print(res.json())
