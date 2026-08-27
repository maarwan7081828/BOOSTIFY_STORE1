from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "BOOSTIFY_LOCAL_SECRET_KEY_2026_CHANGE_ME"
)

DATABASE = "boostify.db"

# =========================================================
# TELEGRAM
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


def send_telegram_message(message):

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN is missing")
        return False

    if not CHAT_ID:
        print("❌ CHAT_ID is missing")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=15
        )

        print("TELEGRAM STATUS:", response.status_code)
        print("TELEGRAM RESPONSE:", response.text)

        if response.ok:
            return response.json().get("ok", False)

        return False

    except requests.RequestException as e:
        print("Telegram Error:", str(e))
        return False


# =========================================================
# DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL DEFAULT '',
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# SECURITY
# =========================================================

def is_safe_url(target):

    if not target:
        return False

    parsed = urlparse(target)

    return (
        parsed.scheme == ""
        and parsed.netloc == ""
        and target.startswith("/")
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    conn = get_db()

    conn.execute(
        "INSERT INTO visitors DEFAULT VALUES"
    )

    conn.commit()
    conn.close()

    return render_template("index.html")


# =========================================================
# SERVICES
# =========================================================

@app.route("/services")
def services():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next="/services"
            )
        )

    return render_template("services.html")


# =========================================================
# SUBSCRIPTIONS
# =========================================================

@app.route("/subscriptions")
def subscriptions():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next="/subscriptions"
            )
        )

    return render_template("subscriptions.html")


# =========================================================
# CONTACT
# =========================================================

