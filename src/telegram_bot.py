import os
from datetime import date, timedelta, datetime
from telegram import Bot
from db import get_client, get_week_activities

async def send_daily_report():
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    db = get_client()
    
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    # Aktivitäten dieser Woche
    activities = get_week_activities(db, week_start.isoformat())
    
    # Nach Sport aufteilen
    swim = [a for a in activities if a["sport"] == "swim"]
    bike = [a for a in activities if a["sport"] == "bike"]
    run  = [a for a in activities if a["sport"] == "run"]
    
    def fmt_distance(acts, unit="m"):
        total = sum(a.get("distance_m", 0) or 0 for a in acts)
        if unit == "km":
            return f"{total/1000:.1f}km"
        return f"{total:.0f}m"
    
    def fmt_duration(acts):
        total = sum(a.get("duration_sec", 0) or 0 for a in acts)
        h, m = divmod(total // 60, 60)
        return f"{h}h {m:02d}min" if h else f"{m}min"
    
    def fmt_hr(acts):
        hrs = [a.get("avg_hr") for a in acts if a.get("avg_hr")]
        return f"{sum(hrs)//len(hrs)}bpm" if hrs else "–"
    
    total_tss = sum(a.get("tss_estimate", 0) or 0 for a in activities)
    total_sec = sum(a.get("duration_sec", 0) or 0 for a in activities)
    total_h, total_m = divmod(total_sec // 60, 60)
    
    # Tage bis Rennen
    race_day = date(2026, 7, 12)
    days_left = (race_day - today).days
    
    # Tägliche Metriken
    metrics = db.table("daily_metrics")\
        .select("*")\
        .eq("date", today.isoformat())\
        .execute().data
    
    hrv = metrics[0].get("hrv_ms") if metrics else None
    bb  = metrics[0].get("body_battery") if metrics else None
    rhr = metrics[0].get("resting_hr") if metrics else None
    
    msg = f"""📊 *Triathlon Dashboard*
{today.strftime("%A, %d. %B %Y")}

🏊 Swim – {fmt_distance(swim)} | {fmt_duration(swim)}
🚴 Bike – {fmt_distance(bike, 'km')} | {fmt_duration(bike)}
🏃 Run  – {fmt_distance(run, 'km')} | {fmt_duration(run)} | Ø {fmt_hr(run)}

❤️ Resting HR: {rhr or '–'}bpm
💤 HRV: {f"{hrv:.0f}ms" if hrv else '–'} | Body Battery: {bb or '–'}

📅 Woche: {total_h}h {total_m:02d}min | TSS: {total_tss:.0f}
🎯 Sprint 12. Juli: noch {days_left} Tage | Ziel sub 1:30h"""

    await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    print("✅ Telegram Report gesendet")

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_daily_report())
