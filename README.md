# 🦅 Sedaye Ma (Our Voice)

> **Coordinating collective action against online violations.**

Sedaye Ma is a Telegram bot designed to help communities organize and report violations on social media platforms (focusing on Instagram). It facilitates the reporting of harmful content such as violence, misinformation, propaganda, and harassment.

![Project Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- **Organized Reporting**: View daily targets for reporting with specific reasons.
- **Verification System**: Automated Instagram profile validation to ensure targets exist.
- **User Suggestions**: Community members can suggest new targets (requires Admin approval).
- **Admin Panel**: Complete management system within Telegram for admins to approve/reject targets and manage listing.
- **Victories**: Section to celebrate successful removals and community impact.
- **Privacy Focused**: Built with user privacy in mind.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- An Admin Telegram ID (your user ID)

### Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/sedaye-ma.git
   cd sedaye-ma
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   Copy `.env.example` to `.env` and fill in your details:
   ```bash
   cp .env.example .env
   # Edit .env with your TELEGRAM_BOT_TOKEN and SUPER_ADMIN_IDS
   ```

5. **Run the bot**
   ```bash
   python -m src.bot
   ```

## 🛠 Deployment

### Option 1: Docker (Recommended)

1. **Build the image**
   ```bash
   docker build -t sedaye-ma .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     -e TELEGRAM_BOT_TOKEN="your_token" \
     -e SUPER_ADMIN_IDS="12345678" \
     -v $(pwd)/data:/app/data \
     --name sedaye-ma \
     sedaye-ma
   ```

### Option 2: GitHub Actions (Automated)

This repository includes a GitHub Actions workflow to automatically build and deploy the bot.

**What you need:**
1. A Server/VPS (Ubuntu recommended) with Docker installed.
2. In your GitHub Repo Settings -> Secrets, add:
   - `HOST`: Your server IP address
   - `USERNAME`: Server SSH username (e.g. root)
   - `PASSWORD`: Server SSH password (OR `KEY` for SSH Key)
   - `TELEGRAM_BOT_TOKEN`: Your bot token
   - `SUPER_ADMIN_IDS`: Admin ID(s)

The workflow will:
1. Build the Docker image on every push to `main`.
2. Push the image to GitHub Container Registry (GHCR).
3. SSH into your server, pull the new image, and restart the bot.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
