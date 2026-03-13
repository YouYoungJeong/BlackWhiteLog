import os
import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database="bwlog",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


def get_owner_info(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT owner_id, owner_name, email, status
                FROM owners
                WHERE owner_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (owner_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_restaurant_id_by_owner(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT restaurant_id, name, status
                FROM restaurants
                WHERE owner_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (owner_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_menu_categories():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT menu_category_id, menu_category_name
                FROM menu_categories
                ORDER BY menu_category_id ASC
            """
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()


def get_menu_list_by_owner(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    rm.menu_id,
                    rm.menu_name,
                    rm.price,
                    rm.status,
                    rm.created_at,
                    mc.menu_category_name
                FROM restaurant_menus rm
                INNER JOIN restaurants r
                    ON rm.restaurant_id = r.restaurant_id
                LEFT JOIN menu_categories mc
                    ON rm.menu_category_id = mc.menu_category_id
                WHERE r.owner_id = %s
                ORDER BY rm.menu_id DESC
            """
            cursor.execute(sql, (owner_id,))
            return cursor.fetchall()
    finally:
        conn.close()


def insert_menu(owner_id, menu_category_id, menu_name, price, status="ON"):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            restaurant_sql = """
                SELECT restaurant_id
                FROM restaurants
                WHERE owner_id = %s
                LIMIT 1
            """
            cursor.execute(restaurant_sql, (owner_id,))
            restaurant = cursor.fetchone()

            if not restaurant:
                raise ValueError("해당 owner_id에 연결된 restaurant가 없습니다.")

            insert_sql = """
                INSERT INTO restaurant_menus
                (
                    restaurant_id,
                    menu_category_id,
                    menu_name,
                    price,
                    status
                )
                VALUES
                (
                    %s, %s, %s, %s, %s
                )
            """
            cursor.execute(
                insert_sql,
                (
                    restaurant["restaurant_id"],
                    menu_category_id,
                    menu_name,
                    price,
                    status
                )
            )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()