from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    vote_phone = State()
    vote_screenshot = State()
    withdraw_wallet = State()
    withdraw_amount = State()
    appeal_text = State()

class AdminState(StatesGroup):
    broadcast_text = State()
    broadcast_forward = State()
    manage_user_id = State()
    add_balance = State()
    deduct_balance = State()
    set_vote_price = State()
    set_ref_price = State()
    set_min_withdraw = State()
    add_channel = State()
    add_payment_system = State()
    reply_appeal = State()
    set_ob_url = State()
    set_admin_user = State()
    reply_appeal = State()
    add_payment_channel = State()
    add_isbot_channel = State()
    waiting_for_ob_captcha = State()
    