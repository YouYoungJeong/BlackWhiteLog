from flask import render_template, request, jsonify, session
import routes.owner.owner_menu_db as owner_db
import routes.owner.owner_notices_db as owner_notice_db
import math



def register_owner_routes(app):
# -------------------------------------------------------------------------------------
# 오너 보드 페이지
# -------------------------------------------------------------------------------------
    @app.route("/owner/board", endpoint="owner_board")
    def owner_board():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        restaurant_menu_list = owner_db.get_menu_count_by_owner(session_owner_id)

        try:
            db_sidebar_restaurant_list = owner_notice_db.get_restaurant_list_by_owner(session_owner_id)

            if db_sidebar_restaurant_list:
                sidebar_selected_restaurant_id = db_sidebar_restaurant_list[0]["restaurant_id"]
                sidebar_selected_restaurant_name = db_sidebar_restaurant_list[0]["name"]
            else:
                sidebar_selected_restaurant_id = None
                sidebar_selected_restaurant_name = ""
                db_sidebar_restaurant_list = []

            db_sidebar_notice_current = None
            db_sidebar_notice_history_list = []

            if sidebar_selected_restaurant_id:
                db_sidebar_notice_current = owner_notice_db.get_notice_list_by_restaurant(
                    sidebar_selected_restaurant_id,
                    limit=1,
                    offset=0
                )

            sidebar_notice_current = None
            if db_sidebar_notice_current:
                for db_notice in db_sidebar_notice_current:
                    if int(db_notice["is_pinned"]) == 1:
                        sidebar_notice_current = {
                            "notice_id": db_notice["notice_id"],
                            "restaurant_id": db_notice["restaurant_id"],
                            "notice_title": db_notice["notice_title"],
                            "notice_content": db_notice["notice_content"],
                            "updated_at": db_notice["updated_at"].strftime("%Y-%m-%d") if db_notice["updated_at"] else ""
                        }
                        break

            if sidebar_selected_restaurant_id:
                db_notice_list = owner_notice_db.get_notice_list_by_restaurant(
                    sidebar_selected_restaurant_id
                )

                for db_notice in db_notice_list:
                    if int(db_notice["is_pinned"]) == 0:
                        db_sidebar_notice_history_list.append({
                            "notice_id": db_notice["notice_id"],
                            "restaurant_id": db_notice["restaurant_id"],
                            "notice_title": db_notice["notice_title"],
                            "notice_content": db_notice["notice_content"],
                            "updated_at": db_notice["updated_at"].strftime("%Y-%m-%d") if db_notice["updated_at"] else ""
                        })

                db_sidebar_notice_history_list = db_sidebar_notice_history_list[:3]

        except Exception:
            db_sidebar_restaurant_list = []
            sidebar_selected_restaurant_id = None
            sidebar_selected_restaurant_name = ""
            sidebar_notice_current = None
            db_sidebar_notice_history_list = []

        return render_template(
            "owner/owner_board.html",
            restaurant_menu_list=restaurant_menu_list,
            session_user_id=session_user_id,
            session_owner_id=session_owner_id,
            sidebar_restaurant_list=db_sidebar_restaurant_list,
            sidebar_selected_restaurant_id=sidebar_selected_restaurant_id,
            sidebar_selected_restaurant_name=sidebar_selected_restaurant_name,
            sidebar_notice_current=sidebar_notice_current,
            sidebar_notice_history_list=db_sidebar_notice_history_list
        )

