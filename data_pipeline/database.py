import sqlite3

CONFIG_DB_PATH = "data/flights.db"

CONFIG_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS flights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL,
    status TEXT,
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


if __name__ == "__main__":
    create_flights_table()