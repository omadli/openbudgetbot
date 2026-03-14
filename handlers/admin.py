import io
import json
import time
import openpyxl
from datetime import datetime
from aiogram import Router, F, Bot
from tortoise.expressions import Q
from tortoise.functions import Sum, Count
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from states.forms import AdminState
from settings import OPENBUDGET_URL, VOTE_PRICE, ADMIN_IDS
from keyboards.reply import admin_menu_keyboard, cancel_kb, get_main_menu
from db.models import User, Vote, Withdrawal, Setting, Channel, PaymentSystem, OBVote
from utils.openbudget import fetch_captcha, fetch_token, parse_and_save_votes
from keyboards.inline import admin_broadcast_menu, primary_settings_kb, bonus_settings_kb, channels_kb, channels_del_kb, payment_systems_kb, rating_keyb

admin_router = Router()
admin_router.message.filter(F.from_user.id.in_(ADMIN_IDS))
admin_router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


@admin_router.callback_query(F.data.startswith("approve_"))
async def approve_vote(call: CallbackQuery, bot: Bot): 
    _, vote_id, user_id = call.data.split("_") # type: ignore
    vote = await Vote.get_or_none(id=int(vote_id))
    
    if not vote or vote.status != "pending":
        return await call.answer("Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)

    vote.status = "approved"
    await vote.save(update_fields=["status"]) # 👈 Optimallashtirildi
    
    vote_price_setting = await Setting.get_or_none(key="vote_price")
    vote_price = int(vote_price_setting.value) if vote_price_setting else VOTE_PRICE
    user = await User.get(telegram_id=int(user_id))
    user.balance += vote_price
    await user.save(update_fields=["balance"]) # 👈 XATOLIK TARTIBGA SOLINDI

    await call.message.edit_caption(caption=f"{call.message.caption}\n\n✅ <b>TASDIQLANDI</b>") # type: ignore
    await bot.send_message(
        chat_id=int(user_id),
        text=f"<b>✅ So'rovingiz qabul qilindi!</b>\n\nHisobingizga {vote_price} so'm qo'shildi."
    )

@admin_router.callback_query(F.data.startswith("reject_"))
async def reject_vote(call: CallbackQuery, bot: Bot):
    _, vote_id, user_id = call.data.split("_") # type: ignore
    vote = await Vote.get_or_none(id=int(vote_id))

    if not vote or vote.status != "pending":
        return await call.answer("Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)

    vote.status = "rejected"
    await vote.save()

    await call.message.edit_caption(caption=f"{call.message.caption}\n\n❌ <b>BEKOR QILINDI</b>", ) # type: ignore
    await bot.send_message(
        chat_id=user_id,
        text="<b>❌ So'rovingiz bekor qilindi! Screenshot yoki raqam xato.</b>",
    )


@admin_router.message(F.text == "🗄 Boshqaruv")
async def admin_main_menu(message: Message, state: FSMContext):
    await message.answer(
        text="<b>🗄 Boshqaruv paneliga xush kelibsiz!</b>",
        reply_markup=admin_menu_keyboard()
    )

@admin_router.message(F.text == "📨 Xabarnoma")
async def broadcast_menu(message: Message, state: FSMContext):
    await message.answer(
        "<b>📨 Yuboriladigan xabar turini tanlang:</b>",
        reply_markup=admin_broadcast_menu()
    )

@admin_router.callback_query(F.data == "oddiy_xabar")
async def ask_broadcast_text(call: CallbackQuery, state: FSMContext): # type: ignore
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        text="<b>Foydalanuvchilarga yuboriladigan xabar matnini kiriting:</b>",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminState.broadcast_text)

@admin_router.callback_query(F.data == "forward_xabar")
async def ask_broadcast_text(call: CallbackQuery, state: FSMContext):
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        text="<b>Foydalanuvchilarga yuboriladigan  xabarni forward shaklida yuboring::</b>",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminState.broadcast_forward)


@admin_router.message(F.text == "◀️ Orqaga")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="<b>🖥 Asosiy menyudasiz</b>",
        reply_markup=get_main_menu(is_admin=True)
    )

@admin_router.message(AdminState.broadcast_text, F.text == "◀️ Orqaga")
@admin_router.message(AdminState.broadcast_forward, F.text == "◀️ Orqaga")
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="<b>🗄 Boshqaruv paneliga xush kelibsiz!</b>",
        reply_markup=admin_menu_keyboard()
    )

@admin_router.message(AdminState.broadcast_text)
async def send_broadcast(message: Message, state: FSMContext, bot: Bot):
    users = await User.all()
    success_count = 0
    await message.answer("Xabar yuborish boshlandi...")
    
    for user in users:
        try:
            await bot.send_message(chat_id=user.telegram_id, text=message.text, ) # type: ignore
            success_count += 1
        except Exception:
            pass # Bloklagan foydalanuvchilarni o'tkazib yuborish
            
    await message.answer(
        text=f"✅ Xabar {success_count} ta foydalanuvchiga yuborildi.",
        reply_markup=admin_menu_keyboard(),
    )
    await state.clear()

@admin_router.message(AdminState.broadcast_forward)
async def send_broadcast_forward(message: Message, state: FSMContext, bot: Bot):
    users = await User.all()
    success_count = 0
    await message.answer("Xabar yuborish boshlandi...")
    
    for user in users:
        try:
            await bot.forward_message(chat_id=user.telegram_id, from_chat_id=message.chat.id, message_id=message.message_id)
            success_count += 1
        except Exception:
            pass # Bloklagan foydalanuvchilarni o'tkazib yuborish
            
    await message.answer(
        text=f"✅ Xabar {success_count} ta foydalanuvchiga yuborildi.", 
        reply_markup=admin_menu_keyboard()
    )
    await state.clear()

