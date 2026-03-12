import random
from aiogram import Router, F
from aiogram.types import CallbackQuery
from db.models import User, Setting
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.inline import games_menu_kb, return_games_kb


games_router = Router()

@games_router.message(F.text == "🎲 O'yinlar")
async def show_games(message: Message):
    await message.answer("<b>Qanday vazifalarni bajarib, pul ishlamoqchisiz ⤵️</b>", reply_markup=games_menu_kb())

@games_router.callback_query(F.data == "back_to_games")
async def back_to_games_menu(call: CallbackQuery):
    await call.message.edit_text("<b>Qanday vazifalarni bajarib, pul ishlamoqchisiz ⤵️</b>", reply_markup=games_menu_kb()) # type: ignore

# --- 📦 QUTI TANLASH ---
@games_router.callback_query(F.data == "game_boxes")
async def select_box(call: CallbackQuery):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦", callback_data="open_box"),
            InlineKeyboardButton(text="📦", callback_data="open_box")
        ],
        [
            InlineKeyboardButton(text="📦", callback_data="open_box"),
            InlineKeyboardButton(text="📦", callback_data="open_box")
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_games")]
    ])
    await call.message.edit_text( # type: ignore
        "<b>4ta quti bor, shulardan birini tanlang:</b>⤵️\n<i>Har bir qutida pul yashirilgan, bitta quti tanlash narxi 5000 so'm</i>", 
        reply_markup=markup
    )

@games_router.callback_query(F.data == "open_box")
async def process_box(call: CallbackQuery):
    user = await User.get(telegram_id=call.from_user.id)
    price = 5000
    
    if user.balance < price:
        return await call.answer("⚠️ Kechirasiz, hisobingizda yetarli mablag' mavjud emas.", show_alert=True)
        
    prizes = [1000, 0, 3000, 0, 1000, 8000, 0, 5000, 0]
    win_amount = random.choice(prizes)
    
    user.balance = (user.balance - price) + win_amount
    await user.save()
    
    valyuta = await Setting.get_or_none(key="valyuta")
    pul = valyuta.value if valyuta else "so'm"
    
    await call.message.edit_text( # type: ignore
        f"📦 <b>Quti tanlandi!</b>\n\nSiz {win_amount} {pul} yutib oldingiz!", 
        reply_markup=return_games_kb()
    )

# --- 🔄 BARABAN ---
@games_router.callback_query(F.data == "game_roulette")
async def select_roulette(call: CallbackQuery):
    valyuta = await Setting.get_or_none(key="valyuta")
    pul = valyuta.value if valyuta else "so'm"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💈 Baraban aylantirish", callback_data="spin_roulette")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_games")]
    ])
    
    text = (
        f"<b>🔁 Baraban</b>\n\n"
        f"<i>Bir marta aylantirish narxi 5000 {pul}!</i>\n\n"
        f"<b>Barabandagi yutuqlar:</b>\n"
        f"0 | 1000 | 0 | 5000 | 0 | 8000"
    )
    await call.message.edit_text(text, reply_markup=markup) # type: ignore

@games_router.callback_query(F.data == "spin_roulette")
async def process_roulette(call: CallbackQuery):
    user = await User.get(telegram_id=call.from_user.id)
    price = 5000
    
    if user.balance < price:
        return await call.answer("⚠️ Kechirasiz, hisobingizda yetarli mablag' mavjud emas.", show_alert=True)
        
    prizes = [0, 1000, 0, 5000, 0, 8000]
    win_amount = random.choice(prizes)
    
    user.balance = (user.balance - price) + win_amount
    await user.save()
    
    await call.message.edit_text( # type: ignore
        f"💈 <b>Baraban aylantirildi!</b>\n\nSiz {win_amount} yutib oldingiz!", 
        reply_markup=return_games_kb()
    )
