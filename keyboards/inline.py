from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from settings import OPENBUDGET_URL
from db.models import PaymentSystem, Setting


async def vote_inline_menu() -> InlineKeyboardMarkup:
    ob_url_setting = await Setting.get_or_none(key="openbudget_url")
    current_url = ob_url_setting.value if ob_url_setting else OPENBUDGET_URL
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📮 Ovoz Berish (Sayt)", url=current_url)],
        [InlineKeyboardButton(text="✅ Ovoz Berdim", callback_data="ovoz_berdim")]
    ])

def admin_verify_menu(vote_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{vote_id}_{user_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"reject_{vote_id}_{user_id}")
        ]
    ])
    

def admin_broadcast_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Oddiy xabar", callback_data="oddiy_xabar"),
            InlineKeyboardButton(text="Forward xabar", callback_data="forward_xabar")
        ]
    ])

def primary_settings_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Hozirgi holat", callback_data="current_settings")],
        [InlineKeyboardButton(text="💵 Bitta Ovoz narxi", callback_data="set_vote_price")],
        [InlineKeyboardButton(text="🔗 Taklif narxi", callback_data="set_ref_price")],
        [InlineKeyboardButton(text="💳 Minimal pul yechish", callback_data="set_min_withdraw")],
        [InlineKeyboardButton(text="👨‍💻 Admin username", callback_data="set_admin_user")],
        [InlineKeyboardButton(text="🔗 Loyiha manzili (URL)", callback_data="set_ob_url", style="danger")],
    ])
    
def bonus_settings_kb(is_active: bool):
    status_text = "💡 Status (O'chirish)" if is_active else "💡 Status (Yoqish)"
    status_action = "toggle_bonus_off" if is_active else "toggle_bonus_on"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Bonus miqdorini sozlash", callback_data="set_bonus_amount")],
        [InlineKeyboardButton(text=status_text, callback_data=status_action)],
    ])

def channels_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Majburiy obuna kanallari", callback_data="manage_mandatory")],
        [InlineKeyboardButton(text="🔐 To'lovlar kanali", callback_data="manage_payment_channel")],
        [InlineKeyboardButton(text="📸 Isbot kanali", callback_data="manage_isbot_channel")],
    ])

def channels_del_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🗑 Barchasini o'chirish", callback_data="clear_mandatory")]]
    )

async def payment_systems_kb() -> InlineKeyboardMarkup:
    systems = await PaymentSystem.all()
    keyboard = []
    
    # Bazadagi bor tizimlarni o'chirish tugmalari
    for sys in systems:
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ {sys.name} - ni o'chirish", 
                callback_data=f"del_paysys_{sys.id}"
            )
        ])
        
    # Yangi tizim qo'shish tugmasi
    keyboard.append([
        InlineKeyboardButton(text="➕ Yechish tizimi qo'shish", callback_data="add_payment_system")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def games_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Baraban", callback_data="game_roulette"),
            InlineKeyboardButton(text="📦 Quti tanlash", callback_data="game_boxes")
        ],
        [InlineKeyboardButton(text="🔐 Sandiq ochish", callback_data="game_chests")]
    ])

def return_games_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_games")]
    ])

def rating_keyb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Reyting", callback_data="ratings")],
        [InlineKeyboardButton(text="🏆 Referallar reytingi", callback_data="ratings_ref")]
    ])

def sub_keyboard(unsubbed_channels: list) -> InlineKeyboardMarkup:
    kb = []
    for i, ch in enumerate(unsubbed_channels, 1):
        url = ch.username.replace("@", "")
        kb.append([InlineKeyboardButton(text=f"❌ {i}-kanal", url=f"https://t.me/{url}")])
    kb.append([InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_subs")])
    return InlineKeyboardMarkup(inline_keyboard=kb)