# --- FOYDALANUVCHINI BOSHQARISH ---
@admin_router.message(F.text == "🔎 Foydalanuvchini boshqarish")
async def ask_user_id_for_manage(message: Message, state: FSMContext):
    await message.answer(
        "<b>Kerakli foydalanuvchining ID raqamini yuboring:</b>",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminState.manage_user_id)

@admin_router.message(AdminState.manage_user_id)
async def manage_user_info(message: Message, state: FSMContext):
    if not message.text.isdigit(): # type: ignore
        return await message.answer("<b>Kerakli ID raqamni kiriting:</b>")
        
    target_id = int(message.text) # type: ignore
    user = await User.get_or_none(telegram_id=target_id)
    
    if not user:
        return await message.answer("<b>Ushbu foydalanuvchi botdan foydalanmaydi!</b>\n\n<i>Qayta yuboring:</i>")
        
    # Ban statusiga qarab tugma matnini aniqlash
    ban_text = "🔕 Bandan olish" if user.is_banned else "🔔 Banlash"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ban_text, callback_data=f"usr_ban_{user.telegram_id}")],
        [
            InlineKeyboardButton(text="➕ Pul qo'shish", callback_data=f"usr_add_{user.telegram_id}"),
            InlineKeyboardButton(text="➖ Pul ayirish", callback_data=f"usr_sub_{user.telegram_id}")
        ]
    ])
    
    # Valyuta nomini bazadan olish (agar yo'q bo'lsa default "so'm")
    valyuta_record = await Setting.get_or_none(key="valyuta")
    pul = valyuta_record.value if valyuta_record else "so'm"
    
    text = (
        f"<b>✅ Foydalanuvchi topildi:</b> <a href='tg://user?id={user.telegram_id}'>{user.telegram_id}</a>\n\n"
        f"<b>Asosiy balans:</b> {user.balance} {pul}\n"
        f"<b>Takliflari:</b> {user.referral_count} ta\n"
    )
    
    await message.answer(text, reply_markup=markup)
    # Inline tugmalar bilan ishlash uchun State ni tozalaymiz
    await state.clear()


# --- 1. BANLASH VA BANDAN OLISH ---
@admin_router.callback_query(F.data.startswith("usr_ban_"))
async def toggle_user_ban(call: CallbackQuery, bot: Bot):
    target_id = int(call.data.split("_")[2]) # type: ignore
    
    if target_id in ADMIN_IDS:
        return await call.answer("Asosiy adminni bloklash mumkin emas!", show_alert=True)
        
    user = await User.get_or_none(telegram_id=target_id)
    if not user:
        return await call.answer("Foydalanuvchi topilmadi!", show_alert=True)
        
    # Holatni o'zgartirish
    user.is_banned = not user.is_banned
    await user.save()
    
    await call.message.delete() # type: ignore
    
    if user.is_banned:
        await call.message.answer("<b>Foydalanuvchi banlandi!</b>", reply_markup=admin_menu_keyboard()) # type: ignore
        try:
            await bot.send_message(target_id, "<b>Admin tomonidan ban oldingiz!</b>")
        except: pass
    else: 
        await call.message.answer("<b>Foydalanuvchi bandan olindi!</b>", reply_markup=admin_menu_keyboard()) # type: ignore
        try:
            await bot.send_message(target_id, "<b>Admin tomonidan bandan olindingiz!</b>")
        except: pass


# --- 2. PUL QO'SHISH ---
@admin_router.callback_query(F.data.startswith("usr_add_"))
async def ask_add_balance(call: CallbackQuery, state: FSMContext):
    target_id = int(call.data.split("_")[2]) # type: ignore
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        f"<a href='tg://user?id={target_id}'>{target_id}</a> <b>ning hisobiga qancha pul qo'shmoqchisiz?</b>",
        reply_markup=cancel_kb
    )
    await state.update_data(target_user_id=target_id)
    await state.set_state(AdminState.add_balance)

@admin_router.message(AdminState.add_balance)
async def process_add_balance(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit(): # type: ignore
        return await message.answer("Iltimos, faqat raqam kiriting:")
        
    amount = int(message.text) # type: ignore
    data = await state.get_data()
    target_id = data.get("target_user_id")
    
    user = await User.get_or_none(telegram_id=target_id)
    if user:
        user.balance += amount
        await user.save()
        
        valyuta_record = await Setting.get_or_none(key="valyuta")
        pul = valyuta_record.value if valyuta_record else "so'm"
        
        await message.answer(f"<b>Foydalanuvchi hisobiga {amount} {pul} qo'shildi</b>", reply_markup=admin_menu_keyboard())
        
        # Foydalanuvchiga xabar
        try:
            await bot.send_message(target_id, f"<b>Adminlar tomonidan hisobingiz {amount} {pul} to'ldirildi</b>") # type: ignore
        except: pass
        
        # To'lovlar kanaliga bildirishnoma yuborish (PHP dagi kabi)
        tolov_kanali = await Setting.get_or_none(key="tolovlar_kanali")
        if tolov_kanali:
            try:
                await bot.send_message(
                    chat_id=tolov_kanali.value,
                    text=f"<b>🔹 Foydalanuvchi: <u>{target_id}</u> hisobini {amount} {pul}'ga to'ldirdi!</b>",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔹 Foydalanuvchi", url=f"tg://user?id={target_id}")]
                    ])
                )
            except: pass
            
    await state.clear()


