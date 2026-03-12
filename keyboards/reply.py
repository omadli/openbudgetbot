from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🎯 Ovoz Berish")],
        [KeyboardButton(text="💵 Hisobim"), KeyboardButton(text="🖇️ Taklif qilish")],
        [KeyboardButton(text="📃 To'lovlar"), KeyboardButton(text="📑 Yo'riqnoma")],
        [KeyboardButton(text="🎲 O'yinlar"), KeyboardButton(text="☎️ Murojaat")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="🗄 Boshqaruv")])
        
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="◀️ Orqaga")]], 
    resize_keyboard=True
)

def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="*⃣ Birlamchi sozlamalar")],
            [KeyboardButton(text="🎁 Kunlik bonus sozlamalari")],
            [KeyboardButton(text="👤 Adminlar"), KeyboardButton(text="💵 Yechish tizimi")],
            [KeyboardButton(text="📢 Kanallar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🔎 Foydalanuvchini boshqarish")],
            [KeyboardButton(text="📨 Xabarnoma"), KeyboardButton(text="◀️ Orqaga")],
        ], 
        resize_keyboard=True)
