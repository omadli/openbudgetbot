import re
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from db.models import User, Vote, Withdrawal, Setting, Channel, PaymentSystem
from states.forms import UserState
from keyboards.reply import get_main_menu, cancel_kb
from keyboards.inline import vote_inline_menu, admin_verify_menu, sub_keyboard
from settings import ADMIN_IDS, REFERRAL_PRICE, VOTES_GROUP

user_router = Router()

async def get_unsubscribed_channels(user_id: int, bot: Bot) -> list:
    channels = await Channel.filter(is_mandatory=True).all()
    unsubbed = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel.username, user_id=user_id)
            if member.status in ['left', 'kicked']:
                unsubbed.append(channel)
        except Exception:
            pass # Bot admin bo'lmasa xato tashlamasligi uchun
    return unsubbed

async def check_and_block_if_unsubbed(message: Message, bot: Bot) -> bool:
    unsubbed = await get_unsubscribed_channels(message.from_user.id, bot) # type: ignore
    if unsubbed:
        await message.answer(
            "<b>⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarimizga obuna bo'ling!</b>",
            reply_markup=sub_keyboard(unsubbed)
        )
        return True
    return False

async def process_referral(user: User, bot: Bot):
    if user.referred_by and not user.is_ref_rewarded:
        referrer = await User.get_or_none(telegram_id=user.referred_by)
        if referrer:
            ref_setting = await Setting.get_or_none(key="ref_price")
            ref_price = int(ref_setting.value) if ref_setting else REFERRAL_PRICE

            referrer.balance += ref_price
            referrer.referral_count += 1
            await referrer.save()

            user.is_ref_rewarded = True
            await user.save()

            try:
                await bot.send_message(
                    chat_id=referrer.telegram_id,
                    text=f"<b>Sizda yangi taklif mavjud! Hisobingizga {ref_price} so'm qo'shildi.</b>"
                )
            except: pass

@user_router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id # type: ignore
    ref_id = command.args

    user, created = await User.get_or_create(
        telegram_id=user_id,
        defaults={"full_name": message.from_user.full_name, "username": message.from_user.username} # type: ignore
    )

    # 1. Referal ID ni saqlash (hali pul bermaymiz)
    if created and ref_id and ref_id.isdigit() and int(ref_id) != user_id:
        user.referred_by = int(ref_id)
        await user.save()

    # 2. Obunani tekshirish
    unsubbed = await get_unsubscribed_channels(user_id, bot)
    if unsubbed:
        await message.answer(
            "<b>⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarimizga obuna bo'ling!</b>",
            reply_markup=sub_keyboard(unsubbed)
        )
        return

    # 3. Agar majburiy kanallar yo'q bo'lsa YOKI hammasiga a'zo bo'lsa, referal hisoblanadi
    await process_referral(user, bot)

    is_admin = user_id in ADMIN_IDS
    start_text_record = await Setting.get_or_none(key="start_text")
    await message.answer_video(
        video="BAACAgIAAxkBAAEhtXhpsraxDJAqlUK1Yo2bKpmtg_xs5QACL5UAAmMzkUkO-mYGfckxjToE",
    )
    start_text = start_text_record.value if start_text_record else "<b>🖥 Asosiy menyudasiz</b>"
    
    await message.answer(start_text, reply_markup=get_main_menu(is_admin))