# --- 3. PUL AYIRISH ---
@admin_router.callback_query(F.data.startswith("usr_sub_"))
async def ask_sub_balance(call: CallbackQuery, state: FSMContext):
    target_id = int(call.data.split("_")[2]) # type: ignore
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        f"<a href='tg://user?id={target_id}'>{target_id}</a> <b>ning hisobidan qancha pul ayirmoqchisiz?</b>",
        reply_markup=cancel_kb
    )
    await state.update_data(target_user_id=target_id)
    await state.set_state(AdminState.deduct_balance)

@admin_router.message(AdminState.deduct_balance)
async def process_sub_balance(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit(): # type: ignore
        return await message.answer("Iltimos, faqat raqam kiriting:")
        
    amount = int(message.text) # type: ignore
    data = await state.get_data()
    target_id = data.get("target_user_id")
    
    user = await User.get_or_none(telegram_id=target_id)
    if user:
        user.balance -= amount
        if user.balance < 0:
            user.balance = 0 # Balans minusga kirib ketmasligi uchun
        await user.save()
        
        valyuta_record = await Setting.get_or_none(key="valyuta")
        pul = valyuta_record.value if valyuta_record else "so'm"
        
        await message.answer(f"<b>Foydalanuvchi hisobidan {amount} {pul} olib tashlandi</b>", reply_markup=admin_menu_keyboard())
        
        try:
            await bot.send_message(target_id, f"<b>Adminlar tomonidan hisobingizdan {amount} {pul} olib tashlandi</b>") # type: ignore
        except: pass
            
    await state.clear()
    

# --- PUL YECHISHNI TASDIQLASH (Kanaldan yoki admin guruhdan) ---
@admin_router.callback_query(F.data.startswith("withdraw_paid_"))
async def withdraw_paid(call: CallbackQuery, bot: Bot):
    withdrawal_id = int(call.data.split("_")[2]) # type: ignore
    withdrawal = await Withdrawal.get_or_none(id=withdrawal_id).prefetch_related('user')
    
    if withdrawal and withdrawal.status == "pending":
        withdrawal.status = "paid"
        await withdrawal.save()
        
        await bot.send_message(
            chat_id=withdrawal.user.telegram_id, 
            text=f"<b>✅ {withdrawal.amount} so'm pullaringiz to'lab berildi!</b>", 
            
        )
        await call.message.edit_text(f"{call.message.text}\n\n✅ TO'LANDI") # type: ignore


@admin_router.callback_query(F.data.startswith("withdraw_reject_"))
async def withdraw_reject(call: CallbackQuery, bot: Bot):
    withdrawal_id = int(call.data.split("_")[2]) # type: ignore
    withdrawal = await Withdrawal.get_or_none(id=withdrawal_id).prefetch_related('user')
    
    if withdrawal and withdrawal.status == "pending":
        withdrawal.status = "rejected"
        await withdrawal.save()
        
        # Pulni qaytarib berish
        withdrawal.user.balance += withdrawal.amount
        await withdrawal.user.save()
        
        await bot.send_message(
            chat_id=withdrawal.user.telegram_id, 
            text="<b>⚠️ Arizangiz bekor qilindi va pullar hisobingizga qaytarildi!</b>", 
            
        )
        await call.message.edit_text(f"{call.message.text}\n\n❌ BEKOR QILINDI") # type: ignore

@admin_router.message(F.text == "📊 Statistika")
async def show_statistics(message: Message):
    start_time = time.time()
    m = await message.answer("Ping")
    end_time = time.time()
    ping = round((end_time - start_time) * 1000)
    
    user_count = await User.all().count()
    approved_votes = await Vote.filter(status="approved").count()
    rejected_votes = await Vote.filter(status="rejected").count()
    pending_votes = await Vote.filter(status="pending").count()
    
    # Jami to'langan summani hisoblash
    paid_sum_result = await Withdrawal.filter(status="paid").annotate(total=Sum("amount")).first()
    total_paid = paid_sum_result.total if paid_sum_result and hasattr(paid_sum_result, 'total') else 0 # type: ignore
    
    text = (
        "<b>📊 Statistika:</b>\n\n"
        f"🚀 Ping: {ping}ms\n"
        f"👥 Foydalanuvchilar: {user_count} ta\n"
        f"🔖 Tasdiqlangan ovozlar: {approved_votes} ta\n"
        f"❌ Bekor qilingan ovozlar: {rejected_votes} ta\n"
        f"⏳ Kutilayotgan ovozlar: {pending_votes} ta\n"
        f"💵 Jami to'landi: {total_paid or 0} so'm\n"
    )
    await m.edit_text(text, reply_markup=rating_keyb())

@admin_router.callback_query(F.data == "ratings_ref")
async def show_referral_rating(call: CallbackQuery):
    wait_msg = await call.message.answer("⏳ <b>Reyting hisoblanmoqda...</b>") # type: ignore
    
    top_referrers = await User.filter(referrer_id__not_isnull=True)\
        .annotate(ref_count=Count("id"))\
        .group_by("referrer_id")\
        .order_by("-ref_count")\
        .limit(10)\
        .values("referrer_id", "ref_count")

    text = "🏆 <b>TOP 10 REFERALLAR REYTINGI:</b>\n\n"
    
    if not top_referrers:
        text += "<i>🤷‍♂️ Hali hech kim referal orqali odam chaqirmagan.</i>"
    else:
        for i, ref in enumerate(top_referrers, start=1):
            referrer = await User.get_or_none(telegram_id=ref["referrer_id"])
            
            name = referrer.full_name if referrer else f"ID: {ref['referrer_id']}"
            
            name = name.replace("<", "").replace(">", "")
            
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"<b>{i}.</b>"
                
            text += f"{medal} <b>{name}</b> — {ref['ref_count']} ta taklif\n"

    await wait_msg.edit_text(text)

@admin_router.callback_query(F.data == "ratings")
async def show_ratings(call: CallbackQuery):
    # Faqat statusi "approved" bo'lgan ovozlar sonini hisoblab, kamayish tartibida taxlaymiz
    top_users = await User.annotate(
        vote_count=Count("votes", _filter=Q(votes__status="approved"))
    ).filter(vote_count__gt=0).order_by("-vote_count").limit(10)
    
    if not top_users:
        return await call.answer("Hali tasdiqlangan ovozlar yo'q!", show_alert=True)
        
    text = "<b>🏆 Ovoz berganlar reytingi (Top 10):</b>\n\n"
    for i, u in enumerate(top_users, 1):
        subtext = f"ID: <code>{u.telegram_id}</code>" if not u.username else f"@{u.username}"
        text += f"{i}. <a href='tg://user?id={u.telegram_id}'>{u.full_name}</a> [{subtext}] - {u.vote_count} ta ovoz\n" # type: ignore
        
    await call.message.answer(text) # type: ignore
    await call.answer()
    
@admin_router.message(F.text == "*⃣ Birlamchi sozlamalar")
async def primary_settings_menu(message: Message):
    await message.answer(
        "<b>*⃣ Birlamchi sozlamalar bo'limi:</b>\n\nNimani o'zgartiramiz?",
        reply_markup=primary_settings_kb(),
    )

# Narxni o'zgartirish (Misol uchun: Ovoz narxi)
@admin_router.callback_query(F.data == "set_vote_price")
async def ask_vote_price(call: CallbackQuery, state: FSMContext):
    await call.message.delete()  # type: ignore
    await call.message.answer("📝 Yangi ovoz narxini raqamlarda kiriting:", reply_markup=cancel_kb) # type: ignore
    await state.set_state(AdminState.set_vote_price)

@admin_router.message(AdminState.set_vote_price)
async def update_vote_price(message: Message, state: FSMContext):
    if not message.text.isdigit(): # type: ignore
        return await message.answer("Iltimos, faqat raqam kiriting!")
    
    await Setting.update_or_create(key="vote_price", defaults={"value": message.text})
    await message.answer("<b>✅ Ovoz narxi muvaffaqiyatli o'zgartirildi!</b>", reply_markup=admin_menu_keyboard())
    await state.clear()

# URL so'rash handlerlari:
@admin_router.callback_query(F.data == "set_ob_url")
async def ask_ob_url(call: CallbackQuery, state: FSMContext):
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        "📝 <b>Yangi OpenBudget loyiha manzilini (URL) yuboring:</b>\n"
        "Namuna: <i>https://openbudget.uz/boards/initiatives/initiative/...</i>",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminState.set_ob_url)

