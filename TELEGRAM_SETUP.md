# Telegram Channel & Bot Setup Guide
## TechyUpdates Tech Events Finder Broadcast Integration

Follow these steps to configure your automated Telegram channel broadcasts for daily tech events drops:

---

### Step 1: Create a Telegram Bot via BotFather
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Start the chat and send `/newbot`.
3. Choose a friendly name (e.g., `TechyUpdates Events Radar Bot`).
4. Choose a unique username ending in `bot` (e.g., `techy_events_radar_bot`).
5. Copy the generated **HTTP API Token** (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`).
6. Set this as `TELEGRAM_BOT_TOKEN` in your `.env` or GitHub Repository Secrets.

---

### Step 2: Setup Your Telegram Channel
1. In Telegram, create a new public or private **Channel** (e.g., `TechyUpdates Tech Events & Conferences`).
2. Go to **Channel Info** -> **Administrators** -> **Add Administrator**.
3. Search for your bot by username (`@techy_events_radar_bot`) and add it as an **Admin**.
4. Grant the bot permissions to **Post Messages** and **Send Documents**.
5. Note your public channel username (e.g., `@techy_hackathons_updates`) or numerical Chat ID.
6. Set this as `TELEGRAM_COMMUNITY_CHANNEL_ID` in your `.env` or GitHub Secrets.

---

### Step 3: Configure GitHub Repository Secrets (for Daily Cron)
Navigate to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**:

| Secret Name | Description | Example / Note |
|:---|:---|:---|
| `GEMINI_API_KEY` | Google Gemini API Key | From [Google AI Studio](https://aistudio.google.com/) |
| `TELEGRAM_BOT_TOKEN` | Bot API Token | From `@BotFather` |
| `TELEGRAM_COMMUNITY_CHANNEL_ID` | Telegram Channel Username/ID | `@techy_hackathons_updates` |
| `CRON_SECRET` | Secret token for securing endpoints | e.g. `techyupdates_cron_secret_2026` |

---

### Step 4: Test Dispatch Locally
You can test Telegram dispatch by setting credentials in `.env` and running:
```bash
python api/trigger.py
```
If configured correctly, the bot will post the formatted summary and attach the `.xlsx` workbook directly to your channel.
