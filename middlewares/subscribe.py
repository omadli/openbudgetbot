from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db.models import Channel

class CheckSubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id # type: ignore 
        bot = data['bot']

        # Bazadan faqat majburiy kanallarni tortib olamiz
        channels = await Channel.filter(is_mandatory=True).all()
        if not channels:
            return await handler(event, data)

        unsubscribed_channels = []
        keyboard = []

        for i, channel in enumerate(channels):
            try:
                chat_member = await bot.get_chat_member(chat_id=channel.username, user_id=user_id)
                if chat_member.status in ['left', 'kicked']:
                    unsubscribed_channels.append(channel)
                    url = channel.username.replace("@", "")
                    keyboard.append([InlineKeyboardButton(text=f"❌ {i+1}-kanal", url=f"https://t.me/{url}")])
            except Exception:
                pass # Bot kanalda admin bo'lmasa xato tashlamasligi uchun

        # Agar a'zo bo'lmagan kanallari bo'lsa:
        if unsubscribed_channels:
            keyboard.append([InlineKeyboardButton(text="🔄 Tekshirish", callback_data="check_subs")])
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            text = "<b>⚠️ Botdan to'liq foydalanish uchun quyidagi kanallarimizga obuna bo'ling!</b>"

            if isinstance(event, Message):
                await event.answer(text, reply_markup=markup, parse_mode="HTML")
            elif isinstance(event, CallbackQuery) and event.data != "check_subs":
                await event.message.answer(text, reply_markup=markup, parse_mode="HTML") # type: ignore
                await event.answer()
            return # Kod shu yerda to'xtaydi, keyingi handlerlarga o'tmaydi

        # Agar hammasiga a'zo bo'lsa, bot odatdagidek ishlayveradi
        return await handler(event, data)
