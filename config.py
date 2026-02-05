# config.py

CHANNELS = {
    # --- DASHBOARD ---
    "start_here": 1460010749924741162,   # KEEP YOUR EXISTING ID
    "live_stats": 1460010827653451928,

    # --- CONNECTION ---
    "daily_question": 1460011095040196721, # KEEP YOUR EXISTING ID
    "moments": 1460011160052039813,
    "audio_capsule": 1460011595475193937,

    # --- UTILITY ---
    "bounty_board": 1460011800085922036,  # <--- THIS IS OUR TARGET FOR TODAY
    "dua_requests": 1460013258546348297,
    "decision_room": 1460012745670791301,
    "wiki_of_us": 1460012804265214235,

    # --- ARCADE ---
    "truth_or_dare": 1460012898586853667,
    "shop": 1460013380298342483,
    "watch_party": 1460013326800130088,
    "digital_garden": 1460012974365212895,

    # --- BACKEND ---
    "debug_logs": 1460012057180110959,    # KEEP YOUR EXISTING ID
    "database_backup": 1460012158690791667
}


PLAYERS = [
    {
        "id": 831165682959253564,     # <--- PASTE YOUR ID HERE
        "tz": "Asia/Kuala_Lumpur"     # GMT+8
    },
    {
        "id": 1459986292086407252,     # <--- PASTE HER ID HERE
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
    "relationship_start": "2025-12-27", # REPLACE with your Anniversary (YYYY-MM-DD)
    "last_seen": "2025-12-15"           # REPLACE with last time you met (YYYY-MM-DD)
}