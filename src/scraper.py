# src/scraper.py
import os
import re
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import (
    CITY,
    DISTRICTS,
    HEADERS,
    COL_IMAGE_URL,
    SOURCE_SITE,
    MAX_LISTINGS_PER_DISTRICT,
    REQUEST_DELAY,
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
    COL_DATE_COLLECTED,
)

from src.database import insert_listings_from_dataframe

# ---------------------------------------------------------
# SAYFA İÇERİĞİNİ ÇEK
# Verilen URL'deki HTML içeriğini alır.
# ---------------------------------------------------------

def fetch_page(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text


# ---------------------------------------------------------
# LİSTELEME SAYFASINDAN İLAN LİNKLERİNİ ÇIKAR
# Emlakjet listeleme sayfasındaki /ilan/ linklerini toplar.
# ---------------------------------------------------------

def parse_listing_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]

        if "/ilan/" not in href:
            continue

        full_url = href if href.startswith("http") else f"https://www.emlakjet.com{href}"

        if full_url not in links:
            links.append(full_url)

    return links


# ---------------------------------------------------------
# SAYFA BAŞLIĞINDAN TEMEL BİLGİLERİ ÇIKAR
# Bazı ilanlarda fiyat, oda sayısı, ilan ID ve mahalle bilgisi
# title içinde bulunabiliyor.
# ---------------------------------------------------------

def extract_from_title(title: str) -> dict:
    price_match = re.search(r"([\d,.]+)\s*TL", title)
    room_match = re.search(r"(\d+(\.\d+)?\+\d+)", title)
    id_match = re.search(r"#(\d+)", title)

    neighborhood_match = re.search(
        r"İstanbul\s+.+?\s+(.+?)\s+Mahallesi",
        title,
    )

    price = None
    if price_match:
        price = int(
            price_match.group(1)
            .replace(".", "")
            .replace(",", "")
        )

    return {
        COL_PRICE: price,
        COL_ROOM_COUNT: room_match.group(1) if room_match else None,
        COL_LISTING_ID: id_match.group(1) if id_match else None,
        COL_NEIGHBORHOOD: neighborhood_match.group(1) if neighborhood_match else None,
    }


# ---------------------------------------------------------
# İLAN DETAY METNİNDEN TEKNİK ÖZELLİKLERİ ÇIKAR
# Detay sayfasındaki uzun metinden net m², brüt m², bina yaşı
# gibi analizde kullanılacak alanları regex ile alır.
# ---------------------------------------------------------

def extract_from_detail_text(text: str) -> dict:
    def find(pattern: str):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    return {
        COL_NET_M2: find(r"Net Metrekare\s+(\d+)\s*m²"),
        COL_GROSS_M2: find(r"Brüt Metrekare\s+(\d+)\s*m²"),
        COL_BUILDING_AGE: find(r"Binanın Yaşı\s+(.+?)\s+Bulunduğu Kat"),
        "listing_update_date": find(r"İlan Güncelleme Tarihi\s+(.+?)\s+Türü"),
        "floor": find(r"Bulunduğu Kat\s+(.+?)\s+Binanın Kat Sayısı"),
        "total_floors": find(r"Binanın Kat Sayısı\s+(\d+)"),
        "heating_type": find(r"Isıtma Tipi\s+(.+?)\s+Kullanım Durumu"),
        "usage_status": find(r"Kullanım Durumu\s+(.+?)\s+Eşya Durumu"),
        "furnished_status": find(r"Eşya Durumu\s+(.+?)\s+Tapu Durumu"),
        "bathroom_count": find(r"Banyo Sayısı\s+(\d+)"),
    }

def extract_image_url(soup: BeautifulSoup) -> str | None:
    """
    İlan detay sayfasındaki ilk uygun görsel URL'sini çıkarır.
    """

    image = soup.find("meta", property="og:image")

    if image and image.get("content"):
        return image.get("content")

    img_tag = soup.find("img")

    if img_tag and img_tag.get("src"):
        return img_tag.get("src")

    return None

# ---------------------------------------------------------
# TEK BİR İLAN DETAYINI PARSE ET
# İlan detay sayfasını açar, başlık ve detay metninden verileri
# standart kolon yapısına uygun şekilde döndürür.
# ---------------------------------------------------------

def parse_listing_detail(url: str, district: str) -> dict:
    html = fetch_page(url)
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.text.strip() if soup.title else ""
    text = soup.get_text(" ", strip=True)
       

    title_data = extract_from_title(title)
    detail_data = extract_from_detail_text(text)

    return {
        COL_SOURCE_SITE: SOURCE_SITE,
        COL_CITY: CITY,
        COL_DISTRICT: district,
        COL_TITLE: title,
        COL_LISTING_URL: url,
        COL_IMAGE_URL: extract_image_url(soup),
        COL_DATE_COLLECTED: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **title_data,
        **detail_data,

}


# ---------------------------------------------------------
# İLÇE BAZLI VERİ ÇEK
# Belirlenen ilçenin listeleme sayfasından ilan linklerini alır
# ve her ilan detayını işler.
# ---------------------------------------------------------

def scrape_district(district: str) -> list[dict]:
    url = f"https://www.emlakjet.com/kiralik-daire/{CITY}-{district}/"

    print(f"{district} çekiliyor...")

    html = fetch_page(url)
    links = parse_listing_links(html)

    links = links[:MAX_LISTINGS_PER_DISTRICT]

    print(f"{len(links)} ilan işlenecek.")

    district_data = []

    for link in links:
        try:
            data = parse_listing_detail(link, district)
            district_data.append(data)
            time.sleep(REQUEST_DELAY)

        except Exception as error:
            print(f"İlan işlenemedi: {link}")
            print(f"Hata: {error}")

    return district_data


# ---------------------------------------------------------
# TÜM İLÇELER İÇİN VERİ ÇEK
# config.py içindeki DISTRICTS listesine göre tüm ilçeleri dolaşır.
# ---------------------------------------------------------

def scrape_all_districts() -> pd.DataFrame:
    all_data = []

    for district in DISTRICTS:
        district_data = scrape_district(district)
        all_data.extend(district_data)

    return pd.DataFrame(all_data)


# ---------------------------------------------------------
# CSV OLARAK KAYDET
# PostgreSQL'e geçmeden önce yedek veri üretmek veya hızlı test
# yapmak için kullanılır.
# ---------------------------------------------------------

def save_to_csv(df: pd.DataFrame) -> str:
    """
    Çekilen veriyi CSV olarak yedekler.
    Klasör yoksa otomatik oluşturur.
    """

    output_dir = "data/raw"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{output_dir}/emlakjet_{CITY}_raw_{timestamp}.csv"

    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path


# ---------------------------------------------------------
# ANA ÇALIŞMA AKIŞI
# Dosya doğrudan çalıştırıldığında:
# 1) Emlakjet verisini çeker
# 2) CSV yedeği oluşturur
# 3) PostgreSQL listings tablosuna kaydeder
# ---------------------------------------------------------

def main():
    print("Scraper başladı.")
    df = scrape_all_districts()

    if df.empty:
        print("Veri çekilemedi.")
        return

    output_path = save_to_csv(df)
    inserted_count = insert_listings_from_dataframe(df)

    print(f"\nCSV kaydedildi: {output_path}")
    print(f"PostgreSQL'e gönderilen ilan sayısı: {inserted_count}")
    print(df.head())

if __name__ == "__main__":
    main()
