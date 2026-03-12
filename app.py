from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
import os

from db import fetch_categories, fetch_regions, fetch_restaurants

load_dotenv()

app = Flask(__name__)

#### 레스토랑 판넬 블루프린트(모듈화)  
from restaurant_panel import restaurant_panel_bp  # 분리한 파일 임포트
app.register_blueprint(restaurant_panel_bp) # 앱에 등록
#### 레스토랑 판넬 블루프린트(모듈화)

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


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "True") == "True")