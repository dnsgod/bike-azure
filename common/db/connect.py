# common/db/connect.py
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def _pick_driver():
    drivers = [d.strip() for d in pyodbc.drivers()]
    for name in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"):
        if name in drivers:
            return name
    raise RuntimeError(f"ODBC SQL Server driver not found. Installed: {drivers}")

def get_conn():
    server   = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DB")
    uid      = os.getenv("SQL_UID")
    pwd      = os.getenv("SQL_PWD")


    print("[DEBUG] SQL_SERVER =", server)
    print("[DEBUG] SQL_DB     =", database)
    print("[DEBUG] SQL_UID    =", uid)

    missing = [k for k,v in {
        "SQL_SERVER": server,
        "SQL_DB": database,
        "SQL_UID": uid,
        "SQL_PWD": pwd,
    }.items() if not v]
    if missing:
        raise RuntimeError(f".env missing keys: {missing}")

    driver = _pick_driver()
    print("[DEBUG] Using driver:", driver)


    conn_str = (
        f"Driver={{{driver}}};"
        f"Server={server};"
        f"Database={database};"
        f"Uid={uid};"
        f"Pwd={pwd};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    print("[DEBUG] Trying conn_str =", conn_str)

    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except pyodbc.Error as e:
        print("[DEBUG] First connect failed:", e)

        fallback_conn_str = (
            f"Driver={{{driver}}};"
            f"Server={server};"
            f"Database={database};"
            f"Uid={uid};"
            f"Pwd={pwd};"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
            "Connection Timeout=30;"
        )
        print("[DEBUG] Trying fallback conn_str =", fallback_conn_str)
        conn = pyodbc.connect(fallback_conn_str)
        return conn
