from flask import render_template, request, redirect, url_for
import owner_db


def register_owner_routes(app):

    @app.route("/owner/board", endpoint="owner_board")
    def owner_board():
        return render_template("owner/owner_board.html")

    @app.route("/owner/menu_management", methods=["GET", "POST"], endpoint="owner_menu_management")
    def owner_menu_management():
        owner_id = 1

        if request.method == "POST":
            menu_name = request.form.get("menu_name", "").strip()
            price = request.form.get("price", "").strip()
            menu_category_id = request.form.get("menu_category_id", "").strip()

            soldout = request.form.get("soldout")
            status = "OFF" if soldout else "ON"

            if menu_name and price and menu_category_id:
                owner_db.insert_menu(
                    owner_id=owner_id,
                    menu_category_id=menu_category_id,
                    menu_name=menu_name,
                    price=price,
                    status=status
                )

            return redirect(url_for("owner_menu_management"))

        owner = owner_db.get_owner_info(owner_id)
        restaurant = owner_db.get_restaurant_id_by_owner(owner_id)
        categories = owner_db.get_menu_categories()
        menu_list = owner_db.get_menu_list_by_owner(owner_id)

        return render_template(
            "owner/owner_menu_management.html",
            owner=owner,
            restaurant=restaurant,
            categories=categories,
            menu_list=menu_list
        )

    @app.route("/owner/review_management", endpoint="owner_review_management")
    def owner_review_management():
        return render_template("owner/owner_review_management.html")

    @app.route("/owner/notice_management", endpoint="owner_notice_management")
    def owner_notice_management():
        return render_template("owner/owner_notice_management.html")