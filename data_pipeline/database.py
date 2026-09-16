import sqlite3
from data_pipeline.aerodatabox_client import get_airport_flights

CONFIG_DB_PATH = "data/flights.db"

CONFIG_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL,
    status TEXT,
    codeshare_status TEXT,
    scheduled_departure TEXT,
    revised_departure TEXT,
    scheduled_arrival TEXT,
    revised_arrival TEXT,
    gate TEXT,
    aircraft_model TEXT,
    airline_name TEXT,
    airline_iata TEXT,
    origin_airport TEXT,
    destination_airport TEXT,
    UNIQUE(number, scheduled_departure)
);
"""

def create_flights_table() -> None:
    conexion = sqlite3.connect(CONFIG_DB_PATH)
    cursor = conexion.cursor()
    cursor.execute(CONFIG_CREATE_TABLE_SQL)
    conexion.commit()
    conexion.close()

def save_flights(flights: list, origin_airport: str) -> None:
    conexion = sqlite3.connect(CONFIG_DB_PATH)
    cursor = conexion.cursor()

    sql = """
        INSERT INTO flights (
            number, status, codeshare_status, scheduled_departure, revised_departure,
            scheduled_arrival, revised_arrival, gate, aircraft_model,
            airline_name, airline_iata, origin_airport, destination_airport
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(number, scheduled_departure) DO UPDATE SET
            status = excluded.status,
            revised_departure = excluded.revised_departure,
            revised_arrival = excluded.revised_arrival,
            gate = excluded.gate;
    """

    for vuelo in flights:
        numero = vuelo["number"]
        estado = vuelo.get("status")

        departure = vuelo.get("departure", {})
        arrival = vuelo.get("arrival", {})

        salida_prevista = departure.get("scheduledTime", {}).get("local")
        salida_revisada = departure.get("revisedTime", {}).get("local")

        llegada_prevista = arrival.get("scheduledTime", {}).get("local")
        llegada_revisada = arrival.get("revisedTime", {}).get("local")

        puerta = departure.get("gate")

        modelo_avion = vuelo.get("aircraft", {}).get("model")
        nombre_aerolinea = vuelo.get("airline", {}).get("name")
        iata_aerolinea = vuelo.get("airline", {}).get("iata")

        aeropuerto_destino = arrival.get("airport", {}).get("icao")
        codeshare_status = vuelo.get("codeshareStatus")

        valores = (
            numero, estado, codeshare_status, salida_prevista, salida_revisada,
            llegada_prevista, llegada_revisada, puerta, modelo_avion,
            nombre_aerolinea, iata_aerolinea, origin_airport, aeropuerto_destino
        )        
        cursor.execute(sql, valores)

    conexion.commit()
    conexion.close()

if __name__ == "__main__":

    create_flights_table()

    vuelos = get_airport_flights("icao", "LEMD", "2026-09-16T06:00", "2026-09-16T12:00")
    departures = vuelos["departures"]

    save_flights(departures, "LEMD")

    print(f"Guardados {len(departures)} vuelos")