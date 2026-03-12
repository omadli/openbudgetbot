# OpenBudget Telegram Bot

## 🛠 Texnologiyalar
* **Python 3.10+**
* **Aiogram 3** (Telegram API bilan ishlash)
* **Tortoise-ORM** (Ma'lumotlar bazasi uchun Async ORM)
* **SQLite** (Ma'lumotlar bazasi)
* **Aerich** (Ma'lumotlar bazasi migratsiyalari uchun)

## 🚀 O'rnatish va Ishga tushirish

1. **Repozitoriyni yuklab oling va virtual muhit yarating:**
   ```bash
   git clone <repo_url>
   cd openbudgetbot
   python3 -m venv venv
   source venv/bin/activate  # Windows uchun: venv\Scripts\activate
   ```

2. Kutubxonalarni o'rnatish:

    ```bash
    pip install -r requirements.txt
    ```

3. Sozlamalarni to'g'rilang:
    .env.example faylidan nusxa olib, .env faylini yarating va o'z ma'lumotlaringizni kiriting:

    ```bash
    cp .env.example .env
    ```

4. Ma'lumotlar bazasini inisializatsiya qiling (Aerich yordamida):

    ```bash
    aerich init -t db.config.TORTOISE_ORM
    aerich init-db
    ```

5. Botni ishga tushiring:

    ```bash
    python main.py
    ```