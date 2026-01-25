# 🔥 صدای ما - Sedaye Ma

<div align="center">

**The Voice of the People**

A privacy-first, open-source Telegram bot built in solidarity with Iranian people.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)

[فارسی](#فارسی) | [English](#english)

</div>

---

## فارسی

### صدای ما چیست؟

صدای ما یک ربات تلگرام متن‌باز است که برای تقویت صدای مردم ایران ساخته شده است. این ربات به کاربران کمک می‌کند تا صفحات اینستاگرام ناقض قوانین را گزارش کنند - همه به صورت ناشناس و امن.

### ویژگی‌ها

- 🎯 **لیست صفحات برای گزارش** - مشاهده صفحات با اولویت و قالب‌های گزارش آماده
- 🏆 **تالار افتخار** - صفحاتی که با موفقیت حذف شده‌اند
- 📊 **آمار زنده** - تأثیر جمعی جامعه
- 📢 **اطلاعیه‌ها** - اخبار و فراخوان‌های مهم
- ✊ **پتیشن‌ها** - امضای درخواست‌های آنلاین
- 💬 **دیوار همبستگی** - پیام‌های ناشناس از سراسر جهان
- 📚 **راهنمای امنیت دیجیتال**

### 🔒 حریم خصوصی

- **هیچ اطلاعات کاربری ذخیره نمی‌شود**
- تعامل کاملاً ناشناس
- کد متن‌باز برای شفافیت کامل

---

## English

### What is Sedaye Ma?

Sedaye Ma ("Our Voice" in Persian) is an open-source Telegram bot built to amplify the voice of Iranian people. It helps users report Instagram pages that violate platform policies - all anonymously and safely.

### Features

- 🎯 **Instagram Target List** - View prioritized pages with ready-to-use report templates
- 🏆 **Victory Wall** - Celebrate successfully removed pages
- 📊 **Live Statistics** - Track community impact in real-time
- 📢 **Announcements** - Important news and calls to action
- ✊ **Petitions** - Sign important online petitions
- 💬 **Solidarity Wall** - Anonymous messages from around the world
- 📚 **Digital Safety Guide** - Stay safe while participating

### 🔒 Privacy Guarantees

- **Zero user data stored** - No IDs, names, or handles
- Fully anonymous interactions
- Open source for complete transparency
- Only admin IDs stored (with explicit consent)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- A Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Sedaye_Ma.git
cd Sedaye_Ma

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your bot token and admin ID
```

### Configuration

Edit `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
SUPER_ADMIN_IDS=your_telegram_user_id
DATABASE_URL=sqlite+aiosqlite:///./data/sedaye_ma.db
ENCRYPTION_KEY=generate_with_cryptography_fernet
ENVIRONMENT=development
```

### Run the Bot

```bash
python -m src.bot
```

---

## 🏗️ Project Structure

```
Sedaye_Ma/
├── config/                 # Configuration
│   ├── settings.py         # Environment settings
│   └── messages_fa.py      # Persian UI strings
├── src/
│   ├── bot.py              # Main entry point
│   ├── database/           # SQLAlchemy models
│   ├── handlers/           # Telegram handlers
│   ├── services/           # Business logic
│   └── utils/              # Utilities
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🛡️ Admin Commands

| Command | Description |
|---------|-------------|
| `/admin` | Open admin panel |
| Add Target | Add new Instagram page to report |
| Mark Victory | Mark a page as successfully removed |
| Moderate | Approve/reject solidarity messages |

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## ⚠️ Disclaimer

This bot is designed for **peaceful, legal reporting** of content that violates Instagram's own policies. Users are encouraged to use official platform reporting tools. We do not encourage any illegal activities.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**زن، زندگی، آزادی**

**Woman, Life, Freedom**

✊🔥

</div>
