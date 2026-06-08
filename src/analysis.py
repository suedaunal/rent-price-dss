# src/analysis.py

import pandas as pd

from src.config import (
    REQUIRED_COLUMNS,
    COL_LISTING_ID,
    COL_TITLE,
    COL_IMAGE_URL,
    COL_DISTRICT,
    COL_NEIGHBORHOOD,
    COL_PRICE,
    COL_NET_M2,
    COL_GROSS_M2,
    COL_ROOM_COUNT,
    COL_LISTING_URL,
    M2_SEGMENT_BINS,
    M2_SEGMENT_LABELS,
    OVERPRICED_THRESHOLD,
    UNDERPRICED_THRESHOLD,
    DEFAULT_ALTERNATIVE_LIMIT,
)


# ---------------------------------------------------------
# HAM VERİYİ TEMİZLE
# Scraper veya CSV üzerinden gelen veriler analizden önce
# standart hale getirilir.
# ---------------------------------------------------------

def clean_listings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ham ilan verisini analiz için kullanılabilir hale getirir.
    """

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Eksik kolonlar: {missing_columns}")

    df = df.copy()

    # Scraper bazı değerleri metin olarak getirebilir.
    # Analizden önce temel sayısal alanları numeric tipe çeviriyoruz.
    df[COL_PRICE] = pd.to_numeric(df[COL_PRICE], errors="coerce")
    df[COL_NET_M2] = pd.to_numeric(df[COL_NET_M2], errors="coerce")
    df[COL_GROSS_M2] = pd.to_numeric(df[COL_GROSS_M2], errors="coerce")

    # Fiyat, net m², ilçe ve oda sayısı olmayan ilanlar
    # karşılaştırma için yeterli bilgi sağlamaz.
    df = df.dropna(
        subset=[
            COL_PRICE,
            COL_NET_M2,
            COL_DISTRICT,
            COL_ROOM_COUNT,
        ]
    )

    # Sıfır veya negatif değerler geçersiz kabul edilir.
    df = df[df[COL_PRICE] > 0]
    df = df[df[COL_NET_M2] > 0]

    # Metinsel alanlar standartlaştırılır.
    df[COL_DISTRICT] = df[COL_DISTRICT].astype(str).str.lower().str.strip()
    df[COL_ROOM_COUNT] = df[COL_ROOM_COUNT].astype(str).str.strip()

    return df


# ---------------------------------------------------------
# ANALİZ KOLONLARI EKLE
# İlanlara m² fiyatı, segment, grup ortalaması, fiyat etiketi
# ve adil kira puanı gibi türetilmiş alanlar eklenir.
# ---------------------------------------------------------

def enrich_listings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Temiz ilan verisine analiz için kullanılacak yeni kolonları ekler.
    """

    df = df.copy()

    # Metrekare başına kira fiyatı.
    # Evleri sadece toplam kiraya göre değil, büyüklüğe göre karşılaştırır.
    df["price_per_net_m2"] = df[COL_PRICE] / df[COL_NET_M2]

    # Brüt m² başına kira.
    # Brüt m² her ilanda güvenilir olmayabilir, bu yüzden ana metrik net m²’dir.
    df["price_per_gross_m2"] = df[COL_PRICE] / df[COL_GROSS_M2]

    # Evleri benzer büyüklükteki ilanlarla karşılaştırmak için segmentliyoruz.
    df["m2_segment"] = pd.cut(
        df[COL_NET_M2],
        bins=M2_SEGMENT_BINS,
        labels=M2_SEGMENT_LABELS,
    )

    # Benzer grup:
    # aynı ilçe + aynı oda sayısı + aynı m² segmenti.
    df["similar_group_avg_price_per_m2"] = (
        df.groupby(
            [COL_DISTRICT, COL_ROOM_COUNT, "m2_segment"],
            observed=False,
        )["price_per_net_m2"]
        .transform("mean")
    )

    # İlçe bazlı genel ortalama.
    # Veri kontrolü ve raporlama için ek metrik.
    df["district_avg_price_per_m2"] = (
        df.groupby(COL_DISTRICT)["price_per_net_m2"]
        .transform("mean")
    )

    # 1.00 = benzer grup ortalamasına eşit.
    # 1.20 = yaklaşık %20 pahalı.
    # 0.85 = yaklaşık %15 ucuz.
    df["relative_price_ratio"] = (
        df["price_per_net_m2"] / df["similar_group_avg_price_per_m2"]
    )

    df["price_label"] = df["relative_price_ratio"].apply(classify_price)
    df["fair_rent_score"] = df["relative_price_ratio"].apply(
        calculate_fair_rent_score
    )

    return df


