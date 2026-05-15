import pandas as pd

# Ham veri dosyasını oku
INPUT_PATH = "../data/raw/emlakjet_istanbul_raw_20260515_022850.csv"

# Analiz sonucu oluşacak temiz dosya
OUTPUT_PATH = "../data/processed/emlakjet_istanbul_processed.csv"

df = pd.read_csv(INPUT_PATH)

print("Veri yüklendi:", df.shape)


# 1) Metrekare başına kira fiyatını hesapla
# Bu değer, evleri sadece toplam kiraya göre değil,
# büyüklüğüne göre de karşılaştırmamızı sağlar.
df["price_per_net_m2"] = df["price"] / df["net_m2"]
df["price_per_gross_m2"] = df["price"] / df["gross_m2"]
# ---------------------------------------------------------
# EVLERİ METREKARE ARALIĞINA GÖRE SEGMENTLERE AYIR
# 55 m² küçük bir daire ile
# 180 m² büyük bir daireyi aynı grupta değerlendirmemek."benzer büyüklükteki evler" arasında karşılaştırma yapabilecek.

df["m2_segment"] = pd.cut(

    # Segmentlenecek kolon
    df["net_m2"],

    # m² aralıkları
    bins=[0, 50, 75, 100, 150, 1000],

    # Segment isimleri
    labels=["0-50","50-75","75-100","100-150","150+"]
)

# ---------------------------------------------------------
# BENZER EV GRUBU ORTALAMASI
# Evleri sadece ilçeye göre değil,oda sayısı + m² segmenti + ilçe kombinasyonuna göre değerlendirmek.


df["similar_group_avg_price_per_m2"] = (

    df.groupby(
        [
            "district",
            "room_count",
            "m2_segment"
        ]
    )["price_per_net_m2"]

    .transform("mean")
)


# 2) Her ilçe için ortalama m² kira fiyatını bul
# Böylece bir evin kendi ilçesine göre pahalı mı ucuz mu  olduğunu ölçebiliriz.
df["district_avg_price_per_m2"] = (
    df.groupby("district")["price_per_net_m2"]
    .transform("mean")
)

# 3)BENZER EVLERE GÖRE FİYAT ORANI
# İlanın kendi segmentindeki ortalamaya göre  pahalı mı ucuz mu olduğunu ölçmek.

# Aynı ilçedeki aynı oda tipindeki benzer m² evlere göre %25 pahalıysa sistem "Overpriced" diyebilecek.

df["relative_price_ratio"] = (

    df["price_per_net_m2"] /

    df["similar_group_avg_price_per_m2"]
)
# 4) Fiyat uygunluk etiketi üret
# Bu ilk versiyonda sadece ilçe ortalamasına göre karar veriyoruz.
# Daha sonra mahalle, bina yaşı, oda sayısı ve ulaşım skoru da eklenecek.
def classify_price(ratio):
    if ratio >= 1.20:
        return "Overpriced"
    elif ratio <= 0.85:
        return "Underpriced"
    else:
        return "Fair Price"


df["price_label"] = df["relative_price_ratio"].apply(classify_price)


# 5) İlçe bazında hızlı özet oluştur
summary = df.groupby("district").agg(
    listing_count=("listing_id", "count"),
    avg_price=("price", "mean"),
    median_price=("price", "median"),
    avg_net_m2=("net_m2", "mean"),
    avg_price_per_net_m2=("price_per_net_m2", "mean"),
).reset_index()


print("\nİlçe bazlı özet:")
print(summary)

print("\nFiyat etiketi dağılımı:")
print(df["price_label"].value_counts())


# 6) İşlenmiş veriyi kaydet
df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

print("\nİşlenmiş veri kaydedildi:", OUTPUT_PATH)