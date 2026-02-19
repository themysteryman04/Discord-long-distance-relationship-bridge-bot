# Changelog

All notable changes to the Echo Bot will be documented in this file.

## [v2.1.1] - 2026-02-19

### Fixed
- **Daily Question Button on Dyno Restart**: Fixed issue where the "Answer" button for daily questions stopped working after dyno restart
  - Added `QuestionView` to persistent views in `on_ready()`
  - Embedded question ID in message footer for recovery after restart
  - Enhanced button handler to extract question ID from message data
  - Ensures seamless user experience even after dyno restarts
- **Daily Dare Buttons After Restart**: Fixed dare-related buttons (Accept, Done, Verify) that stopped functioning after restart
  - Added `DarePendingView`, `DareActiveView`, and `DareVerifyView` as persistent views
  - Embedded dare metadata (dare_id, challenger_id, victim_id, reward) in embed footer
  - All dare button handlers now recover data from footer if lost
  - Buttons remain functional across dyno restarts
- **Moments Data Unpacking**: Fixed error in `get_random_moment()` that was missing the `source` column
  - Updated database query to include source field (SNAP/LOG)
  - Updated `flashback()` command to properly unpack 5-column tuple

### Technical Details
- Modified all interactive View classes to accept optional parameters for recovery
- Added footer-based metadata recovery pattern to all button handlers
- Ensured all persistent views are registered during `on_ready()` initialization
- Database query consistency improvements for moments table

---

## [v2.1.0] - 2026-02-05

### Added
- **Unified Wiki-Moments System**: Moments captured with `!snap` and `!log` commands are now fully integrated into the wiki system
- **Enhanced `!get` Command**: Can now search and retrieve both wiki entries AND moment captions
  - Search wiki entries by key name
  - Search moments by caption (case-insensitive)
  - Returns results with metadata (type, timestamp, capturer)
- **Unified `!wiki` Command**: Displays a complete combined index of all memories and moments
  - Shows all wiki entries and captured moments in one list
  - Clearly distinguishes between different types of content
- **Moment Type Indicators**: 
  - ⚡ **SNAP CHALLENGE** - moments from timed snap challenges
  - 📝 **MANUAL LOG** - manually logged moments
- **Channel Restrictions**: Wiki-related commands (`!wiki`, `!get`, `!moments`, `!remember`) now only work in the #wiki_of_us channel
- **Paginated Moments Browsing**: `!moments` command displays moments with Previous/Next navigation
- **Comprehensive README**: Added detailed documentation covering features, tech stack, deployment, and commands

### Changed
- **`!wiki` Command**: Updated to show a unified list combining wiki entries and moments
- **Start Menu**: Updated documentation to include new wiki-moments commands and moment capture types
- **Database Queries**: Modified to include moment source field (SNAP/LOG) in all moment retrieval operations

### Technical Details
- Added `get_moment_by_caption()` function to database for caption-based moment searching
- Updated `get_all_moments()` to include source field in query results
- Enhanced embed formatting for better visual distinction between wiki entries and moments

---

## [v2.0.0] - 2026-02-04

### Added
- **Wiki of Us Memory System**: Command-based memory storage with optional image attachments
  - `!remember <key> <value>` - Store memories
  - `!get <key>` - Retrieve specific memories via DM
  - `!wiki` - List all stored memories
- **Moments & Time Capsule**: Photo capture system with timestamps
  - `!snap <caption>` - Capture during timed challenges
  - `!log <caption>` - Manually log moments
  - `!flashback` - View random memories
- **Audio Capsules**: Voice message time-capsule system
  - Schedule voice notes for future delivery
  - Multiple delivery options (morning, random, custom)
- **Virtual Economy**: Us-Bucks currency system
  - Earn through challenges and completed tasks
  - Spend on shop items and rewards
- **Arcade Features**: Truth or Dare, Watch Party, Decision Room
- **Cloud Deployment**: Heroku integration with PostgreSQL database

---

## [v1.5.0] - 2026-02-05

### Fixed
- **Heartbeat Crash Prevention**: Fixed bot crash due to missing heartbeat checks
- **Spam Prevention**: Fixed spam bug in reminder system and daily question announcements
- **Dashboard Stability**: Improved stability of the live-stats dashboard updates

### Changed
- **Main.py Refactoring**: Major refactor of core event handling and command processing (262+ lines changed)

---

## [v1.4.0] - 2026-02-05

### Added
- **Stable AI Model**: Switched from experimental model to `gemini-3-flash-preview` for reliability
- **Question Format Fix**: Improved AI question generation with better theme handling
- **Dare Format Fix**: Robust parsing of AI-generated dares with proper fallback handling

### Changed
- **AI Manager Overhaul**: Major refactor of `ai_manager.py` with 95+ lines of improvements
- **Response Cleanup**: Enhanced text cleanup and validation for AI-generated content

### Fixed
- **429/503 Error Handling**: Fixed crashes from unstable AI model
- **Dare Parsing**: Fixed "invalid literal" errors in dare reward parsing

---

## [v1.3.0] - 2026-01-25

### Upgraded
- **AI Engine**: Upgraded from Gemini 2.0 to **Gemini 3.0 Flash** for improved performance and reliability
- **Response Quality**: Better generation of questions, dares, and suggestions with new model capabilities

---

## [v1.2.0] - 2026-01-25

### Added
- **Google GenAI Integration**: Added Google Gemini API support for AI-powered content generation
- **Requirements Update**: Added `google-genai` to project dependencies

### Changed
- **AI Manager**: Integrated new `ai_manager.py` module for centralized AI operations

---

## [v1.1.0] - 2026-01-25

### Added
- **Environment Security**: Proper `.env` file handling with `.gitignore` configuration
- **Heroku Deployment**: Full Heroku-ready setup with Procfile and database configuration

### Fixed
- **Filename Issues**: Fixed filename compatibility for Heroku deployment
- **Library Dependencies**: Added missing required libraries to requirements.txt

### Technical
- **Initial Heroku Setup**: Configured Dyno worker and PostgreSQL database connection
- **Database URL Detection**: Automatic detection of Heroku PostgreSQL via `DATABASE_URL`

---

## [v1.0.0] - 2025-12-27

### Initial Release
- **Daily Question System**: AI-generated relationship questions with hidden answers
- **Reminder System**: Multi-alert reminders (60, 45, 30, 15, 0 mins before events)
- **Snap Challenges**: Synchronized photo challenges across time zones
- **Shop System**: In-game store for purchasing rewards
- **Bounty Board**: Task posting with escrow payments
- **AI Integration**: Google Gemini for content generation
- **PostgreSQL Database**: Persistent data storage for all features

---

## How to Use This Changelog

- **[Added]**: New features introduced in this release
- **[Changed]**: Changes to existing functionality
- **[Fixed]**: Bug fixes
- **[Removed]**: Features removed in this release
- **[Deprecated]**: Features that will be removed in future releases

## Release Deployment

All releases are deployed to:
- **Production**: Heroku Cloud Dyno (`sakina-bot`)
- **Source**: GitHub (`themysteryman04/Discord-long-distance-relationship-bridge-bot`)

---

**Last Updated**: February 5, 2026 @ 08:35 UTC+8