@admin_router.message(AdminState.set_ob_url)
async def update_ob_url(message: Message, state: FSMContext):
    if not message.text.startswith("http"): # type: ignore
        return await message.answer("⚠️ Iltimos, to'g'ri URL manzil kiriting (http yoki https bilan boshlansin):")
        
    # Bazaga url ni saqlaymiz
    await Setting.update_or_create(key="openbudget_url", defaults={"value": message.text.strip()}) # type: ignore
    
    await message.answer(
        "<b>✅ Loyiha manzili muvaffaqiyatli o'zgartirildi!</b>", 
        reply_markup=admin_menu_keyboard()
    )
    await state.clear()
    
# ==========================================
# 🔗 TAKLIF NARXINI O'ZGARTIRISH
# ==========================================
@admin_router.callback_query(F.data == "set_ref_price")
async def ask_ref_price(call: CallbackQuery, state: FSMContext):
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        "📝 <b>Yangi taklif (referal) narxini raqamlarda kiriting:</b>",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminState.set_ref_price)

@admin_router.message(AdminState.set_ref_price)
async def update_ref_price(message: Message, state: FSMContext):
    if not message.text.isdigit(): # type: ignore
        return await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        
    yangi_narx = message.text.strip() # type: ignore
     
    # Bazada saqlash yoki yangilash
    await Setting.update_or_create(key="ref_price", defaults={"value": yangi_narx})
    
    # Valyutani chiroyli ko'rsatish uchun bazadan olamiz (ixtiyoriy)
    valyuta_record = await Setting.get_or_none(key="valyuta")
    pul = valyuta_record.value if valyuta_record else "so'm"
    
    await message.answer(
        f"<b>✅ Bitta taklif uchun beriladigan summa {yangi_narx} {pul} qilib o'zgartirildi!</b>", 
        reply_markup=admin_menu_keyboard()
    )
    await state.clear()


