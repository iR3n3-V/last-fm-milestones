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

API_URL = "http://ws.audioscrobbler.com/2.0/"
MIN_SCROBBLE_THRESHOLD = 95

def get_api_key():
    key = os.getenv("LASTFM_API_KEY")
    if not key:
        print("❌ errore: variabile 'LASTFM_API_KEY' non trovata.")
        sys.exit(1)
    return key

def calculate_milestone(scrobble):
    try:
        S = int(scrobble)
    except (ValueError, TypeError):
        return None

    if S < 95:
        return None

    result = None

    if 95 <= S < 100:
        mancanti = 100 - S
        if mancanti <= 5:
            result = {"milestone": 100, "mancanti": mancanti, "tipo": "h"}
    elif S >= 100:
        prossima_centinaia = math.ceil(S / 100) * 100
        mancanti = prossima_centinaia - S
        if 0 < mancanti <= 20:
            result = {"milestone": prossima_centinaia, "mancanti": mancanti, "tipo": "h"}
        if S >= 1000:
            prossima_migliaia = math.ceil(S / 1000) * 1000
            mancanti_k = prossima_migliaia - S
            if 0 < mancanti_k <= 100:
                result = {"milestone": prossima_migliaia, "mancanti": mancanti_k, "tipo": "k"}
    return result

def fetch_lastfm_data(entity_type, username, api_key):
    method_map = {
        "art": "user.gettopartists",
        "alb": "user.gettopalbums",
        "trk": "user.gettoptracks"
    }
    response_key_map = {
        "art": ("topartists", "artist"),
        "alb": ("topalbums", "album"),
        "trk": ("toptracks", "track")
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
            "page": page
        }
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ errore di connessione alla pagina {page}: {e}")
            break

        try:
            items = data[root_key][list_key]
        except (KeyError, TypeError):
            break

        if not items:
            break

        try:
            last_item_playcount = int(items[-1].get("playcount", 0))
        except:
            last_item_playcount = 0

        all_items.extend(items)

        if last_item_playcount < MIN_SCROBBLE_THRESHOLD:
            keep_fetching = False
        else:
            page += 1
            time.sleep(0.2)

    return all_items

def esc_md2(text: str) -> str:
    """Escape caratteri speciali per MarkdownV2"""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(f"\\{c}" if c in escape_chars else c for c in text)

def process_and_display(items, entity_type, count):
    milestone_groups = {}

    for item in items:
        try:
            playcount = int(item.get("playcount", 0))
        except:
            continue

        m_info = calculate_milestone(playcount)
        if not m_info:
            continue

        if count is not None:
            try:
                if m_info["milestone"] != int(count):
                    continue
            except:
                pass

        item["m_info"] = m_info
        target = m_info["milestone"]
        milestone_groups.setdefault(target, []).append(item)

    if not milestone_groups:
        print("❌ nessun risultato trovato che rispetti i criteri selezionati.")
        return

    sorted_targets = sorted(milestone_groups.keys(), reverse=True)
    type_labels = {"art": "artisti", "alb": "album", "trk": "tracce"}

    for target in sorted_targets:
        group = milestone_groups[target]
        group.sort(key=lambda x: x["m_info"]["mancanti"])

        print(f"🏁  *Milestone: {target}* scrobble \\(_{type_labels.get(entity_type)}_\\) \n")

        for item in group:
            plays = item.get("playcount")
            left = item["m_info"]["mancanti"]
            url = item.get("url", "")

            if entity_type == "art":
                name = esc_md2(item.get("name", "n/a"))
                url = esc_md2(url)
                clickable = f"[{name}]({url})" if url else name
                print(f"\\> 🎤  *{clickable}*\n\\>             *{plays}* _plays_\n\\>             *{left}* _to milestone_ \n")
            elif entity_type == "alb":
                alb_name = esc_md2(item.get("name", "n/a"))
                art_obj = item.get("artist", {})
                art_name = esc_md2(art_obj.get("name", "n/a") if isinstance(art_obj, dict) else str(art_obj))
                clickable = f"[{alb_name} — {art_name}]({url})" if url else f"{alb_name} — {art_name}"
                print(f"> 💿 {clickable}\n> {plays} plays\n> {left} to milestone\n")
            elif entity_type == "trk":
                trk_name = esc_md2(item.get("name", "n/a"))
                art_obj = item.get("artist", {})
                art_name = esc_md2(art_obj.get("name", "n/a") if isinstance(art_obj, dict) else str(art_obj))
                clickable = f"[{trk_name} — {art_name}]({url})" if url else f"{trk_name} — {art_name}"
                print(f"> 🎵 {clickable}\n> {plays} plays\n> {left} to milestone\n")


def main():
    parser = argparse.ArgumentParser(description="last.fm milestone tracker")
    parser.add_argument("entity", choices=["art", "alb", "trk"])
    parser.add_argument("count", nargs="?", default=None, help="milestone numerica (es: 100, 1000)")
    parser.add_argument("username", nargs="?", default=None, help="username last.fm (cadere su .env se assente)")
    args = parser.parse_args()

    api_key = get_api_key()
    username = args.username or os.getenv("LASTFM_USERNAME")
    if not username:
        print("❌ errore: username non specificato. imposta LASTFM_USERNAME nel .env o passalo come arg.")
        sys.exit(1)

    data = fetch_lastfm_data(args.entity, username, api_key)
    if data:
        process_and_display(data, args.entity, args.count)

if __name__ == "__main__":
    main()