# --------------------------------------------------------------------------------------
# 오너 메뉴 관리 페이지
# --------------------------------------------------------------------------------------
    # 수정: 메뉴 목록/개수 조회 기준이 owner_id 대신 restaurant_id가 되도록 함수 매개변수 변경
    def build_menu_list_payload(restaurant_id, page=1, per_page=5):
        # 수정: 총 메뉴 개수 조회도 restaurant_id 기준 함수로 변경
        total_menu_count = owner_db.get_menu_count_by_restaurant(restaurant_id)
        total_pages = math.ceil(total_menu_count / per_page) if total_menu_count > 0 else 1

        if page < 1:
            page = 1

        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        # 수정: 메뉴 목록 조회 시 owner_id 대신 restaurant_id 전달
        db_menu_list = owner_db.get_menu_list_by_owner(
            restaurant_id=restaurant_id,
            limit=per_page,
            offset=offset
        )

        menu_list = []
        for db_menu in db_menu_list:
            menu_list.append({
                "menu_id": db_menu["menu_id"],
                "menu_name": db_menu["menu_name"],
                "price": int(db_menu["price"]) if db_menu["price"] is not None else 0,
                "status": db_menu["status"],
                "menu_category_name": db_menu["menu_category_name"] or "",
                "menu_category_id": db_menu["menu_category_id"],
                "image_url": db_menu["image_url"],
                "thumb_url": db_menu["thumb_url"],
                "original_name": db_menu["original_name"]
            })

        return {
            "menu_list": menu_list,
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "total_menu_count": total_menu_count
        }

    # 수정: 오너가 가진 여러 가게 중 현재 선택된 restaurant_id를 결정하는 공통 함수 추가
    def get_selected_restaurant_id(session_owner_id, client_restaurant_id=None):
        restaurant_list = owner_db.get_restaurant_list_by_owner(session_owner_id)

        if not restaurant_list:
            raise ValueError("등록된 가게가 없습니다.")

        restaurant_id_list = [row["restaurant_id"] for row in restaurant_list]

        if client_restaurant_id is not None:
            try:
                selected_restaurant_id = int(client_restaurant_id)
            except (TypeError, ValueError):
                selected_restaurant_id = restaurant_id_list[0]

            if selected_restaurant_id not in restaurant_id_list:
                selected_restaurant_id = restaurant_id_list[0]
        else:
            selected_restaurant_id = restaurant_id_list[0]

        return selected_restaurant_id, restaurant_list

    @app.route("/owner/menu_management", methods=["GET"], endpoint="owner_menu_management")
    def owner_menu_management():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            # 임시 오너값
            session_owner_id = 1

        db_owner = owner_db.get_owner_info(session_owner_id)
        db_categories = owner_db.get_menu_categories()

        selected_restaurant_id, restaurant_list = get_selected_restaurant_id(session_owner_id)

        # 수정: 초기 메뉴 목록도 restaurant_id 기준으로 조회
        initial_payload = build_menu_list_payload(
            restaurant_id=selected_restaurant_id,
            page=1,
            per_page=5
        )

        return render_template(
            "owner/owner_menu_management.html",
            owner=db_owner,
            restaurant_list=restaurant_list,
            selected_restaurant_id=selected_restaurant_id,
            categories=db_categories,
            initial_payload=initial_payload,
            session_user_id=session_user_id,
            session_owner_id=session_owner_id
        )

    @app.route("/owner/menu_management/api/list", methods=["GET"], endpoint="owner_menu_management_api_list")
    def owner_menu_management_api_list():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            # 임시 오너값
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)
        page = request.args.get("page", default=1, type=int)

        selected_restaurant_id, restaurant_list = get_selected_restaurant_id(
            session_owner_id,
            client_restaurant_id
        )

        payload = build_menu_list_payload(
            restaurant_id=selected_restaurant_id,
            page=page,
            per_page=5
        )

        return jsonify({
            "success": True,
            "message": "메뉴 목록 조회 완료",
            "restaurant_id": selected_restaurant_id,
            "restaurant_list": restaurant_list,
            **payload
        })

    @app.route("/owner/menu_management/api/detail/<int:menu_id>", methods=["GET"], endpoint="owner_menu_management_api_detail")
    def owner_menu_management_api_detail(menu_id):
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            # 임시 오너값
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)

        selected_restaurant_id, _ = get_selected_restaurant_id(
            session_owner_id,
            client_restaurant_id
        )

        # 수정: 상세 조회도 owner_id 대신 restaurant_id 기준으로 조회
        db_menu_detail = owner_db.get_menu_detail_by_id(selected_restaurant_id, menu_id)

        if not db_menu_detail:
            return jsonify({
                "success": False,
                "message": "메뉴 정보를 찾을 수 없습니다."
            }), 404

        return jsonify({
            "success": True,
            "message": "메뉴 상세 조회 완료",
            "menu_id": db_menu_detail["menu_id"],
            "restaurant_id": db_menu_detail["restaurant_id"],
            "menu_category_id": db_menu_detail["menu_category_id"],
            "menu_name": db_menu_detail["menu_name"],
            "price": int(db_menu_detail["price"]) if db_menu_detail["price"] is not None else 0,
            "status": db_menu_detail["status"],
            "image_url": db_menu_detail["image_url"],
            "thumb_url": db_menu_detail["thumb_url"],
            "original_name": db_menu_detail["original_name"]
        })

    @app.route("/owner/menu_management/api/save", methods=["POST"], endpoint="owner_menu_management_api_save")
    def owner_menu_management_api_save():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")
        print("request.form =", request.form)
        print("request.files =", request.files)
        if not session_owner_id:
            # 임시 오너값
            session_owner_id = 1

        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_menu_id = request.form.get("client_menu_id", "").strip()
        client_menu_name = request.form.get("client_menu_name", "").strip()
        client_price = request.form.get("client_price", "").strip()
        client_menu_category_id = request.form.get("client_menu_category_id", "").strip()
        client_remove_image = request.form.get("client_remove_image", "").strip()
        client_soldout = request.form.get("client_soldout", "").strip()
        client_page = request.form.get("client_page", default="1").strip()
        client_menu_image = request.files.get("client_menu_image")

        if not client_menu_name or not client_price or not client_menu_category_id:
            return jsonify({
                "success": False,
                "message": "메뉴명, 가격, 카테고리는 필수입니다."
            }), 400

        if client_menu_image and client_menu_image.filename and not owner_db.allowed_file(client_menu_image.filename):
            return jsonify({
                "success": False,
                "message": "허용 확장자: jpg, jpeg, png, gif, webp"
            }), 400

        menu_status = "OFF" if client_soldout == "Y" else "ON"

        try:
            # 수정: 저장/수정 시 owner_id로 restaurant_id를 구해서 restaurant_id 기준 함수에 전달
            restaurant_id, _ = get_selected_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            if client_menu_id:
                owner_db.update_menu(
                    restaurant_id=restaurant_id,
                    menu_id=int(client_menu_id),
                    menu_category_id=int(client_menu_category_id),
                    menu_name=client_menu_name,
                    price=int(client_price),
                    status=menu_status,
                    image_file=client_menu_image,
                    remove_image=True if client_remove_image == "Y" else False
                )

                action_message = "메뉴가 수정되었습니다."
                saved_menu_id = int(client_menu_id)
            else:
                saved_menu_id = owner_db.insert_menu(
                    restaurant_id=restaurant_id,
                    menu_category_id=int(client_menu_category_id),
                    menu_name=client_menu_name,
                    price=int(client_price),
                    status=menu_status,
                    image_file=client_menu_image
                )
                action_message = "메뉴가 등록되었습니다."

            page = int(client_page) if str(client_page).isdigit() else 1
            payload = build_menu_list_payload(
                restaurant_id=restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": action_message,
                "menu_id": saved_menu_id,
                "restaurant_id": restaurant_id,
                "session_user_id": session_user_id,
                "session_owner_id": session_owner_id,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500

    @app.route("/owner/menu_management/api/delete/<int:menu_id>", methods=["POST"], endpoint="owner_menu_management_api_delete")
    def owner_menu_management_api_delete(menu_id):
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            # 임시 오너값
            session_owner_id = 1

        client_page = request.form.get("client_page", default="1").strip()
        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()

        try:
            # 수정: 삭제도 owner_id로 restaurant_id를 조회해서 restaurant_id 기준으로 삭제
            restaurant_id, _ = get_selected_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            owner_db.delete_menu(restaurant_id, menu_id)

            page = int(client_page) if str(client_page).isdigit() else 1
            payload = build_menu_list_payload(
                restaurant_id=restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": "메뉴가 삭제되었습니다.",
                "menu_id": menu_id,
                "restaurant_id": restaurant_id,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500


# -------------------------------------------------------------------------------------
# 오너 공지 관리 페이지
# -------------------------------------------------------------------------------------
    # 공지사항 목록 payload 생성
    # - restaurant_id 기준으로 공지 목록/페이지/개수를 공통 계산한다.
    # - SPA 응답용 JSON 구성 중복을 줄이기 위해 분리한다.
    def build_notice_list_payload(restaurant_id, page=1, per_page=5):
        total_notice_count = owner_notice_db.get_notice_count_by_restaurant(restaurant_id)
        total_pages = math.ceil(total_notice_count / per_page) if total_notice_count > 0 else 1

        if page < 1:
            page = 1

        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        db_notice_list = owner_notice_db.get_notice_list_by_restaurant(
            restaurant_id=restaurant_id,
            limit=per_page,
            offset=offset
        )

        notice_list = []
        for db_notice in db_notice_list:
            notice_list.append({
                "notice_id": db_notice["notice_id"],
                "owner_id": db_notice["owner_id"],
                "restaurant_id": db_notice["restaurant_id"],
                "user_id": db_notice["user_id"],
                "notice_url": db_notice["notice_url"],
                "thumb_url": db_notice["thumb_url"],
                "notice_title": db_notice["notice_title"],
                "notice_content": db_notice["notice_content"],
                "is_pinned": int(db_notice["is_pinned"]) if db_notice["is_pinned"] is not None else 0,
                "created_at": db_notice["created_at"].strftime("%Y-%m-%d") if db_notice["created_at"] else "",
                "updated_at": db_notice["updated_at"].strftime("%Y-%m-%d") if db_notice["updated_at"] else ""
            })

        return {
            "notice_list": notice_list,
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "total_notice_count": total_notice_count
        }

    # 공지사항 화면에서 선택된 식당 공통 처리
    def get_selected_notice_restaurant_id(session_owner_id, client_restaurant_id=None):
        restaurant_list = owner_notice_db.get_restaurant_list_by_owner(session_owner_id)

        if not restaurant_list:
            raise ValueError("등록된 가게가 없습니다.")

        restaurant_id_list = [row["restaurant_id"] for row in restaurant_list]

        if client_restaurant_id is not None:
            try:
                selected_restaurant_id = int(client_restaurant_id)
            except (TypeError, ValueError):
                selected_restaurant_id = restaurant_id_list[0]

            if selected_restaurant_id not in restaurant_id_list:
                selected_restaurant_id = restaurant_id_list[0]
        else:
            selected_restaurant_id = restaurant_id_list[0]

        return selected_restaurant_id, restaurant_list

    @app.route("/owner/notice_management", methods=["GET"], endpoint="owner_notice_management")
    def owner_notice_management():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        selected_restaurant_id, restaurant_list = get_selected_notice_restaurant_id(session_owner_id)

        initial_payload = build_notice_list_payload(
            restaurant_id=selected_restaurant_id,
            page=1,
            per_page=5
        )

        return render_template(
            "owner/owner_notice_management.html",
            restaurant_list=restaurant_list,
            selected_restaurant_id=selected_restaurant_id,
            initial_payload=initial_payload,
            session_user_id=session_user_id,
            session_owner_id=session_owner_id
        )

    @app.route("/owner/notice_management/api/list", methods=["GET"], endpoint="owner_notice_management_api_list")
    def owner_notice_management_api_list():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)
        page = request.args.get("page", default=1, type=int)

        try:
            selected_restaurant_id, restaurant_list = get_selected_notice_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            payload = build_notice_list_payload(
                restaurant_id=selected_restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": "공지사항 목록 조회 완료",
                "restaurant_id": selected_restaurant_id,
                "restaurant_list": restaurant_list,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500

    @app.route("/owner/notice_management/api/detail/<int:notice_id>", methods=["GET"], endpoint="owner_notice_management_api_detail")
    def owner_notice_management_api_detail(notice_id):
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)

        try:
            selected_restaurant_id, _ = get_selected_notice_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            db_notice = owner_notice_db.get_notice_detail_by_id(selected_restaurant_id, notice_id)

            if not db_notice:
                return jsonify({
                    "success": False,
                    "message": "공지사항 정보를 찾을 수 없습니다."
                }), 404

            return jsonify({
                "success": True,
                "message": "공지사항 상세 조회 완료",
                "notice_id": db_notice["notice_id"],
                "owner_id": db_notice["owner_id"],
                "restaurant_id": db_notice["restaurant_id"],
                "user_id": db_notice["user_id"],
                "notice_url": db_notice["notice_url"],
                "thumb_url": db_notice["thumb_url"],
                "notice_title": db_notice["notice_title"],
                "notice_content": db_notice["notice_content"],
                "is_pinned": int(db_notice["is_pinned"]) if db_notice["is_pinned"] is not None else 0,
                "created_at": db_notice["created_at"].strftime("%Y-%m-%d") if db_notice["created_at"] else "",
                "updated_at": db_notice["updated_at"].strftime("%Y-%m-%d") if db_notice["updated_at"] else ""
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500

    @app.route("/owner/notice_management/api/save", methods=["POST"], endpoint="owner_notice_management_api_save")
    def owner_notice_management_api_save():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_notice_id = request.form.get("client_notice_id", "").strip()
        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_notice_title = request.form.get("client_notice_title", "").strip()
        client_notice_content = request.form.get("client_notice_content", "").strip()
        client_is_pinned = request.form.get("client_is_pinned", "").strip()
        client_remove_image = request.form.get("client_remove_image", "").strip()
        client_page = request.form.get("client_page", default="1").strip()
        client_notice_image = request.files.get("client_notice_image")

        if not client_notice_title or not client_notice_content:
            return jsonify({
                "success": False,
                "message": "공지사항 제목과 내용은 필수입니다."
            }), 400

        if client_notice_image and client_notice_image.filename and not owner_notice_db.allowed_file(client_notice_image.filename):
            return jsonify({
                "success": False,
                "message": "허용 확장자: jpg, jpeg, png, gif, webp"
            }), 400

        try:
            restaurant_id, _ = get_selected_notice_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            is_pinned = 1 if client_is_pinned == "Y" else 0

            if client_notice_id:
                owner_notice_db.update_notice(
                    restaurant_id=restaurant_id,
                    notice_id=int(client_notice_id),
                    notice_title=client_notice_title,
                    notice_content=client_notice_content,
                    is_pinned=is_pinned,
                    image_file=client_notice_image,
                    remove_image=True if client_remove_image == "Y" else False
                )
                saved_notice_id = int(client_notice_id)
                action_message = "공지사항이 수정되었습니다."
            else:
                saved_notice_id = owner_notice_db.insert_notice(
                    owner_id=session_owner_id,
                    restaurant_id=restaurant_id,
                    user_id=session_user_id,
                    notice_title=client_notice_title,
                    notice_content=client_notice_content,
                    is_pinned=is_pinned,
                    image_file=client_notice_image
                )
                action_message = "공지사항이 등록되었습니다."

            page = int(client_page) if str(client_page).isdigit() else 1
            payload = build_notice_list_payload(
                restaurant_id=restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": action_message,
                "notice_id": saved_notice_id,
                "restaurant_id": restaurant_id,
                "session_user_id": session_user_id,
                "session_owner_id": session_owner_id,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500

    @app.route("/owner/notice_management/api/delete/<int:notice_id>", methods=["POST"], endpoint="owner_notice_management_api_delete")
    def owner_notice_management_api_delete(notice_id):
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_page = request.form.get("client_page", default="1").strip()

        try:
            restaurant_id, _ = get_selected_notice_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            owner_notice_db.delete_notice(restaurant_id, notice_id)

            page = int(client_page) if str(client_page).isdigit() else 1
            payload = build_notice_list_payload(
                restaurant_id=restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": "공지사항이 삭제되었습니다.",
                "notice_id": notice_id,
                "restaurant_id": restaurant_id,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500




# ------------------------------------------------------------------------------------
# 오너 리뷰 관리 페이지
# -----------------------------------------------------------------------------------
    @app.route("/owner/review_management", endpoint="owner_review_management")
    def owner_review_management():
        return render_template("owner/owner_review_management.html")