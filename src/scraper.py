import time
import pandas as pd
from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup
from config import DISTRICTS, CITY, HEADERS

# Verilen URL'deki HTML içeriğini çeker
def fetch_page(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text

# Listeleme sayfasındaki ilan detay linklerini bulur
def parse_listing_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []
# Sayfadaki tüm linkleri dolaşır
    for a in soup.find_all("a", href=True):
        href = a["href"]
# Emlakjet ilan linklerini filtreler
        if "/ilan/" in href:
            full_url = href if href.startswith("http") else "https://www.emlakjet.com" + href

            if full_url not in links:
                links.append(full_url)

    return links


# İlan başlığından fiyat, oda sayısı, ilan ID ve mahalle bilgisini çıkarır
def extract_from_title(title):
    price_match = re.search(r"([\d,]+)\s*TL", title)
    room_match = re.search(r"(\d+(\.\d+)?\+\d+)", title)
    id_match = re.search(r"#(\d+)", title)
    neighborhood_match = re.search(
    r"İstanbul\s+(?:Kadıköy|Üsküdar|Beşiktaş)\s+(.+?)\s+Mahallesi",
    title
)

    return {
        "price": int(price_match.group(1).replace(",", "")) if price_match else None,
        "room_count": room_match.group(1) if room_match else None,
        "listing_id": id_match.group(1) if id_match else None,
        "neighborhood": neighborhood_match.group(1) if neighborhood_match else None,
    }
# İlan detay sayfasındaki uzun metinden teknik özellikleri çıkarır
def extract_from_detail_text(text):
    def find(pattern):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    return {
        "listing_update_date": find(r"İlan Güncelleme Tarihi\s+(.+?)\s+Türü"),
        "net_m2": find(r"Net Metrekare\s+(\d+)\s*m²"),
        "gross_m2": find(r"Brüt Metrekare\s+(\d+)\s*m²"),
        "building_age": find(r"Binanın Yaşı\s+(.+?)\s+Bulunduğu Kat"),
        "floor": find(r"Bulunduğu Kat\s+(.+?)\s+Binanın Kat Sayısı"),
        "total_floors": find(r"Binanın Kat Sayısı\s+(\d+)"),
        "heating_type": find(r"Isıtma Tipi\s+(.+?)\s+Kullanım Durumu"),
        "usage_status": find(r"Kullanım Durumu\s+(.+?)\s+Eşya Durumu"),
        "furnished_status": find(r"Eşya Durumu\s+(.+?)\s+Tapu Durumu"),
        "bathroom_count": find(r"Banyo Sayısı\s+(\d+)"),
    }
# İlan detay metninden regex kullanarak ev özelliklerini çıkarır.
def extract_from_detail_text(text):
    def find(pattern):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    return {
        "listing_update_date": find(r"İlan Güncelleme Tarihi\s+(.+?)\s+Türü"),
        "net_m2": find(r"Net Metrekare\s+(\d+)\s*m²"),
        "gross_m2": find(r"Brüt Metrekare\s+(\d+)\s*m²"),
        "building_age": find(r"Binanın Yaşı\s+(.+?)\s+Bulunduğu Kat"),
        "floor": find(r"Bulunduğu Kat\s+(.+?)\s+Binanın Kat Sayısı"),
        "total_floors": find(r"Binanın Kat Sayısı\s+(\d+)"),
        "heating_type": find(r"Isıtma Tipi\s+(.+?)\s+Kullanım Durumu"),
        "usage_status": find(r"Kullanım Durumu\s+(.+?)\s+Eşya Durumu"),
        "furnished_status": find(r"Eşya Durumu\s+(.+?)\s+Tapu Durumu"),
        "bathroom_count": find(r"Banyo Sayısı\s+(\d+)"),
    }
# İlan detay sayfasını işleyerek başlık ve detay bilgilerinden veri çıkarır.
def parse_listing_detail(url):
    html = fetch_page(url)
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.text.strip() if soup.title else ""
    text = soup.get_text(" ", strip=True)

    extracted_title = extract_from_title(title)
    extracted_detail = extract_from_detail_text(text)

    return {
        "url": url,
        "title": title,
        **extracted_title,
        **extracted_detail
    }

# Programın ana çalışma akışı
def main():
    all_data = []
# config.py içindeki ilçe URL'lerini tek tek dolaşır
    for district in DISTRICTS:
        url = f"https://www.emlakjet.com/kiralik-daire/{CITY}-{district}/"
        print(f"{district} çekiliyor...")
# İlçe ilan listeleme sayfasını çeker
        html = fetch_page(url)
        # Sayfadaki ilan linklerini çıkarır
        links = parse_listing_links(html)

        print(f"{len(links)} ilan bulundu.\n")
 # Şimdilik sadece ilk ilanı test amaçlı işler
        for link in links:
            data = parse_listing_detail(link)
            # İlçe ve veri çekim zamanı bilgilerini ekler
            data["district"] = district
            data["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            all_data.append(data)
            #SCRAP BANI YEMEMEK İÇİN
            time.sleep(2)

    df = pd.DataFrame(all_data)
      # CSV dosyasına zaman damgalı isim verir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"../data/raw/emlakjet_istanbul_raw_{timestamp}.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\nCSV kaydedildi: {output_path}")
    print(df.head())

if __name__ == "__main__":
    main()