# ==========================================
# 💳 MINIMAL PUL YECHISH MIQDORINI O'ZGARTIRISH
# ==========================================
@admin_router.callback_query(F.data == "set_min_withdraw")
async def ask_min_withdraw(call: CallbackQuery, state: FSMContext):
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        "📝 <b>Minimal pul yechish miqdorini raqamlarda kiriting:</b>",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminState.set_min_withdraw)

@admin_router.message(AdminState.set_min_withdraw)
async def update_min_withdraw(message: Message, state: FSMContext):
    if not message.text.isdigit(): # type: ignore
        return await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        
    yangi_miqdor = message.text.strip() # type: ignore
    
    # Bazada saqlash yoki yangilash
    await Setting.update_or_create(key="min_withdraw", defaults={"value": yangi_miqdor})
    
    valyuta_record = await Setting.get_or_none(key="valyuta")
    pul = valyuta_record.value if valyuta_record else "so'm"
    
    await message.answer(
        f"<b>✅ Minimal pul yechish chegarasi {yangi_miqdor} {pul} qilib o'zgartirildi!</b>", 
        reply_markup=admin_menu_keyboard()
    )
    await state.clear()

# ==========================================
# 📊 HOZIRGI HOLAT
# ==========================================
@admin_router.callback_query(F.data == "current_settings")
async def show_current_settings(call: CallbackQuery):
    # Barcha sozlamalarni bazadan bittada o'qib olib, dictionary ga o'giramiz
    settings_db = await Setting.all()
    settings = {s.key: s.value for s in settings_db}
    
    vote_price = settings.get("vote_price", "5000") # Agar yo'q bo'lsa default qiymat
    ref_price = settings.get("ref_price", "1000")
    min_withdraw = settings.get("min_withdraw", "3000")
    ob_url = settings.get("openbudget_url", "Belgilanmagan")
    admin_user = settings.get("admin_user", "@admin")
    valyuta = settings.get("valyuta", "so'm")
    
    text = (
        "<b>📊 Hozirgi birlamchi sozlamalar holati:</b>\n\n"
        f"<b>💵 Ovoz narxi:</b> {vote_price} {valyuta}\n"
        f"<b>🔗 Taklif narxi:</b> {ref_price} {valyuta}\n"
        f"<b>💳 Min. yechish:</b> {min_withdraw} {valyuta}\n"
        f"<b>👨‍💻 Admin useri:</b> {admin_user}\n"
        f"<b>🔗 Loyiha manzili:</b> {ob_url}"
    )
    
    # Xabarni o'zgartiramiz, oldingi klaviatura o'zida qolaveradi
    await call.message.edit_text( # type: ignore
        text, 
        reply_markup=primary_settings_kb(), 
        disable_web_page_preview=True
    )

# ==========================================
# 👨‍💻 ADMIN USERNAME'NI O'ZGARTIRISH
# ==========================================
@admin_router.callback_query(F.data == "set_admin_user")
async def ask_admin_user(call: CallbackQuery, state: FSMContext):
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        "📝 <b>Yangi admin username'ini yuboring:</b>\n<i>Namuna: @admin_aloqa</i>",
        reply_markup=cancel_kb
    )
    await state.set_state(AdminState.set_admin_user)

@admin_router.message(AdminState.set_admin_user)
async def update_admin_user(message: Message, state: FSMContext):
    if not message.text.startswith("@"): # type: ignore
        return await message.answer("⚠️ Iltimos, username'ni <b>@</b> belgisi bilan boshlang!")
        
    yangi_user = message.text.strip() # type: ignore
    
    # Bazada saqlash yoki yangilash
    await Setting.update_or_create(key="admin_user", defaults={"value": yangi_user})
    
    await message.answer(
        f"<b>✅ Aloqa uchun admin username {yangi_user} qilib o'zgartirildi!</b>", 
        reply_markup=admin_menu_keyboard()
    )
    await state.clear()

@admin_router.message(F.text == "🎁 Kunlik bonus sozlamalari")
async def bonus_settings_menu(message: Message):
    status_record = await Setting.get_or_none(key="bonus_status")
    amount_record = await Setting.get_or_none(key="bonus_amount")
    
    is_active = status_record.value == "on" if status_record else False
    amount = amount_record.value if amount_record else "100"
    
    text = (
        "<b>🎁 Kunlik bonus sozlamalari</b>\n\n"
        f"<b>Bonus miqdori:</b> {amount} so'm\n"
        f"<b>Status:</b> {'Yoqilgan' if is_active else 'O\'chirilgan'}"
    )
    await message.answer(text, reply_markup=bonus_settings_kb(is_active))

@admin_router.callback_query(F.data.startswith("toggle_bonus_"))
async def toggle_bonus_status(call: CallbackQuery):
    new_status = "on" if call.data == "toggle_bonus_on" else "off"
    await Setting.update_or_create(key="bonus_status", defaults={"value": new_status})
    
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        f"✅ Bonus holati o'zgartirildi: <b>{'Yoqildi' if new_status == 'on' else 'O\'chirildi'}</b>",
    ) 
    

@admin_router.message(F.text == "📢 Kanallar")
async def channels_menu(message: Message):
    await message.answer("<b>Quyidagilardan birini tanlang:</b>", reply_markup=channels_kb())

