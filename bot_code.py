import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.enums import ParseMode
from aiogram.filters import Command
import uuid

API_TOKEN = "8162450268:AAGAbfDgZuhGz_uF_Zz01nbIlnSHBWqOvN8"
DB_PATH = "orders.db"

STATUSES = [
    ("accepted", "Заказ в работе"),
    ("packed", "Собран"),
    ("logistics", "Курьер заказан"),
    ("shipped", "Заказ отгружен"),
]

STATUS_EMOJIS = {
    "accepted": "🛠️",
    "packed": "📦",
    "logistics": "🚚",
    "shipped": "✅",
}

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                description TEXT,
                client_type TEXT,
                status TEXT,
                is_paid INTEGER,
                message_id INTEGER,
                chat_id INTEGER,
                comment TEXT DEFAULT ''
            )
        """)
        await db.commit()

def build_order_message(order):
    emoji = STATUS_EMOJIS.get(order["status"], "❓")
    status_label = dict(STATUSES).get(order["status"], "Статус не назначен")
    paid_text = "✅" if order["is_paid"] else "❌"

    client_type = order.get("client_type", "")
    client_name = order.get("client_name", "")

    client_text = client_type.strip()

    return f"""🧾 Заказ #{order["order_id"]}
📄 {order["description"]}

👤 Клиент: {client_text}

📦 Статус: {emoji} {status_label if order["status"] else "Статус не назначен"}
💰 Оплачен: {paid_text}

💬 Комментарий: {order.get("comment", "")}
"""


def build_inline_keyboard(order):
    status_keys = [key for key, _ in STATUSES]
    try:
        current_index = status_keys.index(order["status"])
    except ValueError:
        current_index = -1

    status_buttons = []
    for i, (key, label) in enumerate(STATUSES):
        if i < current_index:
            status_buttons.append(InlineKeyboardButton(text=label, callback_data="noop"))
        elif i == current_index:
            status_buttons.append(InlineKeyboardButton(
                text=f"{label} (отменить)",
                callback_data=f"undo_status:{order['order_id']}"
            ))
        elif i == current_index + 1:
            status_buttons.append(InlineKeyboardButton(
                text=label,
                callback_data=f"status:{order['order_id']}:{key}"
            ))
        else:
            status_buttons.append(InlineKeyboardButton(text=label, callback_data="noop"))

    paid_button = InlineKeyboardButton(
        text="Оплачен / Не оплачен",
        callback_data=f"paid_toggle:{order['order_id']}"
    )
    delete_button = InlineKeyboardButton(
        text="Удалить заказ",
        callback_data=f"delete_order:{order['order_id']}"
    )

    status_rows = [status_buttons[i:i + 2] for i in range(0, len(status_buttons), 2)]

    return InlineKeyboardMarkup(inline_keyboard=status_rows + [[paid_button, delete_button]])


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для отслеживания заказов.\n"
        "✅ Используй команду:\n"
        "`/new_order <номер> <описание> ИП/ООО <Фамилия>`\n"
        "Пример:\n"
        "`/new_order 123456 Очки серые 5шт ИП Троян`",
        parse_mode=ParseMode.MARKDOWN
    )


@dp.message(Command("new_order"))
async def cmd_new_order(message: Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.answer("Формат: /new_order <номер> <описание> <клиент>")
            return

        order_id = args[1]
        full_description = args[2]

        client_type = ""
        client_name = ""
        description = full_description

        if "ООО" in full_description:
            parts = full_description.split("ООО", 1)
            description = parts[0].strip()
            client_type = "ООО " + parts[1].strip()
        elif "ИП" in full_description:
            parts = full_description.split("ИП", 1)
            description = parts[0].strip()
            client_type = "ИП " + parts[1].strip()

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,))
            existing = await cursor.fetchone()
            if existing:
                await message.answer("Такой заказ уже есть")
                return

            await db.execute("""
                INSERT INTO orders (order_id, description, client_type, status, is_paid, message_id, chat_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (order_id, description, client_type, "", 0, 0, 0))
            await db.commit()

        order = {
            "order_id": order_id,
            "description": description,
            "client_type": client_type,
            "status": "",
            "is_paid": 0
        }

        text = build_order_message(order)
        keyboard = build_inline_keyboard(order)
        msg = await message.answer(text, reply_markup=keyboard)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET message_id = ?, chat_id = ? WHERE order_id = ?",
                             (msg.message_id, msg.chat.id, order_id))
            await db.commit()

    except Exception as e:
        print("Ошибка в /new_order:", e)
        await message.answer("Произошла ошибка при создании заказа")


