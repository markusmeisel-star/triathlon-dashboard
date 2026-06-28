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
        g.display_name = g.get_full_name()
        print(f"Session geladen für: {g.display_name}")
    except Exception as e:
        print(f"Session Fehler, versuche normalen Login: {e}")
        g.login()