@admin_router.callback_query(F.data == "manage_mandatory")
async def manage_mandatory_channels(call: CallbackQuery, state: FSMContext):
    channels = await Channel.filter(is_mandatory=True).all()
    channel_list = "\n".join([f"{i+1}. {ch.username}" for i, ch in enumerate(channels)]) or "Kanallar yo'q."
    
    text = f"<b>Ulangan kanallar ro'yxati:</b>\n\n{channel_list}\n\n<i>Yangi kanal qoshish uchun kanal manzilini yuboring (@kanal):</i>"
    await call.message.edit_text(text, reply_markup=channels_del_kb()) # type: ignore
    await state.set_state(AdminState.add_channel)

@admin_router.message(AdminState.add_channel)
async def add_mandatory_channel(message: Message, state: FSMContext):
    if not message.text.startswith("@"): # type: ignore
        return await message.answer("⚠️ Kanal manzili xato kiritildi! Namuna: @kanal")
        
    await Channel.create(username=message.text, is_mandatory=True)
    await message.answer(f"✅ {message.text} kanali qo'shildi!", reply_markup=admin_menu_keyboard())
    await state.clear()


@admin_router.callback_query(F.data == "clear_mandatory")
async def clear_mandatory_channels(call: CallbackQuery):
    await Channel.filter(is_mandatory=True).delete()
    await call.answer("🗑 Barcha majburiy kanallar o'chirildi!", show_alert=True)
    await call.message.delete() # type: ignore


# ==========================================
# 🔐 TO'LOVLAR KANALINI BOSHQARISH
# ==========================================
@admin_router.callback_query(F.data == "manage_payment_channel")
async def manage_payment_channel_menu(call: CallbackQuery, state: FSMContext):
    channel_record = await Setting.get_or_none(key="tolovlar_kanali")
    current_channel = channel_record.value if channel_record else "Belgilanmagan (Yo'q)"

    text = (
        f"<b>To'lovlar kanali holati:</b>\n\n"
        f"<b>Hozirgi kanal:</b> {current_channel}\n\n"
        f"<i>Yangi to'lovlar kanalini ulash uchun kanal ID si (masalan: -100123...) yoki username (masalan: @kanal) sini yuboring:</i>"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Kanalni olib tashlash", callback_data="clear_payment_channel")]
    ])

    await call.message.edit_text(text, reply_markup=markup) # type: ignore
    await state.set_state(AdminState.add_payment_channel)

@admin_router.message(AdminState.add_payment_channel)
async def save_payment_channel(message: Message, state: FSMContext):
    new_channel = message.text.strip() # type: ignore
    
    # Bazaga saqlash yoki yangilash
    await Setting.update_or_create(key="tolovlar_kanali", defaults={"value": new_channel})
    
    await message.answer(
        f"<b>✅ To'lovlar kanali {new_channel} qilib o'rnatildi!</b>\n\n<i>Endi pul yechish arizalari shu kanalga boradi.</i>", 
        reply_markup=admin_menu_keyboard()
    )
    await state.clear()

@admin_router.callback_query(F.data == "clear_payment_channel")
async def clear_payment_channel_action(call: CallbackQuery, state: FSMContext):
    await Setting.filter(key="tolovlar_kanali").delete()
    
    await call.answer("🗑 To'lovlar kanali bazadan o'chirildi!", show_alert=True)
    await call.message.delete() # type: ignore
    await state.clear()
    
# ==========================================
# 📸 ISBOT KANALINI BOSHQARISH
# ==========================================
@admin_router.callback_query(F.data == "manage_isbot_channel")
async def manage_isbot_channel_menu(call: CallbackQuery, state: FSMContext):
    channel_record = await Setting.get_or_none(key="isbot_kanali")
    current_channel = channel_record.value if channel_record else "Belgilanmagan (Yo'q)"

    text = (
        f"<b>📸 Isbot kanali holati:</b>\n\n"
        f"<b>Hozirgi kanal:</b> {current_channel}\n\n"
        f"<i>Yangi isbot kanalini ulash uchun kanal username (masalan: @kanal) sini yuboring:</i>"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Kanalni olib tashlash", callback_data="clear_isbot_channel")]
    ])

    await call.message.edit_text(text, reply_markup=markup) # type: ignore
    await state.set_state(AdminState.add_isbot_channel)

@admin_router.message(AdminState.add_isbot_channel)
async def save_isbot_channel(message: Message, state: FSMContext):
    new_channel = message.text.strip() # type: ignore
    
    # Bazaga saqlash yoki yangilash
    await Setting.update_or_create(key="isbot_kanali", defaults={"value": new_channel})
    
    await message.answer(
        f"<b>✅ Isbot kanali {new_channel} qilib o'rnatildi!</b>\n\n<i>Endi tasdiqlangan skrinshotlar shu kanalga yuborilishi mumkin.</i>", 
        reply_markup=admin_menu_keyboard()
    )
    await state.clear()

@admin_router.callback_query(F.data == "clear_isbot_channel")
async def clear_isbot_channel_action(call: CallbackQuery, state: FSMContext):
    await Setting.filter(key="isbot_kanali").delete()
    
    await call.answer("🗑 Isbot kanali bazadan o'chirildi!", show_alert=True)
    await call.message.delete() # type: ignore
    await state.clear()

@admin_router.message(F.text == "👤 Adminlar")
async def admins_menu(message: Message):
    admin_list = "\n".join([f"• <a href='tg://user?id={admin_id}'>{admin_id}</a>" for admin_id in ADMIN_IDS])
    text = (
        "<b>👤 Botdagi adminlar ro'yxati:</b>\n\n"
        f"{admin_list}\n\n"
        "<i>💡 Diqqat: Yangi admin qo'shish yoki o'chirish uchun loyihadagi <b>.env</b> faylini tahrirlab, botni qayta ishga tushiring.</i>"
    )
    await message.answer(text)

