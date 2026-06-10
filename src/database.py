# src/database.py

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from src.config import (
    DB_CONFIG,
    COL_LISTING_ID,
    COL_SOURCE_SITE,
    COL_TITLE,
    COL_IMAGE_URL,
    COL_CITY,
    COL_DISTRICT,
    COL_NEIGHBORHOOD,
    COL_PRICE,
    COL_NET_M2,
    COL_GROSS_M2,
    COL_ROOM_COUNT,
    COL_BUILDING_AGE,
    COL_LISTING_URL,
    COL_DATE_COLLECTED,
)


def get_connection():
    """
    PostgreSQL bağlantısı oluşturur.
    """

    return psycopg2.connect(**DB_CONFIG)


def insert_listings_from_dataframe(df: pd.DataFrame) -> int:
    """
    DataFrame içindeki ilanları listings tablosuna toplu ekler.
    Aynı listing_url varsa tekrar eklemez.
    """

    if df.empty:
        return 0

    columns = [
        COL_LISTING_ID,
        COL_SOURCE_SITE,
        COL_TITLE,
        COL_CITY,
        COL_DISTRICT,
        COL_NEIGHBORHOOD,
        COL_PRICE,
        COL_NET_M2,
        COL_GROSS_M2,
        COL_ROOM_COUNT,
        COL_BUILDING_AGE,
        COL_LISTING_URL,
        COL_IMAGE_URL,
        COL_DATE_COLLECTED,
    ]

    records = df[columns].where(pd.notnull(df[columns]), None).values.tolist()

    query = f"""
    INSERT INTO listings ({", ".join(columns)})
    VALUES %s
    ON CONFLICT ({COL_LISTING_URL})
    DO UPDATE SET
        {COL_LISTING_ID} = EXCLUDED.{COL_LISTING_ID},
        {COL_SOURCE_SITE} = EXCLUDED.{COL_SOURCE_SITE},
        {COL_TITLE} = EXCLUDED.{COL_TITLE},
        {COL_CITY} = EXCLUDED.{COL_CITY},
        {COL_DISTRICT} = EXCLUDED.{COL_DISTRICT},
        {COL_NEIGHBORHOOD} = EXCLUDED.{COL_NEIGHBORHOOD},
        {COL_PRICE} = EXCLUDED.{COL_PRICE},
        {COL_NET_M2} = EXCLUDED.{COL_NET_M2},
        {COL_GROSS_M2} = EXCLUDED.{COL_GROSS_M2},
        {COL_ROOM_COUNT} = EXCLUDED.{COL_ROOM_COUNT},
        {COL_BUILDING_AGE} = EXCLUDED.{COL_BUILDING_AGE},
        {COL_IMAGE_URL} = EXCLUDED.{COL_IMAGE_URL},
        {COL_DATE_COLLECTED} = EXCLUDED.{COL_DATE_COLLECTED};
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, records)

    return len(records)


def fetch_all_listings() -> pd.DataFrame:
    """
    listings tablosundaki tüm ilanları DataFrame olarak döndürür.
    """

    query = "SELECT * FROM listings;"

    with get_connection() as conn:
        return pd.read_sql(query, conn)


def fetch_listings_by_district(district: str) -> pd.DataFrame:
    """
    Belirli ilçedeki ilanları DataFrame olarak döndürür.
    """

    query = f"""
    SELECT *
    FROM listings
    WHERE {COL_DISTRICT} = %s;
    """

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=(district,))

def fetch_neighborhoods_by_district(district: str) -> list[str]:
    """
    Seçilen ilçeye ait mahalle listesini PostgreSQL'den getirir.
    Arayüzde mahalle seçeneklerini üretmek için kullanılır.
    """

    query = f"""
    SELECT DISTINCT neighborhood
    FROM listings
    WHERE district = %s
      AND neighborhood IS NOT NULL
    ORDER BY neighborhood;
    """

    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=(district,))

    return df["neighborhood"].dropna().tolist()
def fetch_recent_listings(limit: int = 6) -> pd.DataFrame:
    """
    Ana sayfada gösterilecek son eklenen ilanları getirir.
    """

    query = """
    SELECT
        title,
        district,
        neighborhood,
        price,
        net_m2,
        room_count,
        listing_url,
        image_url,
        source_site,
        date_collected
    FROM listings
    ORDER BY date_collected DESC
    LIMIT %s;
    """

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=(limit,))

def count_listings() -> int:
    """
    listings tablosundaki toplam ilan sayısını döndürür.
    """

    query = "SELECT COUNT(*) FROM listings;"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()[0]


if __name__ == "__main__":
    print("PostgreSQL bağlantısı başarılı.")
    print(f"Toplam ilan sayısı: {count_listings()}")

    # ---------------------------------------------------------
# ANALİZ GEÇMİŞİ KAYDET
# Kullanıcının yaptığı analizleri veritabanına kaydeder.
# ---------------------------------------------------------

def save_analysis(
    user_id,
    district,
    neighborhood,
    room_count,
    rent_price,
    net_m2,
    fair_rent_score,
    status
):
    query = """
    INSERT INTO analysis_history (
        user_id,
        district,
        neighborhood,
        room_count,
        rent_price,
        net_m2,
        fair_rent_score,
        status
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s);
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    user_id,
                    district,
                    neighborhood,
                    room_count,
                    rent_price,
                    net_m2,
                    fair_rent_score,
                    status
                )
            )

# ---------------------------------------------------------
# KULLANICI ANALİZ GEÇMİŞİNİ GETİR
# Giriş yapmış kullanıcının geçmiş kira analizlerini
# en yeniden eskiye doğru listeler.
# ---------------------------------------------------------

def get_user_analysis_history(user_id):
    query = """
    SELECT *
    FROM analysis_history
    WHERE user_id = %s
    ORDER BY created_at DESC;
    """

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=(user_id,))

# ---------------------------------------------------------
# FAVORİ İLAN EKLE
# Kullanıcının seçtiği ilanı favorilerine kaydeder.
# Aynı ilan daha önce favoriye eklendiyse tekrar eklemez.
# ---------------------------------------------------------

def add_favorite(user_id, listing_url):
    query = """
    INSERT INTO favorites (user_id, listing_url)
    VALUES (%s, %s)
    ON CONFLICT (user_id, listing_url)
    DO NOTHING;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id, listing_url))


# ---------------------------------------------------------
# KULLANICININ FAVORİLERİNİ GETİR
# Favorilere eklenen ilanları listings tablosu ile birleştirerek döndürür.
# ---------------------------------------------------------

def get_user_favorites(user_id):
    query = """
    SELECT l.*
    FROM favorites f
    JOIN listings l
      ON f.listing_url = l.listing_url
    WHERE f.user_id = %s
    ORDER BY f.created_at DESC;
    """

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=(user_id,))


#---------------------------------#
def get_user_favorite_urls(user_id):
    query = """
    SELECT listing_url
    FROM favorites
    WHERE user_id = %s;
    """

    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=(user_id,))

    return df["listing_url"].tolist()


def remove_favorite(user_id, listing_url):
    query = """
    DELETE FROM favorites
    WHERE user_id = %s
      AND listing_url = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id, listing_url))


def is_favorite(user_id, listing_url):
    query = """
    SELECT 1
    FROM favorites
    WHERE user_id = %s
      AND listing_url = %s
    LIMIT 1;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id, listing_url))
            return cur.fetchone() is not None
