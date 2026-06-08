# src/test_analysis.py

from src.database import fetch_all_listings
from src.analysis import clean_listings, enrich_listings, analyze_user_input
from src.database import fetch_neighborhoods_by_district

print(fetch_neighborhoods_by_district("kadikoy"))

def main():
    df = fetch_all_listings()

    print(f"Veritabanından gelen ilan sayısı: {len(df)}")

    df = clean_listings(df)
    df = enrich_listings(df)

    result = analyze_user_input(
    df=df,
    district="kadikoy",
    neighborhood="Suadiye",
    rent_price=90000,
    net_m2=90,
    room_count="2+1",
    )

    print("\nAnaliz sonucu:")
    print(result)


if __name__ == "__main__":
    main()