@admin_router.message(F.text == "💵 Yechish tizimi")
async def payment_systems_menu(message: Message):
    markup = await payment_systems_kb()
    await message.answer(
        "<b>Quyidagilardan birini tanlang:</b>", 
        reply_markup=markup, 
    )

@admin_router.callback_query(F.data == "add_payment_system")
async def ask_payment_system(call: CallbackQuery, state: FSMContext):
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        "<b>Yechish to'lov tizimi nomini yuboring:</b>\n<i>(Masalan: Click, Payme, Uzcard, Humo)</i>", 
        reply_markup=cancel_kb
    )
    await state.set_state(AdminState.add_payment_system)

@admin_router.message(AdminState.add_payment_system)
async def save_payment_system(message: Message, state: FSMContext):
    sys_name = message.text.strip() # type: ignore
    
    # Bazaga yangi to'lov tizimini saqlash
    await PaymentSystem.create(name=sys_name)
    
    await message.answer(
        f"<b>✅ {sys_name} to'lov tizimi muvaffaqiyatli qo'shildi!</b>", 
        reply_markup=admin_menu_keyboard()
    )
    await state.clear()

@admin_router.callback_query(F.data.startswith("del_paysys_"))
async def delete_payment_system(call: CallbackQuery):
    sys_id = int(call.data.split("_")[2]) # type: ignore
    system = await PaymentSystem.get_or_none(id=sys_id)
    
    if system:
        name = system.name
        await system.delete()  # Bazadan o'chirish
        await call.answer(f"✅ {name} tizimi o'chirildi!", show_alert=True)
    else:
        await call.answer("⚠️ Tizim topilmadi yoki allaqachon o'chirilgan!", show_alert=True)
    
    # Tugmalarni yangilash
    markup = await payment_systems_kb()
    await call.message.edit_reply_markup(reply_markup=markup) # type: ignore


# ==========================================
# ☎️ MUROJAATGA JAVOB YOZISH (ADMIN QISMI)
# ==========================================
@admin_router.callback_query(F.data.startswith("reply_appeal_"))
async def ask_appeal_reply(call: CallbackQuery, state: FSMContext):
    # callback_data="reply_appeal_12345678" bo'lgani uchun 2-indeksdagi ID ni olamiz
    user_id = int(call.data.split("_")[2]) # type: ignore
    
    await call.message.answer( # type: ignore
        f"📝 <a href='tg://user?id={user_id}'>{user_id}</a> <b>uchun javobingizni yozing:</b>",
        reply_markup=cancel_kb
    )
    # ID ni keyingi qadamga o'tkazish uchun saqlab qo'yamiz
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminState.reply_appeal)
    await call.answer()

@admin_router.message(AdminState.reply_appeal)
async def send_appeal_reply(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Orqaga":
        await state.clear()
        return await message.answer("<b>🗄 Boshqaruv paneliga qaytdingiz.</b>", reply_markup=admin_menu_keyboard())

    data = await state.get_data()
    target_id = data.get("target_user_id")

    # Foydalanuvchiga boradigan xabar matni (PHP dagi bilan bir xil)
    reply_text = (
        f"<b>☎️ Administrator:</b>\n\n"
        f"<i>{message.text}</i>"
    )
    
    # Foydalanuvchi yana qayta javob yoza olishi uchun tugma
    user_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Javob yozish", callback_data="user_reply_to_admin")]
    ])

    try:
        # Foydalanuvchiga jo'natish
        await bot.send_message(
            chat_id=target_id, # type: ignore
            text=reply_text,
            reply_markup=user_markup
        )
        await message.answer("<b>✅ Javob yuborildi!</b>", reply_markup=admin_menu_keyboard())
    except Exception as e:
        await message.answer(f"<b>❌ Xatolik! Foydalanuvchi botni bloklagan bo'lishi mumkin.</b>", reply_markup=admin_menu_keyboard())
    
    await state.clear()

# ==========================================
# 🔄 OPENBUDGET SAYTIDAN OVOZLARNI OLISH
# ==========================================
@admin_router.message(F.text == "🔄 Saytdan ovozlarni yig'ish")
async def start_fetching_votes(message: Message, state: FSMContext):
    # Loyiha URL in bazadan tortamiz
    ob_setting = await Setting.get_or_none(key="openbudget_url")
    url = OPENBUDGET_URL
    if  ob_setting:
        url = ob_setting.value
    initiative_id = url.split("?")[0].split("/")[-1]
    
    await message.answer("⏳ <b>Saytga ulanilmoqda, captcha olinmoqda...</b>")
    
    # ID ni berib captcha chaqiramiz
    captcha_key, image_bytes, cookies, headers = await fetch_captcha(initiative_id)
    
    if not captcha_key or not image_bytes:
        return await message.answer("⚠️ <b>Saytga ulanishda xatolik!</b>\nOpenBudget hozircha bloklagan bo'lishi mumkin. Keyinroq urining.")
        
    photo = BufferedInputFile(image_bytes, filename="captcha.jpg")
    
    try:
        # Avval rasm sifatida yuborishga harakat qilamiz
        await message.answer_photo(
            photo=photo,
            caption="<b>🖼 Captcha rasmidagi sonni kiriting:</b>",
            reply_markup=cancel_kb
        )
    except Exception as e:
        # Agar Telegram "IMAGE_PROCESS_FAILED" bersa, fayl sifatida yuboramiz
        await message.answer_document(
            document=photo,
            caption="<b>🖼 Captcha rasmidagi sonni kiriting:</b>",
            reply_markup=cancel_kb
        )
    
    # Xotiraga keyingi qadamlar uchun saqlaymiz
    await state.update_data(
        initiative_id=initiative_id,
        captcha_key=captcha_key, 
        cookies=cookies,
        ob_headers=headers
    )
    await state.set_state(AdminState.waiting_for_ob_captcha)

