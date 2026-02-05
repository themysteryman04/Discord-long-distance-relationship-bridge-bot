# ❤️ Relationship Operating System (Discord Bot)

A smart, cloud-hosted Discord bot designed to bridge the gap for long-distance couples. It acts as a dedicated operating system for the relationship, managing memories, finances, and daily interactions using Generative AI.

## 🚀 Key Features
* **🧠 AI-Powered Interaction:** Uses **Google Gemini 3.0 flash preview** to generate daily deep-dive questions and creative date ideas.
* **📼 Audio Time Capsules:** A voice message system that "buries" messages to be delivered at specific future times (e.g., next morning, random 3-day delay).
* **📸 Multi-User 'BeReal' Game:** Synchronized photo challenges that trigger for both partners simultaneously across time zones.
* **💰 Virtual Economy:** A custom currency ("Us-Bucks") system backed by **PostgreSQL** to reward engagement and task completion.
* **☁️ Cloud Architecture:** Hosted on **Heroku** with a CI/CD pipeline and automated database backups.
* **📚 Shared Memory System:** Capture moments with `!snap` and `!log` commands, then browse and search through all memories with `!wiki` and `!moments`.

## 🛠️ Tech Stack
* **Language:** Python 3.10
* **Core Library:** Discord.py (Async)
* **AI Engine:** Google Gemini (GenAI SDK)
* **Database:** PostgreSQL (Hosted on Heroku)
* **Cloud Platform:** Heroku (Dynos & Schedulers)

## 📂 Project Structure
* `main.py`: Core bot logic, event loops, and command handling.
* `ai_manager.py`: Interface with Google Gemini API for content generation.
* `database.py`: PostgreSQL connection handling and CRUD operations.
* `config.py`: Channel IDs, player configurations, and shop items.

## 💽 Database Setup
This bot requires a PostgreSQL database.
1. **Heroku:** Simply add the Postgres add-on (`heroku addons:create heroku-postgresql`). The bot detects the `DATABASE_URL` automatically.
2. **Local:** Create a Postgres database and add the connection string to your `.env` file as `DATABASE_URL`.
3. **Initialization:** The bot automatically creates all necessary tables (`users`, `dares`, `wiki`, `moments`, etc.) on the first run.

## 🔧 Installation & Deployment

### Local Setup
```bash
# Clone the repository
git clone https://github.com/themysteryman04/Discord-long-distance-relationship-bridge-bot.git
cd Echo_bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your tokens
echo DISCORD_TOKEN=your_token_here > .env
echo GEMINI_API_KEY=your_gemini_key_here >> .env
echo DATABASE_URL=postgresql://... >> .env
```

### Deploy to Heroku
```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Set environment variables
heroku config:set DISCORD_TOKEN=your_token_here
heroku config:set GEMINI_API_KEY=your_gemini_key_here

# Deploy
git push heroku master
```

## 📋 Commands Overview

### Connection Modules
- **`!snap <caption>`** - Respond to a timed snap challenge (15 min window)
- **`!log <caption>`** - Manually log a memory anytime
- **`!flashback`** - See a random memory from the past
- **`!moments`** - Browse all captured moments with pagination

### Memory & Wiki
- **`!remember <key> <value>`** - Save a memory with optional image
- **`!wiki`** - View all stored memories and captured moments
- **`!get <key>`** - Retrieve a specific memory
- **`!moments`** - View all captured SNAP and LOG moments with source labels

### Economy & Shop
- **`!shop`** - View available items to purchase with Us-Bucks
- **`!dare`** - Accept a dare challenge
- **`!bounty <amount> <task>`** - Post a task for your partner to complete

### Utility
- **`!food <craving>`** - AI suggests 3 meal options
- **`!movie <genre>`** - AI suggests 3 movies
- **`!date <vibe>`** - AI suggests 3 date ideas
- **`!watch <title>`** - Sync movie start times

## 📊 Features in Detail

### Wiki & Moments System
The bot maintains a comprehensive memory system with two distinct types:
- **📝 Manually Stored Memories:** Saved with `!remember` command
- **📸 Captured Moments:** Auto-logged from `!snap` (timed challenges) and `!log` (manual captures)

All moments include:
- Caption/description
- Timestamp (with timezone support)
- Source type (SNAP/LOG)
- User who captured it
- Original image attachment

### Virtual Economy
Earn and spend "Us-Bucks" through:
- **Snap challenges:** +50 Us-Bucks
- **Manual logs:** +5 Us-Bucks
- **Completed dares:** Variable rewards

Shop items available:
- 💆‍♂️ 10-Minute Massage (50)
- 🍕 I Pick Dinner (80)
- 🧹 Get Out of 1 Chore (150)
- 🎬 Movie Night Choice (60)
- 🤫 End an Argument Veto (500)

## ⚙️ Configuration

Edit `config.py` to customize:
- Discord channel IDs for each feature
- Player IDs and timezones
- Shop item names and costs
- Relationship start date and last met date

## 🔐 Security
- All environment variables stored in `.env` (not committed to git)
- `.env` file is in `.gitignore`
- Discord token and Gemini API key never exposed in code
- Database credentials passed via Heroku config

## 🚀 Deployment
The bot is automatically deployed to Heroku via `git push heroku master`. The `Procfile` defines it as a worker dyno that runs continuously.

## 📝 License
Private project for personal use.

## 🤝 Support
For issues or feature requests, check the GitHub Issues page.

---

**Built with ❤️ for long-distance love** 💑
