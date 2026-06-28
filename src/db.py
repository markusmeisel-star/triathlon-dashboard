import os
from supabase import create_client

def get_client():
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)

def upsert_activity(db, activity):
    db.table("activities").upsert(activity).execute()

def upsert_daily_metrics(db, metrics):
    db.table("daily_metrics").upsert(metrics).execute()

def get_week_activities(db, week_start):
    response = db.table("activities").select("*").gte("started_at", week_start).execute()
    return response.data
