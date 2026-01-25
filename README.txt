# ❤️ Relationship Operating System (Discord Bot)

A smart, cloud-hosted Discord bot designed to bridge the gap for long-distance couples. It acts as a dedicated operating system for the relationship, managing memories, finances, and daily interactions using Generative AI.

## 🚀 Key Features
* **🧠 AI-Powered Interaction:** Uses **Google Gemini 3.0 flash preview** to generate daily deep-dive questions and creative date ideas.
* **📼 Audio Time Capsules:** A voice message system that "buries" messages to be delivered at specific future times (e.g., next morning, random 3-day delay).
* **📸 Multi-User 'BeReal' Game:** Synchronized photo challenges that trigger for both partners simultaneously across time zones.
* **💰 Virtual Economy:** A custom currency ("Us-Bucks") system backed by **PostgreSQL** to reward engagement and task completion.
* **☁️ Cloud Architecture:** Hosted on **Heroku** with a CI/CD pipeline and automated database backups.

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