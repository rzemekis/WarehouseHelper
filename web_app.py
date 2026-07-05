import logging
import sqlite3
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

from bot_code import STATUSES, init_db
from config import DB_PATH

LOG_PATH = Path("telegram_bot.log")


app = Flask(__name__)


def ensure_db():
    import asyncio

    asyncio.run(init_db())


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def parse_order_text(full_description):
    description = full_description.strip()
    client_type = ""

    if "ООО" in full_description:
        parts = full_description.split("ООО", 1)
        description = parts[0].strip()
        client_type = "ООО " + parts[1].strip()
    elif "ИП" in full_description:
        parts = full_description.split("ИП", 1)
        description = parts[0].strip()
        client_type = "ИП " + parts[1].strip()

    return description, client_type


def fetch_orders():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT order_id, description, client_type, status, is_paid, comment
            FROM orders
            ORDER BY order_id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def status_label(status):
    return dict(STATUSES).get(status, "Статус не назначен")


def read_logs():
    if not LOG_PATH.exists():
        return "Логи пока пустые. Запустите бота через main.py, и события появятся здесь."

    text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()[-250:]
    return "\n".join(lines) if lines else "Логи пока пустые."


@app.context_processor
def inject_helpers():
    return {
        "statuses": STATUSES,
        "status_label": status_label,
    }


@app.route("/")
def index():
    return redirect(url_for("orders"))


@app.route("/orders")
def orders():
    return render_template("orders.html", active_tab="orders", orders=fetch_orders())


@app.route("/add", methods=["GET", "POST"])
def add_order():
    error = None

    if request.method == "POST":
        order_id = request.form.get("order_id", "").strip()
        full_description = request.form.get("description", "").strip()
        is_paid = 1 if request.form.get("is_paid") == "on" else 0
        comment = request.form.get("comment", "").strip()

        if not order_id or not full_description:
            error = "Заполните номер и описание заказа."
        else:
            description, client_type = parse_order_text(full_description)
            try:
                with get_connection() as connection:
                    connection.execute(
                        """
                        INSERT INTO orders (
                            order_id, description, client_type, status,
                            is_paid, message_id, chat_id, comment
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (order_id, description, client_type, "", is_paid, 0, 0, comment),
                    )
                logging.info("Web: created order %s", order_id)
                return redirect(url_for("orders"))
            except sqlite3.IntegrityError:
                error = "Заказ с таким номером уже есть."

    return render_template("add_order.html", active_tab="add", error=error)


@app.post("/orders/<order_id>/update")
def update_order(order_id):
    status = request.form.get("status", "")
    is_paid = 1 if request.form.get("is_paid") == "on" else 0
    comment = request.form.get("comment", "").strip()

    with get_connection() as connection:
        connection.execute(
            "UPDATE orders SET status = ?, is_paid = ?, comment = ? WHERE order_id = ?",
            (status, is_paid, comment, order_id),
        )

    logging.info("Web: updated order %s", order_id)
    return redirect(url_for("orders"))


@app.post("/orders/<order_id>/delete")
def delete_order(order_id):
    with get_connection() as connection:
        connection.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))

    logging.info("Web: deleted order %s", order_id)
    return redirect(url_for("orders"))


@app.route("/logs")
def logs():
    return render_template("logs.html", active_tab="logs", logs=read_logs())


@app.route("/about")
def about():
    return render_template("about.html", active_tab="about")
