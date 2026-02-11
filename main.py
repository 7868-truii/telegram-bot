import os
import telebot
from telebot import types
import pandas as pd
import uuid

# === TELEGRAM TOKEN FROM RAILWAY ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# === LOAD EXCEL ===
df = pd.read_excel(
    'nasosy.xlsx',
    header=None,
    names=['оборудование', 'level1', 'level2', 'level3', 'level4', 'level5']
)
df.fillna('', inplace=True)

user_state = {}

# ---------- KEYBOARDS ----------
def main_menu_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("📂 Насосы", callback_data="nasos"))
    keyboard.add(types.InlineKeyboardButton("🧪 Расчёт дезсредств", callback_data="dez"))
    keyboard.add(types.InlineKeyboardButton("📚 Полезная информация", callback_data="info"))
    keyboard.add(types.InlineKeyboardButton("📏 Нормы", callback_data="norms"))
    return keyboard


def back_home_keyboard(back_callback):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data=back_callback))
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="back"))
    return keyboard


def lvl_keyboard(items_map, prefix, back_callback):
    keyboard = types.InlineKeyboardMarkup()
    for item_id, item_name in items_map.items():
        keyboard.add(types.InlineKeyboardButton(item_name, callback_data=f"{prefix}:{item_id}"))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data=back_callback))
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="back"))
    return keyboard


# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_menu_keyboard())


# ---------- NASOS ----------
@bot.callback_query_handler(func=lambda call: call.data == "nasos")
def equipment(call):
    eq_map = {
        uuid.uuid4().hex[:8]: eq.strip()
        for eq in df['оборудование'].dropna().unique()
        if eq.strip().lower() != 'оборудование'
    }

    user_state[call.from_user.id] = {"eq_map": eq_map}

    keyboard = types.InlineKeyboardMarkup()
    for k, v in eq_map.items():
        keyboard.add(types.InlineKeyboardButton(v, callback_data=f"eq:{k}"))
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="back"))

    bot.edit_message_text(
        "Выбери оборудование:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )


# ---------- LEVEL 1 ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith("eq:"))
def level1(call):
    eq_id = call.data.split(":")[1]
    state = user_state.get(call.from_user.id, {})
    eq = state.get("eq_map", {}).get(eq_id)

    if not eq:
        start(call.message)
        return

    lvl1_map = {
        uuid.uuid4().hex[:8]: l
        for l in df[df['оборудование'] == eq]['level1'].dropna().unique()
    }

    state.update({
        "eq": eq,
        "eq_id": eq_id,
        "lvl1_map": lvl1_map
    })

    bot.edit_message_text(
        f"{eq}\nВыбери:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=lvl_keyboard(lvl1_map, "l1", "nasos")
    )


# ---------- LEVEL 2 ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith("l1:"))
def level2(call):
    lvl1_id = call.data.split(":")[1]
    state = user_state[call.from_user.id]
    lvl1 = state["lvl1_map"].get(lvl1_id)

    if not lvl1:
        start(call.message)
        return

    eq = state["eq"]

    lvl2_map = {
        uuid.uuid4().hex[:8]: l
        for l in df[(df['оборудование'] == eq) & (df['level1'] == lvl1)]['level2'].dropna().unique()
    }

    state.update({
        "lvl1": lvl1,
        "lvl2_map": lvl2_map,
        "current_lvl1_id": lvl1_id
    })

    bot.edit_message_text(
        f"{eq} → {lvl1}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=lvl_keyboard(lvl2_map, "l2", f"eq:{state['eq_id']}")
    )


# ---------- RESULT ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith("l2:"))
def result_level(call):
    lvl2_id = call.data.split(":")[1]
    state = user_state[call.from_user.id]
    lvl2 = state["lvl2_map"].get(lvl2_id)

    if not lvl2:
        start(call.message)
        return

    rows = df[
        (df['оборудование'] == state['eq']) &
        (df['level1'] == state['lvl1']) &
        (df['level2'] == lvl2)
    ]

    text = f"🔧 **{state['eq']}**\n- {state['lvl1']}\n- {lvl2}\n\n"
    for _, r in rows.iterrows():
        text += f"🔹 Номер насоса: {r['level3']}\n📝 {r['level4']}\n\n"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"l1:{state['current_lvl1_id']}"))
    keyboard.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="back"))

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ---------- BACK ----------
@bot.callback_query_handler(func=lambda call: call.data == "back")
def back(call):
    bot.send_message(call.message.chat.id, "Главное меню:", reply_markup=main_menu_keyboard())


# ---------- POLLING ----------
bot.polling(none_stop=True)