import os
import json
import pickle
import base64
from datetime import date, timedelta
from garminconnect import Garmin
from db import get_client, upsert_activity, upsert_daily_metrics

def sync_garmin():
    email = os.environ["GARMIN_EMAIL"]
    password = os.environ["GARMIN_PASSWORD"]
    session_data = os.environ["GARMIN_SESSION"]
    
    # Garmin Objekt normal initialisieren
    g = Garmin(email, password)
    
    # Session Token laden um Login zu überspringen
    try:
        g.client = pickle.loads(base64.b64decode(session_data))
        g.display_name = g.get_full_name()
        print(f"Session geladen für: {g.display_name}")
    except Exception as e:
        print(f"Session Fehler, versuche normalen Login: {e}")
        g.login()
    
    db = get_client()
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # Aktivitäten sync
    try:
        activities = g.get_activities_by_date(
            week_ago.isoformat(), today.isoformat()
        )
        print(f"Gefunden: {len(activities)} Aktivitäten")
    except Exception as e:
        print(f"Aktivitäten Fehler: {e}")
        activities = []
    
    for act in activities:
        sport_type = act.get("activityType", {}).get("typeKey", "unknown")
        
        if "swim" in sport_type.lower():
            sport = "swim"
        elif "bike" in sport_type.lower() or "cycling" in sport_type.lower():
            sport = "bike"
        elif "run" in sport_type.lower():
            sport = "run"
        else:
            sport = sport_type
        
        activity = {
            "id": f"garmin_{act['activityId']}",
            "source": "garmin",
            "sport": sport,
            "started_at": act.get("startTimeLocal"),
            "duration_sec": int(act.get("duration", 0)),
            "distance_m": act.get("distance", 0),
            "avg_hr": act.get("averageHR"),
            "max_hr": act.get("maxHR"),
            "tss_estimate": act.get("trainingStressScore"),
            "raw": json.dumps(act)
        }
        upsert_activity(db, activity)
    
    # Tägliche Metriken sync
    try:
        hrv = g.get_hrv_data(today.isoformat())
        sleep = g.get_sleep_data(today.isoformat())
        body_battery = g.get_body_battery(today.isoformat(), today.isoformat())
        stats = g.get_stats(today.isoformat())
        
        metrics = {
            "date": today.isoformat(),
            "hrv_ms": hrv.get("lastNight", {}).get("avg") if hrv else None,
            "body_battery": body_battery[0].get("charged") if body_battery else None,
            "resting_hr": stats.get("restingHeartRate"),
            "sleep_sec": sleep.get("dailySleepDTO", {}).get("sleepTimeSeconds") if sleep else None,
            "sleep_score": sleep.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value") if sleep else None
        }
        upsert_daily_metrics(db, metrics)
        print("✅ Metriken gespeichert")
    except Exception as e:
        print(f"Metriken Fehler: {e}")
    
    print(f"✅ Garmin sync abgeschlossen: {len(activities)} Aktivitäten")

if __name__ == "__main__":
    sync_garmin()