@user_router.callback_query(F.data == "check_subs")
async def check_subscriptions_callback(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    unsubbed = await get_unsubscribed_channels(user_id, bot)

    if unsubbed:
        return await call.answer("Iltimos, barcha kanallarga a'zo bo'ling!", show_alert=True)

    await call.message.delete() # type: ignore
    user = await User.get(telegram_id=user_id)
    
    # Endi a'zo bo'lgani uchun referal puli beriladi
    await process_referral(user, bot)

    is_admin = user_id in ADMIN_IDS
    start_text_record = await Setting.get_or_none(key="start_text")
    start_text = start_text_record.value if start_text_record else "<b>🖥 Asosiy menyudasiz</b>"
    
    await call.message.answer( # type: ignore
        f"<b>✅ Kanallarga muvaffaqiyatli a'zo bo'ldingiz!</b>\n\n{start_text}", 
        reply_markup=get_main_menu(is_admin)
    )

@user_router.message(F.text == "🎯 Ovoz Berish")
async def vote_start(message: Message, bot: Bot):
    if await check_and_block_if_unsubbed(message, bot): return
    markup = await vote_inline_menu()
    await message.answer(
        "<b>💾 Saytga kirib ovoz bering va <i>«🎯 Ovoz Berdim»</i> tugmasini bosing!</b>",
        reply_markup=markup
    )

@user_router.callback_query(F.data == "ovoz_berdim")
async def ask_phone(call: CallbackQuery, state: FSMContext, bot: Bot):
    if await check_and_block_if_unsubbed(call.message, bot): return # type: ignore
    await call.message.delete() # type: ignore
    await call.message.answer( # type: ignore
        "<b>📞 Telefon raqamingizni kiriting:\n\n✅ Namuna: +998931234567</b>",
        reply_markup=cancel_kb
    )
    await state.set_state(UserState.vote_phone)

@user_router.message(UserState.vote_phone)
async def process_phone(message: Message, state: FSMContext):
    if message.text == "◀️ Orqaga":
        await state.clear()
        is_admin = message.from_user.id in ADMIN_IDS # type: ignore
        return await message.answer("<b>🖥 Asosiy menyudasiz</b>", reply_markup=get_main_menu(is_admin))

    phone = message.text.strip() # type: ignore
    if not re.match(r"^\+998\d{9}$", phone):
        return await message.answer("Noto'g'ri format! Iltimos, namunadagidek kiriting: +998931234567")

    exists = await Vote.get_or_none(phone_number=phone)
    if exists:
        if exists.status == "pending":
            return await message.answer("Ushbu raqamdan berilgan ovoz hozirda tekshirish jarayonida.")
        elif exists.status == "approved":
            return await message.answer("Ushbu raqamdan avval ovoz berilgan")

    await state.update_data(phone=phone)
    await message.answer("<b>🧬 Ovoz berganingiz haqidagi ScreenShotni yuboring!</b>", )
    await state.set_state(UserState.vote_screenshot)

@user_router.message(UserState.vote_screenshot, F.photo)
async def process_screenshot(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    phone = data['phone']
    photo_id = message.photo[-1].file_id # type: ignore

    vote = await Vote.create(
        user_id=message.from_user.id, # type: ignore
        phone_number=phone,
        screenshot_id=photo_id
    )

    await message.answer(
        "<b>📮 So'rovingiz yuborildi.\n⏰ Administratorlarimiz 15 daqiqa ichida tekshirib chiqishadi. Agar tasdiqlansa balansingizga pul qo'shiladi!</b>",
        reply_markup=get_main_menu(message.from_user.id in ADMIN_IDS) # type: ignore 
    )
    await state.clear()

    # Adminga yuborish
    
    caption = "\n".join([f"📄 <b>Yangi ovoz:</b>\n",
            f"<b>👤 Foydalanuvchi:</b> {message.from_user.mention_html()}", # type: ignore
            f"<b>🔎 ID raqami:</b> <code>{message.from_user.id}</code>", # type: ignore
            f"<b>📞 Telefon raqami:</b> {phone}"]) # type: ignore
    await bot.send_photo(
        chat_id=VOTES_GROUP,
        photo=photo_id,
        caption=caption,
        reply_markup=admin_verify_menu(vote.id, message.from_user.id) # type: ignore
    )

@user_router.callback_query(F.data.startswith("pay_"))
async def select_payment_system(call: CallbackQuery, state: FSMContext):
    system_name = call.data.split("_")[1] # type: ignore
    user = await User.get(telegram_id=call.from_user.id)
    
    # Minimal pul yechish summasini bazadan olish
    min_withdraw_setting = await Setting.get_or_none(key="min_withdraw")
    min_withdraw = int(min_withdraw_setting.value) if min_withdraw_setting else 30000
    
    if user.balance < min_withdraw:
        return await call.answer(f"⚠️ Minimal pul yechish narxi: {min_withdraw} so'm", show_alert=True)
        
    await state.update_data(system_name=system_name)
    await call.message.edit_text(f"<b>✅ {system_name} qabul qilindi!</b>\n\nHamyon raqamini yuboring:", ) # type: ignore
    await state.set_state(UserState.withdraw_wallet)

@user_router.message(UserState.withdraw_wallet)
async def enter_wallet(message: Message, state: FSMContext):
    await state.update_data(wallet=message.text)
    await message.answer("<b>❕Qancha pul yechmoqchisiz?</b>", )
    await state.set_state(UserState.withdraw_amount)

@user_router.message(UserState.withdraw_amount)
async def enter_amount(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit(): # type: ignore
        return await message.answer("Iltimos, faqat raqam kiriting.")
        
    amount = int(message.text)  # type: ignore
    user = await User.get(telegram_id=message.from_user.id)  # type: ignore
    data = await state.get_data()
    
    if amount > user.balance:
        return await message.answer("⚠️ <b>Hisobingizda mablag' yetarli emas!</b>")
        
    # Balansdan yechish va bazaga yozish
    user.balance -= amount
    await user.save()
    
    withdrawal = await Withdrawal.create(
        user=user,
        system_name=data['system_name'],
        wallet_number=data['wallet'],
        amount=amount
    )
    
    await message.answer("<b>✉️ Pul yechib olish uchun adminga ariza yuborildi!</b>")
    await state.clear()
    
    # --- CHALA QOLGAN QISM TO'LDIRILDI ---
    
    valyuta_record = await Setting.get_or_none(key="valyuta")
    pul = valyuta_record.value if valyuta_record else "so'm"
    
    # Adminga/Kanalga ketadigan xabar matni
    admin_text = (
        f"💵 <a href='tg://user?id={user.telegram_id}'>{user.full_name}</a> <b>pul yechib olmoqchi!</b>\n\n"
        f"• <b>To'lov turi:</b> {data['system_name']}\n"
        f"• <b>Pul miqdori:</b> {amount} {pul}\n"
        f"• <b>Hamyon raqami:</b> <code>{data['wallet']}</code>"
    )
    
    # Inline tugmalar (withdraw_paid_{id} va withdraw_reject_{id})
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ To'landi", callback_data=f"withdraw_paid_{withdrawal.id}"),
            InlineKeyboardButton(text="❌ To'lanmadi", callback_data=f"withdraw_reject_{withdrawal.id}")
        ]
    ])
    
    channel_setting = await Setting.get_or_none(key="tolovlar_kanali")
    
    # Agar to'lovlar kanali sozlangan bo'lsa, o'sha yerga yuboramiz
    if channel_setting and channel_setting.value:
        try:
            await bot.send_message(
                chat_id=channel_setting.value, 
                text=admin_text, 
                reply_markup=markup
            )
            return # Kanalga yuborilsa, shu joyda funksiya to'xtaydi
        except Exception:
            pass # Agar kanalga yuborishda bot admin bo'lmasa xato beradi va pastga o'tadi
            
    # Agar kanal topilmasa yoki xatolik bersa, barcha adminlar lichkasiga yuboramiz
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id, 
                text=admin_text, 
                reply_markup=markup
            )
        except Exception:
            pass

