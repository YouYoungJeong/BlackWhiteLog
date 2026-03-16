from db import get_connection, is_favorite_restaurant

def get_restaurant_detail(restaurant_id, user_id=None):
    sql = """
        SELECT
            r.restaurant_id,
            r.name,
            r.description,
            r.road_address,
            r.phone,
            r.business_hours,
            r.status,
            (
                SELECT image_url
                FROM restaurant_images
                WHERE restaurant_id = r.restaurant_id
                ORDER BY sort_order ASC
                LIMIT 1
            ) AS image_url
        FROM restaurants r
        WHERE r.restaurant_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
            row = cursor.fetchone()

            if not row:
                return None

            row["is_favorite"] = False
            row["has_visited"] = False
            row["has_reviewed_latest_visit"] = False
            
            if user_id:
                row["is_favorite"] = is_favorite_restaurant(user_id, restaurant_id)

                cursor.execute(
                    "SELECT visit_id FROM visits WHERE user_id=%s AND restaurant_id=%s ORDER BY visited_at DESC LIMIT 1",
                    (user_id, restaurant_id)
                )
                visit_row = cursor.fetchone()

                if visit_row:
                    row["has_visited"] = True
                    latest_visit_id = visit_row["visit_id"]

                    cursor.execute("""
                        SELECT 1
                        FROM reviews
                        WHERE visit_id = %s
                          AND COALESCE(status, 'ACTIVE') = 'ACTIVE'
                        LIMIT 1
                    """, (latest_visit_id,))
                    if cursor.fetchone():
                        row["has_reviewed_latest_visit"] = True
                    
            return row
    finally:
        conn.close()


def get_restaurant_menus(restaurant_id, user_id=None):
    """특정 음식점의 메뉴 목록 + 현재 유저가 먹은 메뉴 여부를 가져오는 함수"""
    effective_user_id = user_id if user_id else 0

    sql = """
        SELECT
            rm.menu_id,
            rm.menu_name,
            rm.price,
            COALESCE(uvm.eaten_count, 0) AS eaten_count,
            CASE
                WHEN uvm.menu_id IS NULL THEN 0
                ELSE 1
            END AS has_eaten
        FROM restaurant_menus rm
        LEFT JOIN (
            SELECT
                vm.menu_id,
                SUM(vm.quantity) AS eaten_count
            FROM visit_menus vm
            INNER JOIN visits v
                ON vm.visit_id = v.visit_id
            WHERE v.user_id = %s
              AND v.restaurant_id = %s
            GROUP BY vm.menu_id
        ) uvm
            ON rm.menu_id = uvm.menu_id
        WHERE rm.restaurant_id = %s
        ORDER BY rm.menu_id ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (effective_user_id, restaurant_id, restaurant_id))
            rows = cursor.fetchall()

            for row in rows:
                row["price"] = int(row["price"] or 0)
                row["eaten_count"] = int(row.get("eaten_count") or 0)
                row["has_eaten"] = bool(row.get("has_eaten", 0))

            return rows
    finally:
        conn.close()