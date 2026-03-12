import aiohttp
import asyncio
import base64
import random
import string
from datetime import datetime
from db.models import OBVote

def generate_access_captcha():
    """Tasodifiy 17 xonali access-captcha generatsiya qilish"""
    chars = string.ascii_lowercase + string.digits
    rand_str = ''.join(random.choice(chars) for _ in range(17))
    return base64.b64encode(rand_str.encode('utf-8')).decode('utf-8')

def get_headers(initiative_id: str):
    """Har bir so'rov uchun yangi va ishonchli headerlar"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "uz,en-US;q=0.9,en;q=0.8,ru;q=0.7",
        "Access-Captcha": generate_access_captcha(),
        "Authorization": "",
        "Priority": "u=1, i",
        "Referer": f"https://openbudget.uz/boards/initiatives/initiative/53/{initiative_id}",
        "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

async def fetch_captcha(initiative_id: str):
    headers = get_headers(initiative_id)
    url = "https://openbudget.uz/api/v2/vote/captcha-2"
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # Sessiya ochish
        await session.get(f"https://openbudget.uz/boards/initiatives/initiative/53/{initiative_id}")
        await asyncio.sleep(0.5)
        
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                captcha_key = data.get("captchaKey")
                captcha_b64 = data.get("image", "")
                
                if "," in captcha_b64:
                    captcha_b64 = captcha_b64.split(",")[1]
                
                # 1. Bo'sh joy va yangi qatorlarni tozalash
                captcha_b64 = captcha_b64.replace(" ", "").replace("\n", "")
                
                # 2. Base64 uchun yetishmayotgan "=" (padding) larni qo'shish
                captcha_b64 += "=" * ((4 - len(captcha_b64) % 4) % 4)
                
                image_bytes = base64.b64decode(captcha_b64)
                
                # Cookielarni saqlab olish
                cookies = {}
                for cookie in session.cookie_jar:
                    cookies[cookie.key] = cookie.value
                    
                # Keyingi bosqichlarda ham shu header va cookielarni ishlatamiz
                return captcha_key, image_bytes, cookies, headers
            return None, None, None, None

async def fetch_token(initiative_id: str, captcha_key: str, captcha_result: str, cookies: dict, headers: dict):
    url = "https://openbudget.uz/api/v2/info/get-initiative-token"
    payload = {
        "initiativeId": initiative_id,
        "captchaKey": captcha_key,
        "captchaResult": captcha_result
    }
    
    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("token")
            return None

async def parse_and_save_votes(token: str, cookies: dict, headers: dict, initiative_id: str) -> int:
    new_votes_count = 0
    page = 0
    
    # Bazadagi eng oxirgi (eng yangi) ovozni topib olamiz
    last_vote = await OBVote.filter(initiative_id=initiative_id).order_by("-vote_date").first()
    last_vote_date = last_vote.vote_date.replace(tzinfo=None) if last_vote else None

    async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
        while True:
            url = f"https://openbudget.uz/api/v2/info/votes/{token}?page={page}"
            async with session.get(url) as response:
                if response.status != 200:
                    break
                    
                data = await response.json()
                content = data.get("content", [])
                
                if not content:
                    break
                
                stop_parsing = False
                for item in content:
                    phone = item.get("phoneNumber")
                    v_date_str = item.get("voteDate")
                    
                    v_date = datetime.strptime(v_date_str, "%Y-%m-%d %H:%M")
                    
                    if last_vote_date and v_date < last_vote_date:
                        stop_parsing = True
                        break
                        
                    try:
                        # Saqlashda initiative_id ni ham qo'shib yuboramiz
                        obj, created = await OBVote.get_or_create(
                            initiative_id=initiative_id, # 👈 Mana bu yerda
                            phone_number=phone, 
                            vote_date=v_date
                        )
                        if created:
                            new_votes_count += 1
                    except Exception:
                        pass
                
                if stop_parsing or data.get("last") == True:
                    break
                
                page += 1
                await asyncio.sleep(0.5)
                
    return new_votes_count