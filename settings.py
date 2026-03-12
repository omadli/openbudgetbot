from environs import Env

env = Env()
env.read_env()

BOT_TOKEN = env.str("BOT_TOKEN")
ADMIN_IDS = env.list("ADMIN_IDS", subcast=int)
VOTES_GROUP = env.str("VOTES_GROUP")
OPENBUDGET_URL = env.str("OPENBUDGET_URL")
DB_URL = env.str("DB_URL")
VOTE_PRICE = env.int("VOTE_PRICE", default=5000)
REFERRAL_PRICE = env.int("REFERRAL_PRICE", default=1000)
