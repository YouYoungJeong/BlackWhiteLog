from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
import os

from db import fetch_categories, fetch_regions, fetch_restaurants

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")


@app.route("/")
def index():
    regions = ["전체"] + fetch_regions()
    categories = fetch_categories()
    return render_template("index.html", regions=regions, categories=categories)


@app.route("/api/restaurants")
def api_restaurants():
    region = request.args.get("region", default="전체", type=str)
    keyword = request.args.get("keyword", default="", type=str).strip()
    category_id = request.args.get("category_id", default="", type=str).strip()
    sort_by = request.args.get("sort_by", default="visits", type=str)

    items = fetch_restaurants(
        region=region,
        keyword=keyword,
        category_id=category_id if category_id else None,
        sort_by=sort_by,
    )
    return jsonify(items)

# Owner 보드 route
@app.route("/owner/board")
def owner_board():
    return render_template("owner_board.html")

# Oner 메뉴관리 route
@app.route("/owner/menu_management")
def owner_menu_management():
    return render_template("owner_menu_management.html")

# Oner 리뷰관리 route
@app.route("/owner/review_management")
def owner_review_management():
    return render_template("owner_review_management.html")


# Oner 공지사항 route
@app.route("/owner/notice_management")
def owner_notice_management():
    return render_template("owner_notice_management.html")


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "True") == "True")