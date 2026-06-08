# app.py

from flask import Flask, render_template, request, jsonify

from src.database import fetch_all_listings, fetch_neighborhoods_by_district, fetch_recent_listings
from src.analysis import clean_listings, enrich_listings, analyze_user_input


DISTRICT_LABELS = {
    "kadikoy": "Kadıköy",
    "uskudar": "Üsküdar",
    "besiktas": "Beşiktaş",
}

app = Flask(__name__)


# ---------------------------------------------------------
# ANA SAYFA
# Kullanıcı kira analizi için ev bilgilerini bu sayfada girer.
# ---------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    recent_df = fetch_recent_listings(limit=6)
    recent_listings = recent_df.to_dict(orient="records")

    return render_template(
        "index.html",
        recent_listings=recent_listings,
    )

#-----------------
@app.route("/neighborhoods/<district>", methods=["GET"])
def neighborhoods(district):
    neighborhoods_list = fetch_neighborhoods_by_district(district)
    return jsonify(neighborhoods_list)

# ---------------------------------------------------------
# ANALİZ SONUCU
# Formdan gelen kullanıcı girdilerini alır, PostgreSQL'deki
# ilanlarla karşılaştırır ve sonucu arayüze gönderir.
# ---------------------------------------------------------

@app.route("/analyze", methods=["POST"])
def analyze():
    district = request.form.get("district")
    neighborhood = request.form.get("neighborhood")
    room_count = request.form.get("room_count")
    rent_price = int(request.form.get("rent_price"))
    net_m2 = int(request.form.get("net_m2"))

    df = fetch_all_listings()

    df = clean_listings(df)
    df = enrich_listings(df)

    result = analyze_user_input(
        df=df,
        district=district,
        neighborhood=neighborhood,
        rent_price=rent_price,
        net_m2=net_m2,
        room_count=room_count,
    )

    user_input = {
        "district": district,
        "district_label": DISTRICT_LABELS.get(district, district),
        "neighborhood": neighborhood,
        "room_count": room_count,
        "rent_price": rent_price,
        "net_m2": net_m2,
    }

    return render_template(
        "result.html",
        result=result,
        user_input=user_input,
    )



#-----------------------
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json()

    district = data.get("district")
    neighborhood = data.get("neighborhood")
    room_count = data.get("room_count")
    rent_price = int(data.get("rent_price"))
    net_m2 = int(data.get("net_m2"))

    df = fetch_all_listings()
    df = clean_listings(df)
    df = enrich_listings(df)

    result = analyze_user_input(
        df=df,
        district=district,
        neighborhood=neighborhood,
        rent_price=rent_price,
        net_m2=net_m2,
        room_count=room_count,
    )

    return jsonify(result)

# ---------------------------------------------------------
# UYGULAMA BAŞLATMA
# Flask geliştirme sunucusunu çalıştırır.
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5001)


print(app.url_map)