@app.route("/contact")
def contact():

    return render_template("contact.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    next_page = (
        request.args.get("next")
        or request.form.get("next")
        or "/"
    )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            session["phone"] = user["phone"]

            if is_safe_url(next_page):
                return redirect(next_page)

            return redirect(
                url_for("home")
            )

        return render_template(
            "login.html",
            error="البريد الإلكتروني أو كلمة المرور غير صحيحة.",
            next=next_page
        )

    return render_template(
        "login.html",
        next=next_page
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    next_page = (
        request.args.get("next")
        or request.form.get("next")
        or "/"
    )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not email or not phone or not password:

            return render_template(
                "register.html",
                error="من فضلك املأ جميع البيانات.",
                next=next_page
            )

        if password != confirm_password:

            return render_template(
                "register.html",
                error="كلمتا المرور غير متطابقتين.",
                next=next_page
            )

        if len(password) < 6:

            return render_template(
                "register.html",
                error="كلمة المرور يجب أن تكون 6 أحرف على الأقل.",
                next=next_page
            )

        hashed_password = generate_password_hash(
            password
        )

        conn = get_db()

        try:

            cursor = conn.execute(
                """
                INSERT INTO users
                (name, email, phone, password)
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    phone,
                    hashed_password
                )
            )

            conn.commit()

            user_id = cursor.lastrowid

            session.clear()

            session["user_id"] = user_id
            session["name"] = name
            session["email"] = email
            session["phone"] = phone

        except sqlite3.IntegrityError:

            conn.close()

            return render_template(
                "register.html",
                error="البريد الإلكتروني ده مسجل بالفعل.",
                next=next_page
            )

        conn.close()

        if is_safe_url(next_page):
            return redirect(next_page)

        return redirect(
            url_for("home")
        )

    return render_template(
        "register.html",
        next=next_page
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# SERVICE NAMES
# =========================================================

SERVICE_NAMES = {

    "followers": "زيادة المتابعين",

    "likes": "Likes & Engagement",

    "views": "المشاهدات",

    "graphic-design": "Graphic Design",

    "paid-ads": "Paid Advertising",

    "social-management": "Social Media Management"
}


# =========================================================
# SERVICE PAGE
# =========================================================

@app.route("/service/<service_name>")
def service_page(service_name):

    if service_name not in SERVICE_NAMES:

        return redirect(
            url_for("services")
        )

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next=f"/service/{service_name}"
            )
        )

    return render_template(
        "service.html",
        service_name=SERVICE_NAMES[service_name],
        service_slug=service_name
    )


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/checkout")
def checkout():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next=request.full_path
            )
        )

    product = request.args.get(
        "product",
        ""
    ).strip()

    duration = request.args.get(
        "duration",
        ""
    ).strip()

    price = request.args.get(
        "price",
        ""
    ).strip()

    service = request.args.get(
        "service",
        ""
    ).strip()

    is_social = service in [
        "followers",
        "likes",
        "views"
    ]

    is_custom = (
        not price
        or price.lower() in [
            "custom",
            "حسب الطلب",
            "تواصل معنا"
        ]
    )

    if product:

        session["pending_order"] = {

            "product": product,

            "duration": duration,

            "price": price,

            "service": service
        }

    pending_order = session.get(
        "pending_order"
    )

    if not pending_order:

        return redirect(
            url_for("services")
        )

    return render_template(
        "checkout.html",

        customer_name=session.get(
            "name",
            ""
        ),

        customer_email=session.get(
            "email",
            ""
        ),

        customer_phone=session.get(
            "phone",
            ""
        ),

        product=pending_order.get(
            "product",
            ""
        ),

        duration=pending_order.get(
            "duration",
            ""
        ),

        price=pending_order.get(
            "price",
            ""
        ),

        service=pending_order.get(
            "service",
            ""
        ),

        is_social=is_social,

        is_custom=is_custom,

        success=None,

        error=None
    )


# =========================================================
# SEND ORDER
# =========================================================

@app.route("/send-order", methods=["POST"])
def send_order():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next="/services"
            )
        )

    product = request.form.get(
        "product",
        ""
    ).strip()

    duration = request.form.get(
        "duration",
        ""
    ).strip()

    price = request.form.get(
        "price",
        ""
    ).strip()

    service = request.form.get(
        "service",
        ""
    ).strip()

    order_details = request.form.get(
        "order_details",
        ""
    ).strip()

    username = request.form.get(
        "username",
        ""
    ).strip()

    account_link = request.form.get(
        "account_link",
        ""
    ).strip()

    payment_method = request.form.get(
        "payment_method",
        ""
    ).strip()

    transfer_phone = request.form.get(
        "transfer_phone",
        ""
    ).strip()

    transfer_amount = request.form.get(
        "transfer_amount",
        ""
    ).strip()

    if not product:

        return redirect(
            url_for("services")
        )

    # -----------------------------------------------------
    # SAVE COMPLETE ORDER
    # -----------------------------------------------------

    session["pending_order"] = {

        "product": product,

        "duration": duration,

        "price": price,

        "service": service,

        "order_details": order_details,

        "username": username,

        "account_link": account_link,

        "payment_method": payment_method,

        "transfer_phone": transfer_phone,

        "transfer_amount": transfer_amount
    }

    # -----------------------------------------------------
    # CUSTOMER
    # -----------------------------------------------------

    customer_name = session.get(
        "name",
        ""
    )

    customer_email = session.get(
        "email",
        ""
    )

    customer_phone = session.get(
        "phone",
        ""
    )

    # -----------------------------------------------------
    # TELEGRAM
    # -----------------------------------------------------

    message = f"""🛒 طلب جديد - BOOSTIFY STORE

━━━━━━━━━━━━━━━━━━

👤 اسم العميل:
{customer_name}

📧 البريد الإلكتروني:
{customer_email}

📱 رقم العميل:
{customer_phone}

━━━━━━━━━━━━━━━━━━

🛠️ القسم:
{service or "غير محدد"}

📦 الخدمة:
{product}

🔢 الباقة / الكمية:
{duration or "غير محدد"}

💰 السعر المطلوب:
{price or "حسب الطلب"} جنيه

━━━━━━━━━━━━━━━━━━

🌐 بيانات الحساب:

Username:
{username or "غير مذكور"}

رابط الحساب:
{account_link or "غير مذكور"}

━━━━━━━━━━━━━━━━━━

📝 تفاصيل الطلب:
{order_details or "لا يوجد"}

━━━━━━━━━━━━━━━━━━

💳 بيانات الدفع:

طريقة الدفع:
{payment_method or "لم يتم تحديدها"}

📱 رقم الهاتف المحول منه:
{transfer_phone or "غير مذكور"}

💰 المبلغ المحول:
{transfer_amount or "غير مذكور"} جنيه

━━━━━━━━━━━━━━━━━━

🟡 حالة الطلب:
تم إرسال الطلب وينتظر مراجعة الدفع

📸 إثبات التحويل:
سيتم إرساله عبر WhatsApp
"""

    sent = send_telegram_message(message)

    # -----------------------------------------------------
    # WHATSAPP
    # -----------------------------------------------------

    whatsapp_number = "201123308826"

    whatsapp_message = f"""مرحباً BOOSTIFY STORE 👋

أريد تأكيد طلبي:

👤 الاسم:
{customer_name}

📦 الخدمة:
{product}

🔢 الباقة / الكمية:
{duration or "غير محدد"}

💰 السعر:
{price or "حسب الطلب"} جنيه

💳 طريقة الدفع:
{payment_method or "غير محددة"}

📱 رقم التحويل:
{transfer_phone or "غير مذكور"}

💰 المبلغ المحول:
{transfer_amount or "غير مذكور"} جنيه

🌐 Username:
{username or "غير مذكور"}

🔗 رابط الحساب:
{account_link or "غير مذكور"}

📝 تفاصيل الطلب:
{order_details or "لا يوجد"}

سأرسل الآن صورة Screenshot لإثبات التحويل.
"""

    whatsapp_url = (
        f"https://wa.me/{whatsapp_number}"
        f"?text={requests.utils.quote(whatsapp_message)}"
    )

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    is_social = service in [
        "followers",
        "likes",
        "views"
    ]

    is_custom = (
        not price
        or price.lower() in [
            "custom",
            "حسب الطلب",
            "تواصل معنا"
        ]
    )

    if sent:

        return render_template(
            "checkout.html",

            customer_name=customer_name,

            customer_email=customer_email,

            customer_phone=customer_phone,

            product=product,

            duration=duration,

            price=price,

            service=service,

            is_social=is_social,

            is_custom=is_custom,

            success=True,

            error=None,

            whatsapp_url=whatsapp_url
        )

    return render_template(
        "checkout.html",

        customer_name=customer_name,

        customer_email=customer_email,

        customer_phone=customer_phone,

        product=product,

        duration=duration,

        price=price,

        service=service,

        is_social=is_social,

        is_custom=is_custom,

        success=False,

        error="حصل خطأ أثناء إرسال الطلب. حاول مرة أخرى.",

        whatsapp_url=whatsapp_url
    )


# =========================================================
# WHATSAPP PROOF
# =========================================================

@app.route("/whatsapp-proof")
def whatsapp_proof():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next="/services"
            )
        )

    pending_order = session.get(
        "pending_order",
        {}
    )

    product = pending_order.get(
        "product",
        "الخدمة"
    )

    price = pending_order.get(
        "price",
        ""
    )

    customer_name = session.get(
        "name",
        ""
    )

    whatsapp_number = "201123308826"

    message = (
        f"مرحباً BOOSTIFY STORE 👋\n\n"
        f"أنا {customer_name}\n"
        f"أرسلت طلب خدمة: {product}\n"
        f"السعر: {price} جنيه\n\n"
        f"وسأرسل الآن صورة إثبات التحويل."
    )

    whatsapp_url = (
        f"https://wa.me/{whatsapp_number}"
        f"?text={requests.utils.quote(message)}"
    )

    return redirect(
        whatsapp_url
    )


# =========================================================
# START
# =========================================================

init_db()

@app.route('/reviews')
def reviews():
    return render_template('reviews.html')
    
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )