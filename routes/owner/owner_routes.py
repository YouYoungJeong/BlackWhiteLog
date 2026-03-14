from flask import render_template, request, redirect, url_for
import routes.owner.owner_db as owner_db


def register_owner_routes(app):

    @app.route("/owner/board", endpoint="owner_board")
    def owner_board():
        return render_template("owner/owner_board.html")

    @app.route("/owner/menu_management", methods=["GET", "POST"], endpoint="owner_menu_management")
    def owner_menu_management():
        # 임시 오너 id
        owner_id = 1
        #수정 menu_id 받기
        edit_menu_id = request.args.get("edit_menu_id", type=int)
        edit_menu = None


        if request.method == "POST":
            menu_id = request.form.get("menu_id", "").strip()
            menu_name = request.form.get("menu_name", "").strip()
            price = request.form.get("price", "").strip()
            menu_category_id = request.form.get("menu_category_id", "").strip()

            soldout = request.form.get("soldout")
            status = "OFF" if soldout else "ON"

            # 수정 : menu_id가 있으면 UPDATE
            if menu_id and menu_name and price and menu_category_id:
                owner_db.update_menu(
                    owner_id=owner_id,
                    menu_id=menu_id,
                    menu_category_id=menu_category_id,
                    menu_name=menu_name,
                    price=price,
                    status=status
                )
                return redirect(url_for("owner_menu_management"))            

            # 추가 : menu_id가 없으면 INSERT
            if menu_name and price and menu_category_id:
                owner_db.insert_menu(
                    owner_id=owner_id,
                    menu_category_id=menu_category_id,
                    menu_name=menu_name,
                    price=price,
                    status=status
                )

            return redirect(url_for("owner_menu_management"))
        
        # 수정 모드일 때만 수정 대상 메뉴 1건 조회
        if edit_menu_id:
            edit_menu = owner_db.get_menu_detail_by_id(owner_id, edit_menu_id)

        # 항상 조회되어야 하는 값들은 조건문 밖에서 선언
        owner = owner_db.get_owner_info(owner_id)
        restaurant = owner_db.get_restaurant_id_by_owner(owner_id)
        categories = owner_db.get_menu_categories()
        menu_list = owner_db.get_menu_list_by_owner(owner_id)

        return render_template(
            "owner/owner_menu_management.html",
            owner=owner,
            restaurant=restaurant,
            categories=categories,
            menu_list=menu_list,
            edit_menu=edit_menu
        )

        # [추가] 삭제 전용 라우트
    @app.route("/owner/menu/<int:menu_id>/delete", methods=["POST"], endpoint="delete_menu")
    def delete_menu(menu_id):
        owner_id = 1
        owner_db.delete_menu(owner_id, menu_id)
        return redirect(url_for("owner_menu_management"))

    @app.route("/owner/notice_management", endpoint="owner_notice_management")
    def owner_notice_management():
        return render_template("owner/owner_notice_management.html")

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