@dp.message(Command("comment"))
async def cmd_comment(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Формат: /comment <номер заказа> <текст комментария>")
        return

    order_id = args[1]
    new_comment = args[2]

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = await cursor.fetchone()
        if not row:
            await message.answer("Заказ не найден")
            return

        await db.execute("UPDATE orders SET comment = ? WHERE order_id = ?", (new_comment, order_id))
        await db.commit()

    message_id = row[5]
    chat_id = row[6]

    order = {
        "order_id": row[0],
        "description": row[1],
        "client_type": row[2],
        "status": row[3],
        "is_paid": row[4],
        "message_id": message_id,
        "chat_id": chat_id,
        "comment": new_comment,
    }

    text = build_order_message(order)
    keyboard = build_inline_keyboard(order)

    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
    except Exception as e:
        print("Ошибка при обновлении сообщения с заказом:", e)

    await message.answer(f"Комментарий для заказа #{order_id} успешно обновлён.")


@dp.message(Command("list_orders"))
async def cmd_list_orders(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT order_id, client_type FROM orders")
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("Пока нет заказов.")
        return

    buttons = [
        InlineKeyboardButton(
            text=f"#{order_id} — {client_type}" if client_type else f"#{order_id}",
            callback_data=f"show_order:{order_id}"
        ) for (order_id, client_type) in rows
    ]

    rows_buttons = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows_buttons)
    await message.answer("Выберите заказ:", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("show_order:"))
async def show_order_card(callback: CallbackQuery):
    order_id = callback.data.split(":", 1)[1]
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = await cursor.fetchone()

    if not row:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    order = {
        "order_id": row[0],
        "description": row[1],
        "client_type": row[2],
        "status": row[3],
        "is_paid": row[4],
        "message_id": row[5],
        "chat_id": row[6],
        "comment": row[7] if len(row) > 7 else ""
    }

    text = build_order_message(order)
    keyboard = build_inline_keyboard(order)

    if order["message_id"] and order["chat_id"]:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=order["chat_id"],
                message_id=order["message_id"],
                reply_markup=keyboard
            )
        except Exception:
            msg = await callback.message.answer(text, reply_markup=keyboard)
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE orders SET message_id = ?, chat_id = ? WHERE order_id = ?",
                                 (msg.message_id, msg.chat.id, order_id))
                await db.commit()
    else:
        msg = await callback.message.answer(text, reply_markup=keyboard)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET message_id = ?, chat_id = ? WHERE order_id = ?",
                             (msg.message_id, msg.chat.id, order_id))
            await db.commit()

    await callback.answer()


@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    data = callback.data

    if data == "noop":
        await callback.answer()
        return

    elif data.startswith("status:"):
        _, order_id, new_status = data.split(":")

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
            row = await cursor.fetchone()
            if not row:
                await callback.answer("Заказ не найден")
                return
            await db.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))
            await db.commit()

        order = {
            "order_id": row[0],
            "description": row[1],
            "client_type": row[2],
            "status": new_status,
            "is_paid": row[4],
            "message_id": row[5],
            "chat_id": row[6],
            "comment": row[7] if len(row) > 7 else ""
        }

        text = build_order_message(order)
        keyboard = build_inline_keyboard(order)

        try:
            await bot.edit_message_text(text, chat_id=row[6], message_id=row[5], reply_markup=keyboard)
        except Exception as e:
            print("Edit message error:", e)

        await callback.answer("Статус обновлён")

    elif data.startswith("undo_status:"):
        _, order_id = data.split(":")
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
            row = await cursor.fetchone()
            if not row:
                await callback.answer("Заказ не найден")
                return
            status_keys = [k for k, _ in STATUSES]
            try:
                current_index = status_keys.index(row[3])
            except ValueError:
                current_index = -1
            if current_index <= 0:
                await callback.answer("Это первый статус или статус не назначен")
                return
            new_status = status_keys[current_index - 1]
            await db.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))
            await db.commit()

        order = {
            "order_id": row[0],
            "description": row[1],
            "client_type": row[2],
            "status": new_status,
            "is_paid": row[4],
            "message_id": row[5],
            "chat_id": row[6],
            "comment": row[7] if len(row) > 7 else ""
        }
        text = build_order_message(order)
        keyboard = build_inline_keyboard(order)
        try:
            await bot.edit_message_text(text, chat_id=row[6], message_id=row[5], reply_markup=keyboard)
        except Exception as e:
            print("Edit message error (undo):", e)
        await callback.answer("Статус откатили")

    elif data.startswith("paid_toggle:"):
        _, order_id = data.split(":")
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
            row = await cursor.fetchone()
            if not row:
                await callback.answer("Заказ не найден")
                return
            new_paid = 0 if row[4] else 1
            await db.execute("UPDATE orders SET is_paid = ? WHERE order_id = ?", (new_paid, order_id))
            await db.commit()

        order = {
            "order_id": row[0],
            "description": row[1],
            "client_type": row[2],
            "status": row[3],
            "is_paid": new_paid,
            "message_id": row[5],
            "chat_id": row[6],
            "comment": row[7] if len(row) > 7 else ""
        }
        text = build_order_message(order)
        keyboard = build_inline_keyboard(order)
        try:
            await bot.edit_message_text(text, chat_id=row[6], message_id=row[5], reply_markup=keyboard)
        except Exception as e:
            print("Edit message error (paid):", e)
        await callback.answer("Оплата изменена")

    elif data.startswith("delete_order:"):
        _, order_id = data.split(":")
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT message_id, chat_id FROM orders WHERE order_id = ?", (order_id,))
            row = await cursor.fetchone()
            if not row:
                await callback.answer("Заказ не найден")
                return
            await db.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
            await db.commit()
        try:
            await bot.delete_message(chat_id=row[1], message_id=row[0])
        except Exception as e:
            print("Delete message error:", e)
        await callback.answer("Заказ удалён")


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


async def main():
    await init_db()
    print("База данных инициализирована, бот запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())