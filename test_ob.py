import aiohttp
import asyncio
import base64
import json
import random
import string

# Sizning tashlagan logingizdagi Initiative ID
INITIATIVE_ID = "9ee10df4-78e5-4441-b4c8-a98f5e2449a6"
PROXY = "http://213.230.110.191:3128"
PROXY = "http://213.230.110.191:3128"

def generate_access_captcha():
    """JavaScript dagi kabi tasodifiy 17 xonali matn yasab, Base64 ga o'giradi"""
    # JS dagi Math.random().toString(36) ga o'xshash tasodifiy matn
    chars = string.ascii_lowercase + string.digits
    rand_str = ''.join(random.choice(chars) for _ in range(17))
    # Base64 qilib kodlaymiz
    return base64.b64encode(rand_str.encode('utf-8')).decode('utf-8')

async def main():
    # Har safar yangi access-captcha generatsiya qilamiz
    access_captcha = generate_access_captcha()
    
    # Headerlarni aynan sizning brauzeringiznikidek qilib tuzamiz
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Access-Captcha": access_captcha,  # 👈 Eng muhim joyi!
        "Authorization": "", 
        "Priority": "u=1, i",
        "Referer": f"https://openbudget.uz/boards/initiatives/initiative/53/{INITIATIVE_ID}", # 👈 ID li referer
        "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
    
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        
        print(f"1. Asosiy sahifaga ulanish (Proxy orqali: {PROXY})...")
        try:
            await session.get(f"https://openbudget.uz/boards/initiatives/initiative/53/{INITIATIVE_ID}", proxy=PROXY)
            await asyncio.sleep(1) # Sayt bloklamasligi uchun kichik pauza
        except Exception as e:
            print(f"❌ Proxy orqali ulanishda xato (Sahifa): {e}")
            return
        
        print(f"1. Asosiy sahifaga ulanish (Proxy orqali: {PROXY})...")
        try:
            await session.get(f"https://openbudget.uz/boards/initiatives/initiative/53/{INITIATIVE_ID}", proxy=PROXY)
            await asyncio.sleep(1) # Sayt bloklamasligi uchun kichik pauza
        except Exception as e:
            print(f"❌ Proxy orqali ulanishda xato (Sahifa): {e}")
            return
        
        print("2. Captcha olinmoqda...")
        try:
            async with session.get("https://openbudget.uz/api/v2/vote/captcha-2", proxy=PROXY) as response:
                if response.status != 200:
                    print(f"❌ XATOLIK: Captcha olishda xato. Status: {response.status}")
                    print(await response.text())
                    return
                
                data = await response.json()
                captcha_key = data.get("captchaKey")
                img_b64 = data.get("image", "")

                    # Base64 dan rasmni ajratib olib faylga saqlash
                    if "," in img_b64:
                        img_b64 = img_b64.split(",")[1]
                    
                    with open("captcha.jpg", "wb") as f:
                        f.write(base64.b64decode(img_b64))
                    
                    print("✅ 'captcha.jpg' fayli saqlandi!")
        except Exception as e:
            print(f"❌ Proxy orqali ulanishda xato (Captcha): {e}")
            return

        # Terminaldan javobni kutish
        print("\nDIQQAT: Loyiha papkasidagi 'captcha.jpg' faylini oching!")
        captcha_result = input("👉 Captcha rasmidagi raqamni kiriting: ").strip()

        print("\n3. Token olinmoqda...")
        payload = {
            "initiativeId": INITIATIVE_ID,
            "captchaKey": captcha_key,
            "captchaResult": captcha_result
        }
        
        try:
            async with session.post("https://openbudget.uz/api/v2/info/get-initiative-token", json=payload, proxy=PROXY) as response:
                if response.status != 200:
                    print(f"❌ XATOLIK: Token olishda xato. Status: {response.status}")
                    print("Sabab:", await response.text())
                    return
                    
                token_data = await response.json()
                token = token_data.get("token")
                print(f"✅ Token muvaffaqiyatli olindi: {token}")
        except Exception as e:
            print(f"❌ Proxy orqali ulanishda xato (Token): {e}")
            return
        try:
            async with session.post("https://openbudget.uz/api/v2/info/get-initiative-token", json=payload, proxy=PROXY) as response:
                if response.status != 200:
                    print(f"❌ XATOLIK: Token olishda xato. Status: {response.status}")
                    print("Sabab:", await response.text())
                    return
                    
                token_data = await response.json()
                token = token_data.get("token")
                print(f"✅ Token muvaffaqiyatli olindi: {token}")
        except Exception as e:
            print(f"❌ Proxy orqali ulanishda xato (Token): {e}")
            return

        print("4. Ovozlar yig'ilmoqda (bu biroz vaqt olishi mumkin)...")
        all_votes = []
        page = 0
        
        while True:
            print(f"   📥 Sahifa: {page} yuklanmoqda...")
            url = f"https://openbudget.uz/api/v2/info/votes/{token}?page={page}"
            try:
                async with session.get(url, proxy=PROXY) as response:
                    if response.status != 200:
                        print(f"⚠️ {page}-sahifani olishda xatolik yuz berdi. To'xtatildi.")
                        break
                        
                    v_data = await response.json()
                    content = v_data.get("content", [])
                    
                    if not content:
                        break
                        
                    all_votes.extend(content)
                    
                    # Agar "last": true bo'lsa yoki ovozlar tugagan bo'lsa
                    if v_data.get("last") == True:
                        break
                        
                page += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"⚠️ Proxy orqali xatolik ({page}-sahifa): {e}")
                break
            try:
                async with session.get(url, proxy=PROXY) as response:
                    if response.status != 200:
                        print(f"⚠️ {page}-sahifani olishda xatolik yuz berdi. To'xtatildi.")
                        break
                        
                    v_data = await response.json()
                    content = v_data.get("content", [])
                    
                    if not content:
                        break
                        
                    all_votes.extend(content)
                    
                    # Agar "last": true bo'lsa yoki ovozlar tugagan bo'lsa
                    if v_data.get("last") == True:
                        break
                        
                page += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"⚠️ Proxy orqali xatolik ({page}-sahifa): {e}")
                break

        # Olingan barcha ovozlarni JSON faylga chiroyli qilib saqlash
        with open("votes.json", "w", encoding="utf-8") as f:
            json.dump(all_votes, f, ensure_ascii=False, indent=4)
            
        print(f"\n🎉 MUVAFFAQIYATLI! Jami {len(all_votes)} ta ovoz 'votes.json' fayliga saqlandi.")

if __name__ == "__main__":
    asyncio.run(main())
    