@admin_router.message(AdminState.waiting_for_ob_captcha)
async def process_ob_captcha(message: Message, state: FSMContext, bot: Bot):
    # Agar orqaga bossa jarayonni to'xtatamiz
    if message.text == "◀️ Orqaga":
        await state.clear()
        return await message.answer("<b>🗄 Boshqaruv paneliga qaytdingiz.</b>", reply_markup=admin_menu_keyboard())

    captcha_result = message.text.strip() # type: ignore
    
    data = await state.get_data()
    initiative_id = data.get("initiative_id")
    captcha_key = data.get("captcha_key")
    cookies = data.get("cookies")
    headers = data.get("ob_headers")
    
    wait_msg = await message.answer("⏳ <b>Token olinmoqda...</b>")
    
    token = await fetch_token(initiative_id, captcha_key, captcha_result, cookies, headers) # type: ignore
    
    if not token:
        await state.clear()
        return await wait_msg.edit_text("❌ <b>Captcha xato kiritildi yoki sayt blokladi!</b>\nQaytadan urining.")
        
    await wait_msg.edit_text("🔄 <b>Ovozlar tekshirilmoqda. Bu biroz vaqt olishi mumkin...</b>")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        new_votes = await parse_and_save_votes(token, cookies, headers, initiative_id) # type: ignore
        await wait_msg.edit_text(
            f"✅ <b>Tekshiruv yakunlandi!</b>\n\n"
            f"📥 Yangi saqlangan ovozlar: <b>{new_votes} ta</b>\n"
            f"<i>Barcha eski ovozlar o'tkazib yuborildi.</i>"
        )
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_document")
        
        # 1. Barcha ovozlarni bazadan tortamiz (aynan shu loyiha uchun, vaqt bo'yicha kamayish tartibida)
        all_votes = await OBVote.filter(initiative_id=initiative_id).order_by("-vote_date").all()
        total_votes = len(all_votes)
        
        if total_votes == 0:
            await wait_msg.edit_text("🤷‍♂️ Hali hech qanday ovoz topilmadi.")
            return await state.clear()

        # 2. Excel fayl yaratish (xotirada)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ovozlar" # type: ignore
        
        # Excel sarlavhalari
        ws.append(["T/r", "Telefon raqam", "Ovoz berilgan vaqt",]) # type: ignore
        
        # Ustunlar kengligini chiroyli qilish
        ws.column_dimensions['B'].width = 18 # type: ignore
        ws.column_dimensions['C'].width = 20 # type: ignore
        # ws.column_dimensions['D'].width = 20
        
        json_data = []
        
        for i, vote in enumerate(all_votes, start=1):
            v_date_str = vote.vote_date.strftime("%Y-%m-%d %H:%M")
            # c_date_str = vote.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            # Excelga yozish
            ws.append([i, vote.phone_number, v_date_str]) # type: ignore
            
            # JSON uchun yig'ish
            json_data.append({
                "No": i,
                "phone_number": vote.phone_number,
                "vote_date": v_date_str
            })
            
        # Excelni baytlarga aylantirib, yuborishga tayyorlash
        current_time_file = datetime.now().strftime("%Y-%m-%d_%H-%M")
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        excel_filename = f"Ovozlar_{current_time_file}.xlsx"
        excel_file = BufferedInputFile(excel_buffer.read(), filename=excel_filename)
        
        # 3. JSON fayl yaratish (xotirada)
        json_bytes = json.dumps(json_data, indent=4).encode("utf-8")
        json_filename = f"Ovozlar_{current_time_file}.json"
        json_file = BufferedInputFile(json_bytes, filename=json_filename)
        
        # 4. Izoh matnini (Caption) tayyorlash
        last_vote_time = all_votes[0].vote_date.strftime("%Y-%m-%d %H:%M")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        caption = (
            # f"✅ <b>Tekshiruv yakunlandi!</b>\n\n"
            f"📥 Yangi saqlangan ovozlar: <b>{new_votes} ta</b>\n"
            f"📊 <b>Jami ovozlar soni:</b> {total_votes} ta\n"
            f"🕒 <b>Oxirgi yangilangan vaqt:</b> {current_time}\n"
            f"📩 <b>Eng oxirgi ovoz vaqti:</b> {last_vote_time}"
        )
        
        
        # Asosiy ma'lumotlar bilan Excel faylni jo'natamiz
        await message.answer_document(document=excel_file, caption=caption)
        # Ketidan JSON faylni jo'natamiz
        await message.answer_document(document=json_file, reply_markup=admin_menu_keyboard())
        
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ <b>Ovozlarni yig'ishda uzilish bo'ldi:</b>\n{str(e)}")
        await wait_msg.answer("<b>🗄 Boshqaruv paneli!</b>", reply_markup=admin_menu_keyboard())
        
    await state.clear()