# ---------------------------------------------------------
# FİYAT SINIFLANDIRMA
# Eşik değerleri config.py üzerinden gelir.
# ---------------------------------------------------------

def classify_price(ratio: float) -> str:
    """
    Göreli fiyat oranına göre kira sınıfı döndürür.
    """

    if pd.isna(ratio):
        return "Veri Yetersiz"

    if ratio >= OVERPRICED_THRESHOLD:
        return "Yüksek"

    if ratio <= UNDERPRICED_THRESHOLD:
        return "Düşük"

    return "Makul"


# ---------------------------------------------------------
# ADİL KİRA PUANI
# Oran 1.00'a yaklaştıkça puan yükselir.
# ---------------------------------------------------------

def calculate_fair_rent_score(ratio: float) -> int:
    """
    Göreli fiyat oranına göre 0-100 arası adil kira puanı üretir.
    """

    if pd.isna(ratio):
        return 0

    score = 100 - abs(1 - ratio) * 100

    return max(0, min(100, round(score)))


# ---------------------------------------------------------
# KULLANICI GİRDİSİNİ ANALİZ ET
# Web formundan gelen ev bilgilerini mevcut ilan verisiyle
# karşılaştırır.
# ---------------------------------------------------------

def analyze_user_input(
    df: pd.DataFrame,
    district: str,
    rent_price: int,
    net_m2: int,
    room_count: str,
    neighborhood: str | None = None,
) -> dict:
    """
    Kullanıcının girdiği kira bilgisini benzer ilanlarla karşılaştırır.
    """

    district = district.lower().strip()
    room_count = room_count.strip()
    neighborhood = neighborhood.strip() if neighborhood else None
    user_price_per_m2 = rent_price / net_m2

    # Kullanıcının evi hangi m² segmentinde, önce onu belirliyoruz.
    user_segment = pd.cut(
        pd.Series([net_m2]),
        bins=M2_SEGMENT_BINS,
        labels=M2_SEGMENT_LABELS,
    ).iloc[0]

    # İlk karşılaştırma: en dar ve en doğru grup.
    # Önce en dar karşılaştırma yapılır:
    # aynı ilçe + aynı mahalle + aynı oda sayısı + aynı m² segmenti.
    if neighborhood:
        similar_listings = df[
            (df[COL_DISTRICT] == district)
            & (df[COL_NEIGHBORHOOD] == neighborhood)
            & (df[COL_ROOM_COUNT] == room_count)
            & (df["m2_segment"] == user_segment)
        ].copy()

        # Mahallede segment bazlı yeterli veri yoksa segment filtresi kaldırılır.
        if similar_listings.empty:
            similar_listings = df[
                (df[COL_DISTRICT] == district)
                & (df[COL_NEIGHBORHOOD] == neighborhood)
                & (df[COL_ROOM_COUNT] == room_count)
            ].copy()
    else:
        similar_listings = pd.DataFrame()

    # Mahalle bazında yeterli veri yoksa ilçe seviyesine düşülür.
    if similar_listings.empty:
        similar_listings = df[
            (df[COL_DISTRICT] == district)
            & (df[COL_ROOM_COUNT] == room_count)
            & (df["m2_segment"] == user_segment)
        ].copy()

    # İlçe + segment bazında veri yoksa sadece ilçe + oda sayısı kullanılır.
    if similar_listings.empty:
        similar_listings = df[
            (df[COL_DISTRICT] == district)
            & (df[COL_ROOM_COUNT] == room_count)
        ].copy()

    # Veri azsa segment filtresini kaldırıyoruz.
    # Böylece sistem tamamen sonuçsuz kalmaz.
    if similar_listings.empty:
        similar_listings = df[
            (df[COL_DISTRICT] == district)
            & (df[COL_ROOM_COUNT] == room_count)
        ].copy()

    if similar_listings.empty:
        return {
            "status": "Veri Yetersiz",
            "message": "Bu kriterlere uygun karşılaştırılabilir ilan bulunamadı.",
            "fair_rent_score": 0,
            "average_rent": None,
            "average_price_per_m2": None,
            "user_price_per_m2": float(round(user_price_per_m2, 2)),
            "relative_price_ratio": None,
            "alternatives": [],
        }

    avg_rent = similar_listings[COL_PRICE].mean()
    avg_price_per_m2 = similar_listings["price_per_net_m2"].mean()

    ratio = user_price_per_m2 / avg_price_per_m2
    label = classify_price(ratio)
    score = calculate_fair_rent_score(ratio)

    alternatives = get_alternative_listings(
        similar_listings=similar_listings,
        user_rent_price=rent_price,
        limit=DEFAULT_ALTERNATIVE_LIMIT,
    )

    return {
    "status": label,
    "fair_rent_score": int(score),
    "average_rent": int(round(avg_rent)),
    "average_price_per_m2": float(round(avg_price_per_m2, 2)),
    "user_price_per_m2": float(round(user_price_per_m2, 2)),
    "relative_price_ratio": float(round(ratio, 2)),
    "alternatives": alternatives,
    }