# --- 💵 HISOBIM ---
@user_router.message(F.text == "💵 Hisobim")
async def my_account(message: Message, bot: Bot):
    if await check_and_block_if_unsubbed(message, bot): return
    
    user = await User.get(telegram_id=message.from_user.id) # type: ignore
    valyuta_record = await Setting.get_or_none(key="valyuta")
    pul = valyuta_record.value if valyuta_record else "so'm"
    bot_me = await bot.get_me()
    
    text = (
        f"🏛 <b>Sizning botdagi hisobingiz</b>\n\n"
        f"<b>ID raqamingiz:</b> <code>{user.telegram_id}</code>\n"
        f"<b>Asosiy balans:</b> {user.balance} {pul}\n"
        f"<b>Takliflaringiz:</b> {user.referral_count} ta\n\n"
        f"<b>@{bot_me.username} | Official</b>"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Pul yechish", callback_data="withdraw_money")]
    ])
    
    # Rasm bilan yuborish (PHP dagi kabi)
    await message.answer_photo(
        photo="https://t.me/Fast_Sim_News/23", 
        caption=text, 
        reply_markup=markup
    )
    
@user_router.callback_query(F.data == "withdraw_money")
async def show_payment_systems(call: CallbackQuery):
    systems = await PaymentSystem.all()
    if not systems:
        return await call.answer("⚠️ Pul yechish tizimlari qo'shilmagan!", show_alert=True)
        
    kb = [[InlineKeyboardButton(text=sys.name, callback_data=f"pay_{sys.name}")] for sys in systems]
    await call.answer()
    await call.message.delete() # type: ignore
    await call.message.answer("<b>💳 Pul yechish tizimlaridan birini tanlang:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)) # type: ignore

# --- 🖇️ TAKLIF QILISH ---
@user_router.message(F.text == "🖇️ Taklif qilish")
async def referral_link(message: Message, bot: Bot):
    if await check_and_block_if_unsubbed(message, bot): return
    
    user = await User.get(telegram_id=message.from_user.id) # type: ignore
    ref_setting = await Setting.get_or_none(key="ref_price")
    ref_price = ref_setting.value if ref_setting else str(REFERRAL_PRICE)
    
    valyuta_record = await Setting.get_or_none(key="valyuta")
    pul = valyuta_record.value if valyuta_record else "so'm"
    
    bot_me = await bot.get_me()
    link = f"https://t.me/{bot_me.username}?start={user.telegram_id}"
    
    text = (
        f"<b>🔗 Sizning referal havolangiz:</b>\n\n"
        f"▫️ <code>{link}</code> ▫️\n\n"
        f"<b>▪️👤 1 ta taklif uchun {ref_price} {pul} beriladi▪️</b>\n\n"
        f"<b>🔔 Takliflaringiz :</b> {user.referral_count} ta"
    )
    await message.answer_photo(photo="https://t.me/Fast_Sim_News/26", caption=text)

# --- 📑 YO'RIQNOMA ---
@user_router.message(F.text == "📑 Yo'riqnoma")
async def bot_instructions(message: Message):
    admin_setting = await Setting.get_or_none(key="admin_user")
    admin_user = admin_setting.value if admin_setting else "@admin"
    
    text = (
        "❓<b>Bot nima qila oladi?:</b>\n"
        "— Botimiz orqali OpenBudget uchun ovoz berib pul ishlashingiz mumkin. To'plangan pullarni telefon raqamingizga paynet tariqasida yoki karta raqamingizga yechib olishingiz mumkin.\n\n"
        "❓<b>Pulni qanday yechib olaman?:</b>\n"
        "— 💵 Hisobim bo'limiga o'ting va «💰 Pul yechish» tugmasini bosing. To'lov tizimlaridan birini tanlang. Karta raqamingiz yoki telefon raqamingizni kiriting. Administratorimiz hisobingizni to'ldiradi.\n\n"
        f"🙆‍♂️ <b>Bizning admin:</b> {admin_user}"
    )
    await message.answer(text)

# --- 📃 TO'LOVLAR ---
@user_router.message(F.text == "📃 To'lovlar")
async def payment_channel_info(message: Message):
    channel = await Setting.get_or_none(key="isbot_kanali")
    channel_link = channel.value if channel else "Hali sozlanmagan"
    await message.answer(f"<b>📮 To'lovlar Kanali:</b> {channel_link}")

# --- ☎️ MUROJAAT ---
@user_router.message(F.text == "☎️ Murojaat")
async def contact_support(message: Message, state: FSMContext):
    admin_setting = await Setting.get_or_none(key="admin_user")
    admin_user = admin_setting.value if admin_setting else "@admin"
    
    await message.answer(
        f"<b>📞 Aloqa markazi: {admin_user}</b>\n\n<b>📝 Murojaat matnini yuboring:</b>",
        reply_markup=cancel_kb
    )
    await state.set_state(UserState.appeal_text)

@user_router.message(UserState.appeal_text)
async def process_appeal(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Orqaga":
        await state.clear()
        is_admin = message.from_user.id in ADMIN_IDS # type: ignore
        return await message.answer("<b>🖥 Asosiy menyudasiz</b>", reply_markup=get_main_menu(is_admin))
    
    text_to_admin = (
        f"<b>📨 Yangi murojaat keldi:</b> <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>\n\n" # type: ignore
        f"<b>📑 Murojaat matni:</b> {message.text}"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Javob yozish", callback_data=f"reply_appeal_{message.from_user.id}")] # type: ignore
    ])
    
    # Barcha adminlarga yuborish
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text_to_admin, reply_markup=markup)
        except Exception:
            pass # Admin botni bloklagan bo'lishi mumkin
            
    is_admin = message.from_user.id in ADMIN_IDS # type: ignore
    await message.answer("<b>✅ Murojaatingiz yuborildi.</b>\n<i>Tez orada javob qaytaramiz!</i>", reply_markup=get_main_menu(is_admin))
    await state.clear()

@user_router.callback_query(F.data == "user_reply_to_admin")
async def ask_user_reply_to_admin(call: CallbackQuery, state: FSMContext):
    await call.message.delete() # type: ignore
    await call.message.answer("<b>📝 Murojaat matnini yuboring:</b>", reply_markup=cancel_kb) # type: ignore
    await state.set_state(UserState.appeal_text)
    