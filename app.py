# app.py

from flask import (Flask,render_template,request,jsonify,redirect,session,url_for)

from werkzeug.security import (generate_password_hash,check_password_hash)

from src.database import (
    fetch_all_listings,
    fetch_neighborhoods_by_district,
    fetch_recent_listings,
    get_connection,
    save_analysis,
    get_user_analysis_history,
    add_favorite,
    get_user_favorites,
    get_user_favorite_urls,
    remove_favorite,
    is_favorite,
    get_home_stats
)

from src.analysis import (clean_listings,enrich_listings,analyze_user_input)

DISTRICT_LABELS = {
    "kadikoy": "Kadıköy",
    "uskudar": "Üsküdar",
    "besiktas": "Beşiktaş",
    "sisli": "Şişli",
    "bakirkoy": "Bakırköy",
    "maltepe": "Maltepe",
    "atasehir": "Ataşehir",
    "sariyer": "Sarıyer",
}

app = Flask(__name__)
app.secret_key = "dev-secret-key"
# ---------------------------------------------------------
# KAYIT OL
# Yeni kullanıcı oluşturur.
# Şifre veritabanına düz metin olarak değil,
# hashlenmiş şekilde kaydedilir.
# Başarılı kayıt sonrası kullanıcı otomatik giriş yapar.
# ---------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")


    if not email or not password:
        return "E-posta ve şifre zorunludur."

    if password != confirm_password:
        return "Şifreler eşleşmiyor."

    password_hash = generate_password_hash(password)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash)
                    VALUES (%s, %s)
                    RETURNING id;
                    """,
                    (email, password_hash),
                )
                user_id = cur.fetchone()[0]

        session["user_id"] = user_id
        session["email"] = email

        return redirect(url_for("index"))

    except Exception as error:
        print(error)
        return "Bu e-posta zaten kayıtlı olabilir."


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, password_hash
                FROM users
                WHERE email = %s;
                """,
                (email,),
            )
            user = cur.fetchone()

    if user and check_password_hash(user[2], password):
        session["user_id"] = user[0]
        session["email"] = user[1]
        return redirect(url_for("index"))

    return "E-posta veya şifre hatalı."


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------------------------------------------------------
# GEÇMİŞ ANALİZLER
# Kullanıcının yaptığı analizleri listeler.
# ---------------------------------------------------------

@app.route("/history")
def history():

    if not session.get("user_id"):
        return redirect("/?auth=login")

    history_df = get_user_analysis_history(
        session["user_id"]
    )

    history_records = history_df.to_dict(
        orient="records"
    )

    return render_template(
        "history.html",
        history=history_records
    )

# ---------------------------------------------------------
# FAVORİYE EKLE
# Giriş yapmış kullanıcının seçtiği ilanı favorilerine kaydeder.
# ---------------------------------------------------------

@app.route("/favorite/add", methods=["POST"])
def favorite_add():

    if not session.get("user_id"):
        return redirect(url_for("login"))

    listing_url = request.form.get("listing_url")

    if listing_url:
        add_favorite(
            user_id=session["user_id"],
            listing_url=listing_url
        )

    return redirect(request.referrer or url_for("index"))

@app.route("/favorite/toggle", methods=["POST"])
def favorite_toggle():

    if not session.get("user_id"):
        return jsonify({
            "success": False,
            "requires_login": True
        }), 401

    data = request.get_json()
    listing_url = data.get("listing_url")

    if not listing_url:
        return jsonify({
            "success": False,
            "message": "listing_url eksik"
        }), 400

    if is_favorite(session["user_id"], listing_url):
        remove_favorite(session["user_id"], listing_url)
        return jsonify({
            "success": True,
            "is_favorite": False
        })

    add_favorite(session["user_id"], listing_url)
    return jsonify({
        "success": True,
        "is_favorite": True
    })

# ---------------------------------------------------------
# FAVORİLERİM
# Kullanıcının favoriye eklediği ilanları listeler.
# ---------------------------------------------------------

@app.route("/favorites")
def favorites():
    if not session.get("user_id"):
        return redirect("/?auth=login")

    favorites_df = get_user_favorites(
        session["user_id"]
    )

    favorite_listings = favorites_df.to_dict(
        orient="records"
    )

    return render_template(
        "favorites.html",
        favorites=favorite_listings
    )
# ---------------------------------------------------------
# ANA SAYFA
# Kullanıcı kira analizi için ev bilgilerini bu sayfada girer.
# ---------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    recent_df = fetch_recent_listings(limit=6)
    recent_listings = recent_df.to_dict(orient="records")
    stats = get_home_stats()

    favorite_urls = []

    if session.get("user_id"):
        favorite_urls = get_user_favorite_urls(session["user_id"])

    return render_template(
        "index.html",
        recent_listings=recent_listings,
        favorite_urls=favorite_urls,
        stats=stats,
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
    # ---------------------------------------------------------
    # Giriş yapmış kullanıcıların analiz geçmişini kaydet
    # ---------------------------------------------------------
    if session.get("user_id"):
        print("USER_ID =", session.get("user_id"))
        print("SAVE ANALYSIS START")

        save_analysis(
        user_id=session["user_id"],
        district=district,
        neighborhood=neighborhood,
        room_count=room_count,
        rent_price=rent_price,
        net_m2=net_m2,
        fair_rent_score=result["fair_rent_score"],
        status=result["status"]
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

    if session.get("user_id"):

        save_analysis(
            user_id=session["user_id"],
            district=district,
            neighborhood=neighborhood,
            room_count=room_count,
            rent_price=rent_price,
            net_m2=net_m2,
            fair_rent_score=result["fair_rent_score"],
            status=result["status"]
        )

    return jsonify(result)

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")




# ---------------------------------------------------------
# UYGULAMA BAŞLATMA
# Flask geliştirme sunucusunu çalıştırır.
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5001)


print(app.url_map)

#---------------------------------------
#Yardımcı Fonk
#--------------------------------------
