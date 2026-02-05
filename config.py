# config.py

CHANNELS = {
    # --- DASHBOARD ---
    "start_here": 1234567890123456789,   # REPLACE WITH YOUR CHANNEL ID
    "live_stats": 1234567890123456790,

    # --- CONNECTION ---
    "daily_question": 1234567890123456791, # REPLACE WITH YOUR CHANNEL ID
    "moments": 1234567890123456792,
    "audio_capsule": 1234567890123456793,

    # --- UTILITY ---
    "bounty_board": 1234567890123456794,  # REPLACE WITH YOUR CHANNEL ID
    "dua_requests": 1234567890123456795,
    "decision_room": 1234567890123456796,
    "wiki_of_us": 1234567890123456797,

    # --- ARCADE ---
    "truth_or_dare": 1234567890123456798,
    "shop": 1234567890123456799,
    "watch_party": 1234567890123456800,
    "digital_garden": 1234567890123456801,

    # --- BACKEND ---
    "debug_logs": 1234567890123456802,    # REPLACE WITH YOUR CHANNEL ID
    "database_backup": 1234567890123456803
}


PLAYERS = [
    {
        "id": 9876543210987654321,     # REPLACE WITH YOUR DISCORD USER ID
        "tz": "Asia/Kuala_Lumpur"      # GMT+8
    },
    {
        "id": 9876543210987654322,     # REPLACE WITH YOUR PARTNER'S DISCORD USER ID
        "tz": "Africa/Harare"          # GMT+2 
    }
]


# Shop items remain the same...
SHOP_ITEMS = {
    "1": {"name": "💆‍♂️ 10-Minute Massage", "cost": 50},
    "2": {"name": "🍕 I Pick Dinner", "cost": 80},
    "3": {"name": "🧹 Get Out of 1 Chore", "cost": 150},
    "4": {"name": "🎬 Movie Night Choice", "cost": 60},
    "5": {"name": "🤫 End an Argument (Veto Card)", "cost": 500}
}

# STATS CONFIGURATION
DATES = {
    "relationship_start": "2024-01-15", # REPLACE with your Anniversary (YYYY-MM-DD)
    "last_seen": "2024-12-20"           # REPLACE with last time you met (YYYY-MM-DD)
}