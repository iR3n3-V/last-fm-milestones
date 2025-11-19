#!/usr/bin/env python3
# milestone.py

import argparse
import os
import sys
import math
import time
import requests
from dotenv import load_dotenv

load_dotenv()

api_url = "http://ws.audioscrobbler.com/2.0/"
min_scrobble_threshold = 95

# ---------------------------
#  escape per markdown v2
# ---------------------------
def escape_md(text: str) -> str:
    """
    escape markdownv2 telegram senza toccare * e _ 
    così la formattazione continua a funzionare.
    """
    # lista ufficiale dei caratteri da escapare
    chars = r"[]()~`>#+-=|{}.!"
    escaped = ""
    for c in text:
        if c in chars:
            escaped += "\\" + c
        else:
            escaped += c
    return escaped

def get_api_key():
    key = os.getenv("LASTFM_API_KEY")
    if not key:
        print("❌ errore: variabile 'LASTFM_API_KEY' non trovata.")
        sys.exit(1)
    return key


def calculate_milestone(scrobble):
    try:
        s = int(scrobble)
    except (valueError, typeError):
        return None

    if s < 95:
        return None

    result = None

    if 95 <= s < 100:
        mancanti = 100 - s
        if mancanti <= 5:
            result = {"milestone": 100, "mancanti": mancanti, "tipo": "h"}

    elif s >= 100:
        prossima_centinaia = math.ceil(s / 100) * 100
        mancanti = prossima_centinaia - s
        if 0 < mancanti <= 20:
            result = {"milestone": prossima_centinaia, "mancanti": mancanti, "tipo": "h"}

        if s >= 1000:
            prossima_migliaia = math.ceil(s / 1000) * 1000
            mancanti_k = prossima_migliaia - s
            if 0 < mancanti_k <= 100:
                result = {"milestone": prossima_migliaia, "mancanti": mancanti_k, "tipo": "k"}

    return result


def fetch_lastfm_data(entity_type, username, api_key):
    method_map = {
        "art": "user.gettopartists",
        "alb": "user.gettopalbums",
        "trk": "user.gettoptracks",
    }
    response_key_map = {
        "art": ("topartists", "artist"),
        "alb": ("topalbums", "album"),
        "trk": ("toptracks", "track"),
    }

    method = method_map[entity_type]
    root_key, list_key = response_key_map[entity_type]

    all_items = []
    page = 1
    limit = 200
    keep_fetching = True

    while keep_fetching:
        params = {
            "method": method,
            "user": username,
            "api_key": api_key,
            "format": "json",
            "limit": limit,
            "page": page,
        }

        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ errore di connessione alla pagina {page}: {e}")
            break

        try:
            items = data[root_key][list_key]
        except (keyError, typeError):
            break

        if not items:
            break

        try:
            last_item_playcount = int(items[-1].get("playcount", 0))
        except (indexError, keyError, valueError):
            last_item_playcount = 0

        all_items.extend(items)

        if last_item_playcount < min_scrobble_threshold:
            keep_fetching = False
        else:
            page += 1
            time.sleep(0.2)

    return all_items


def process_and_display(items, entity_type, count):
    milestone_groups = {}

    for item in items:
        try:
            playcount = int(item.get("playcount", 0))
        except (valueError, typeError):
            continue

        m_info = calculate_milestone(playcount)
        if not m_info:
            continue

        if count is not None:
            try:
                if m_info["milestone"] != int(count):
                    continue
            except valueError:
                pass

        item["m_info"] = m_info
        target = m_info["milestone"]
        milestone_groups.setdefault(target, []).append(item)

    if not milestone_groups:
        print("\n❌ nessun risultato trovato che rispetti i criteri selezionati.")
        return

    sorted_targets = sorted(milestone_groups.keys(), reverse=True)
    type_labels = {"art": "artisti", "alb": "album", "trk": "tracce"}

    for target in sorted_targets:
        group = milestone_groups[target]
        group.sort(key=lambda x: x["m_info"]["mancanti"])
        m_type = group[0]["m_info"]["tipo"]

        header = f"🏁 milestone: *{target}* scrobble ({type_labels.get(entity_type)})"
        print(escape_md(header) + "\n")

        for item in group:
            plays = item.get("playcount")
            left = item["m_info"]["mancanti"]

            if entity_type == "art":
                name = item.get("name", "n/a")

                line = (
                    f"🎤 *{name}*\n"
                    f"   *{plays}* _plays_\n"
                    f"   *{left}* _to milestone_\n"
                )
                print(escape_md(line) + "\n")

            elif entity_type == "alb":
                alb_name = item.get("name", "n/a")
                art_obj = item.get("artist", {})
                art_name = (
                    art_obj.get("name", art_obj) if isinstance(art_obj, dict) else str(art_obj)
                )

                line = (
                    f"💿 *{alb_name}* / *{art_name}*\n"
                    f"   *{plays}* plays\n"
                    f"   *{left}* to milestone\n"
                )
                print(escape_md(line) + "\n")

            elif entity_type == "trk":
                trk_name = item.get("name", "n/a")
                art_obj = item.get("artist", {})
                art_name = (
                    art_obj.get("name", art_obj) if isinstance(art_obj, dict) else str(art_obj)
                )

                line = (
                    f"🎵 *{trk_name}* / *{art_name}*\n"
                    f"   *{plays}* plays\n"
                    f"   *{left}* to milestone\n"
                )
                print(escape_md(line) + "\n")

    print("\n")


def main():
    parser = argparse.ArgumentParser(description="last.fm milestone tracker")
    parser.add_argument("entity", choices=["art", "alb", "trk"])
    parser.add_argument("count", nargs="?", default=None)
    parser.add_argument("username", nargs="?", default=None)
    args = parser.parse_args()

    api_key = get_api_key()
    username = args.username or os.getenv("LASTFM_USERNAME")

    if not username:
        print("❌ errore: username non specificato")
        sys.exit(1)

    data = fetch_lastfm_data(args.entity, username, api_key)
    if data:
        process_and_display(data, args.entity, args.count)


if __name__ == "__main__":
    main()