# ---------------------------------------------------------
# ALTERNATİF İLANLARI GETİR
# Kullanıcının girdiği kiradan daha uygun fiyatlı benzer
# ilanları seçer.
# ---------------------------------------------------------

def get_alternative_listings(
    similar_listings: pd.DataFrame,
    user_rent_price: int,
    limit: int = DEFAULT_ALTERNATIVE_LIMIT,
) -> list[dict]:
    """
    Kullanıcı kirasından daha düşük fiyatlı alternatif ilanları döndürür.
    """

    alternatives = similar_listings[
        similar_listings[COL_PRICE] < user_rent_price
    ].copy()

    if alternatives.empty:
        return []

    # Önce yüksek puanlı, sonra daha ucuz ilanlar gösterilir.
    alternatives = alternatives.sort_values(
        by=["fair_rent_score", COL_PRICE],
        ascending=[False, True],
    ).head(limit)

    return alternatives[
        [
            COL_TITLE,
            COL_DISTRICT,
            COL_PRICE,
            COL_NET_M2,
            COL_ROOM_COUNT,
            "fair_rent_score",
            COL_LISTING_URL,
            COL_IMAGE_URL,
        ]
    ].to_dict(orient="records")


# ---------------------------------------------------------
# İLÇE BAZLI ÖZET
# Veri kontrolü ve raporlama için kullanılır.
# ---------------------------------------------------------

def create_district_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    İlçe bazında ilan sayısı ve fiyat istatistiklerini üretir.
    """

    return (
        df.groupby(COL_DISTRICT)
        .agg(
            listing_count=(COL_LISTING_ID, "count"),
            avg_price=(COL_PRICE, "mean"),
            median_price=(COL_PRICE, "median"),
            avg_net_m2=(COL_NET_M2, "mean"),
            avg_price_per_net_m2=("price_per_net_m2", "mean"),
        )
        .reset_index()
    )


# ---------------------------------------------------------
# CSV İŞLEME
# Yedek veri üretmek veya hızlı test yapmak için kullanılır.
# Ana ürün akışında veri PostgreSQL'den gelecek.
# ---------------------------------------------------------

def process_csv(input_path: str, output_path: str) -> pd.DataFrame:
    """
    CSV verisini temizler, analiz kolonlarını ekler ve çıktıyı kaydeder.
    """

    df = pd.read_csv(input_path)

    df = clean_listings(df)
    df = enrich_listings(df)

    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return df