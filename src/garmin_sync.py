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
    
    g = Garmin(email, password)
    
    try:
        g.client = pickle.loads(base64.b64decode(session_data))
        g.display_name = "markus"
        print(f"Session geladen")
    except Exception as e:
        print(f"Session Fehler, versuche normalen Login: {e}")
        g.login()
    
    db = get_client()
    today = date.today()
    week_ago = today - timedelta(days=30)
    
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
            "duration_sec": int(act.get("duration", 0) or 0),
            "distance_m": float(act.get("distance", 0) or 0),
            "avg_hr": int(act.get("averageHR", 0) or 0) or None,
            "max_hr": int(act.get("maxHR", 0) or 0) or None,
            "tss_estimate": float(act.get("trainingStressScore", 0) or 0) or None,
            "raw": json.dumps(act)
        }
        upsert_activity(db, activity)
        print(f"✅ Gespeichert: {sport} am {act.get('startTimeLocal')}")
    
    try:
        print("Hole Sleep...")
        sleep = g.get_sleep_data(today.isoformat())
        print(f"Sleep OK")
    except Exception as e:
        print(f"Sleep Fehler: {e}")
        sleep = None

    try:
        print("Hole HRV...")
        hrv = g.get_hrv_data(today.isoformat())
        print(f"HRV OK")
    except Exception as e:
        print(f"HRV Fehler: {e}")
        hrv = None

    try:
        print("Hole Body Battery...")
        body_battery = g.get_body_battery(today.isoformat(), today.isoformat())
        print(f"Body Battery OK")
    except Exception as e:
        print(f"Body Battery Fehler: {e}")
        body_battery = None

    try:
        print("Hole SpO2...")
        spo2 = g.get_spo2_data(today.isoformat())
        print(f"SpO2 OK")
    except Exception as e:
        print(f"SpO2 Fehler: {e}")
        spo2 = None

    # SpO2 Stunden unter 90% berechnen
    spo2_hours_below_90 = None
    if spo2 and spo2.get("spO2HourlyAverages"):
        below = sum(1 for reading in spo2["spO2HourlyAverages"] if reading[1] < 90)
        spo2_hours_below_90 = round(below * 0.5, 1)  # jeder Eintrag = 30min

    try:
        metrics = {
            "date": today.isoformat(),
            "hrv_ms": hrv.get("hrvSummary", {}).get("lastNightAvg") if hrv else None,
            "body_battery": body_battery[0].get("charged") if body_battery else None,
            "resting_hr": None,
            "sleep_sec": sleep.get("dailySleepDTO", {}).get("sleepTimeSeconds") if sleep else None,
            "sleep_score": sleep.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value") if sleep else None,
            "spo2_avg": spo2.get("averageSpO2") if spo2 else None,
            "spo2_sleep": spo2.get("avgSleepSpO2") if spo2 else None,
            "spo2_lowest": spo2.get("lowestSpO2") if spo2 else None,
            "spo2_hours_below_90": spo2_hours_below_90
        }
        upsert_daily_metrics(db, metrics)
        print("✅ Metriken gespeichert")
    except Exception as e:
        print(f"Metriken Fehler: {e}")

    print(f"✅ Garmin sync abgeschlossen: {len(activities)} Aktivitäten")

if __name__ == "__main__":
    sync_garmin()
