RADIO_LINES = {
    "infantry": {
        "select": {
            "give_work": "mykyta",
            "short_intro": "dmytro",
            "ready_attitude": "oleksa",
            "no_questions": "mykyta",
            "give_direction": "dmytro",
            "not_a_stroll": "oleksa",
            "serious_work": "mykyta",
        },
        "move": {
            "quiet_advance": "dmytro",
            "try_stopping_us": "oleksa",
            "not_getting_lost": "mykyta",
            "legs_working": "dmytro",
            "their_surprise": "oleksa",
            "coffee_later": "mykyta",
            "no_empty_promises": "dmytro",
        },
        "stop": {"no_extra_moves": "oleksa", "hold_position": "mykyta", "stay_sharp": "dmytro"},
    },
    "group": {
        "select": {
            "getting_crowded": "dmytro",
            "proper_work": "oleksa",
            "no_wasted_moves": "mykyta",
            "all_with_attitude": "dmytro",
            "enemy_can_keep_chaos": "oleksa",
            "many_but_quiet": "mykyta",
            "your_move": "dmytro",
        },
        "move": {
            "keep_formation": "oleksa",
            "together": "mykyta",
            "no_heroics": "dmytro",
            "making_progress": "oleksa",
            "no_bus": "mykyta",
            "nobody_lags": "dmytro",
            "get_used_to_it": "oleksa",
        },
        "stop": {"hold_formation": "mykyta", "watch_sectors": "dmytro", "not_a_break": "oleksa"},
    },
    "tank": {
        "select": {
            "find_a_road": "oleksa",
            "no_gentleness": "mykyta",
            "heavy_arguments": "dmytro",
            "tight_but_armored": "oleksa",
            "where_weight_matters": "mykyta",
            "no_fuss": "dmytro",
            "clear_orders": "oleksa",
        },
        "move": {
            "tracks_working": "mykyta",
            "fragile_step_aside": "dmytro",
            "hard_for_them": "oleksa",
            "asphalt_will_survive": "mykyta",
            "engine_will_speak": "dmytro",
            "driving": "oleksa",
            "no_indicators": "mykyta",
        },
        "stop": {"turret_working": "dmytro", "armor_holds": "oleksa", "engine_grumbles": "mykyta"},
    },
}

RADIO_LINES["patriot"] = {
    "select": {"sky_watch": "mykyta", "bad_ideas": "dmytro"},
    "move": {"quiet_relocation": "oleksa"},
    "stop": {"unwelcome_guests": "mykyta"},
}


def radio_category(units):
    if units and all(unit.is_patriot for unit in units):
        return "patriot"
    if len(units) > 1:
        return "group"
    if units:
        return "tank" if units[0].is_tank else "infantry"
    return None
