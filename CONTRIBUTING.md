# Contributing to Sedaye Ma 🦁☀️

First off, thank you for considering contributing to Sedaye Ma! It's people like you that make this movement powerful.

## 🤝 Code of Conduct

This project is built on trust and safety. Contributors are expected to:
- Respect the privacy and safety of all users.
- Focus on the mission of combating online violations.
- Be respectful and constructive in all communications.

## 🐛 Found a Bug?

If you find a bug in the source code, you can help us by [submitting an issue](../issues) to our GitHub Repository. Even better, you can submit a Pull Request with a fix.

## 💡 Missing a Feature?

You can *request* a new feature by [submitting an issue](../issues) to our GitHub Repository. If you would like to implement a new feature, please submit an issue with a proposal for your work first, to be sure that we can use it.

## 💻 Development Guide

### Prerequisites
- Python 3.11+
- SQLite
- Docker (optional, but recommended)

### Setup
1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/sedaye-ma.git`
3. Create a virtual environment: `python -m venv venv`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up `.env` (see README)

### Coding Standards
- **Async First**: Use `async`/`await` for all I/O bound operations (database, network).
- **Type Hinting**: Use Python type hints for all function arguments and return values.
- **Logging**: Use the standard `logging` module, not `print()`.
- **Formatting**: Keep code clean and readable.

## 🚀 Validating Changes

Before submitting your PR, please verify:
1. The bot starts successfully: `python -m src.bot`
2. Database migrations (if any) are handled gracefully.
3. No sensitive data is committed.

## 📥 Submission Guidelines

### Submitting a Pull Request (PR)

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes.
4. Make sure your code lints.
5. Create the PR with a clear title and description.
6. Link any related issues.

Thank you for your support! ✌️👑✨
