# =========================================
# CONFIGURATION FILE
# =========================================

# 1. Channel IDs (Replace with your actual Channel IDs)
CHANNELS = {
    "daily_question": 0,    # ID for daily questions
    "moments": 0,           # ID for photo challenges
    "audio_capsule": 0,     # ID for voice notes
    "truth_or_dare": 0,     # ID for games
    "bounty_board": 0,      # ID for task requests
    "decision_room": 0,     # ID for polls/AI help
    "shop": 0,              # ID for the store
    "live_stats": 0,        # ID for the dashboard
    "debug_logs": 0,        # Private channel for backups
    "database_backup": 0,   # Private channel for DB dumps
    "start_here": 0,        # ID for the manual/menu
    "watch_party": 0        # ID for movie sync
}

# 2. Player Timezones (Replace IDs with User IDs)
PLAYERS = [
    {"id": 0, "tz": "Asia/Kuala_Lumpur", "name": "Partner A"},
    {"id": 0, "tz": "Africa/Lusaka", "name": "Partner B"}
]

# 3. Important Dates
DATES = {
    "relationship_start": "2024-01-01", 
    "last_seen": "2024-01-01"
}

# 4. Shop Items (Economy)
SHOP_ITEMS = {
    "1": {"name": "Massage Coupon (30m)", "cost": 150},
    "2": {"name": "Movie Night Choice", "cost": 300},
    "3": {"name": "No Chores Day", "cost": 500},
    "4": {"name": "Forgiveness Card", "cost": 1000},
}