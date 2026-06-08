# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()
# ---------------------------------------------------------
# GENEL PROJE AYARLARI
# ---------------------------------------------------------

CITY = "istanbul"

DISTRICTS = [
    "kadikoy",
    "uskudar",
    "besiktas",
]


# ---------------------------------------------------------
# SCRAPER AYARLARI
# ---------------------------------------------------------

SOURCE_SITE = "Emlakjet"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    )
}

MAX_LISTINGS_PER_DISTRICT = 100
REQUEST_DELAY = 2


# ---------------------------------------------------------
# VERİ SETİ KOLON STANDARTLARI
# ---------------------------------------------------------

COL_LISTING_ID = "listing_id"
COL_SOURCE_SITE = "source_site"
COL_TITLE = "title"
COL_IMAGE_URL = "image_url"
COL_CITY = "city"
COL_DISTRICT = "district"
COL_NEIGHBORHOOD = "neighborhood"
COL_PRICE = "price"
COL_NET_M2 = "net_m2"
COL_GROSS_M2 = "gross_m2"
COL_ROOM_COUNT = "room_count"
COL_BUILDING_AGE = "building_age"
COL_LISTING_URL = "listing_url"
COL_DATE_COLLECTED = "date_collected"

REQUIRED_COLUMNS = [
    COL_LISTING_ID,
    COL_TITLE,
    COL_DISTRICT,
    COL_PRICE,
    COL_NET_M2,
    COL_GROSS_M2,
    COL_ROOM_COUNT,
    COL_LISTING_URL,
]


# ---------------------------------------------------------
# ANALİZ PARAMETRELERİ
# ---------------------------------------------------------

M2_SEGMENT_BINS = [0, 50, 75, 100, 150, 1000]
M2_SEGMENT_LABELS = ["0-50", "50-75", "75-100", "100-150", "150+"]

OVERPRICED_THRESHOLD = 1.20
UNDERPRICED_THRESHOLD = 0.85

DEFAULT_ALTERNATIVE_LIMIT = 5


# ---------------------------------------------------------
# POSTGRESQL AYARLARI
# ---------------------------------------------------------

DB_CONFIG = {
    "dbname": "fair_rent_db",
    "user": "postgres",
    "password": "12345",
    "host": "localhost",
    "port": 5432,
}