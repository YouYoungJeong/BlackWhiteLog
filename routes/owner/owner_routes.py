from flask import render_template, request, redirect, url_for
import routes.owner.owner_db as owner_db
import math


def register_owner_routes(app):
# -------------------------------------------------------------------------------------
# 오너 보드 페이지
# -------------------------------------------------------------------------------------
    @app.route("/owner/board", endpoint="owner_board")
    def owner_board():
        return render_template("owner/owner_board.html")





# --------------------------------------------------------------------------------------
# 오너 메뉴 관리 페이지
# --------------------------------------------------------------------------------------
    @app.route("/owner/menu_management", methods=["GET", "POST"], endpoint="owner_menu_management")
    def owner_menu_management():
        # 임시 오너 id
        owner_id = 1
        #수정 menu_id 받기
        edit_menu_id = request.args.get("edit_menu_id", type=int)
        edit_menu = None

        # 등록된 메뉴 카드 페이징 처리용 기본값
        per_page = 5
        page = request.args.get("page", 1, type=int)

        # page 예외 방지
        if not page or page < 1:
            page = 1

        if request.method == "POST":
            menu_id = request.form.get("menu_id", "").strip()
            menu_name = request.form.get("menu_name", "").strip()
            price = request.form.get("price", "").strip()
            menu_category_id = request.form.get("menu_category_id", "").strip()

            soldout = request.form.get("soldout")
            status = "OFF" if soldout else "ON"

            # 메뉴 수정 : menu_id가 있으면 UPDATE
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

            # 메뉴 추가 : menu_id가 없으면 INSERT
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

        # 항상 조회되어야 하는 값들
        owner = owner_db.get_owner_info(owner_id)
        restaurant = owner_db.get_restaurant_id_by_owner(owner_id)
        categories = owner_db.get_menu_categories()
        menu_list = owner_db.get_menu_list_by_owner(owner_id)
        
        # 페이징 전체 메뉴 개수 조회
        total_menu_count = owner_db.get_menu_count_by_owner(owner_id)

        # 페이징 전체 페이지 수 계산
        total_pages = math.ceil(total_menu_count / per_page) if total_menu_count > 0 else 1

        # 페이징 page가 총 페이지보다 크면 마지막 페이지로 보정
        if page > total_pages:
            page = total_pages

        # 페이징 LIMIT / OFFSET 계산
        offset = (page - 1) * per_page

        # 현재 페이지 메뉴만 조회
        menu_list = owner_db.get_menu_list_by_owner(
            owner_id=owner_id,
            limit=per_page,
            offset=offset
        )

        return render_template(
            "owner/owner_menu_management.html",
            owner=owner,
            restaurant=restaurant,
            categories=categories,
            menu_list=menu_list,
            edit_menu=edit_menu,
            current_page=page,
            total_pages=total_pages,
            has_prev=page > 1,
            has_next=page < total_pages
        )

        # 삭제 전용 라우트
    @app.route("/owner/menu/<int:menu_id>/delete", methods=["POST"], endpoint="delete_menu")
    def delete_menu(menu_id):
        owner_id = 1
        owner_db.delete_menu(owner_id, menu_id)
        return redirect(url_for("owner_menu_management"))


# -------------------------------------------------------------------------------------
# 오너 공지 관리 페이지
# -------------------------------------------------------------------------------------

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


# ------------------------------------------------------------------------------------
# 오너 리뷰 관리 페이지
# -----------------------------------------------------------------------------------
    @app.route("/owner/review_management", endpoint="owner_review_management")
    def owner_review_management():
        return render_template("owner/owner_review_management.html")
