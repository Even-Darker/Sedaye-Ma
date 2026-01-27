# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-27

### Added
- **User Statistics**: Admin command `/stats` to track active users (24h, 7d, 30d).
- **Email Campaigns**: Feature to organize mass emailing to officials.
- **Petitions**: System for signing and tracking petitions.
- **Solidarity Wall**: Anonymous messaging feature.
- **Free Configs**: Section to distribute V2Ray configs.
- **Welcome Hype**: Revamped start message with energetic text ("Cyber Army").
- **Broadcast Service**: Notification system for new campaigns and victories.
- **Project Structure**: Organized assets in `.github/assets`.
- **Documentation**: Persian (`README_fa.md`) and English (`README.md`) guides.
- **Deployment**: Docker support and GitHub Actions workflow.

### Changed
- **Database**: Migrated to include `last_active_at` and `email_campaigns` in `NotificationPreference`.
- **UI**: Improved keyboard layouts and added "Hype" styling.
- **Logging**: Enhanced logging for notification services.

### Fixed
- **Email Button**: Resolved `Url_invalid` error on "Open Email" buttons.
- **Markdown Escaping**: Fixed crashes caused by unescaped characters in welcome messages.
