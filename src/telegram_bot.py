import os
import asyncio
from datetime import date, timedelta
from telegram import Bot
from db import get_client, get_week_activities

def score_emoji(value, thresholds, emojis):
    for threshold, emoji in zip(thresholds, emojis):
        if value >= threshold:
            return emoji
    return emojis[-1]

async def send_daily_report():
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    db = get_client()
    
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    
    # Aktivitäten dieser Woche
    activities = get_week_activities(db, week_start.isoformat())
    
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
    
    race_day = date(2026, 7, 12)
    days_left = (race_day - today).days
    
    # Tägliche Metriken
    metrics_result = db.table("daily_metrics").select("*").eq("date", today.isoformat()).execute().data
    m = metrics_result[0] if metrics_result else {}
    
    hrv = m.get("hrv_ms")
    bb  = m.get("body_battery")
    rhr = m.get("resting_hr")
    sleep_score = m.get("sleep_score")
    sleep_sec = m.get("sleep_sec")
    
    # Schlaf formatieren
    if sleep_sec:
        sh, sm = divmod(sleep_sec // 60, 60)
        sleep_str = f"{sh}h {sm:02d}min"
    else:
        sleep_str = "–"
    
    # Bewertungen
    def hrv_rating(v):
        if not v: return "–", "keine Daten"
        if v >= 70: return "🟢", "Sehr gut – bereit für intensive Einheit"
        if v >= 50: return "🟡", "Gut – moderate Belastung empfohlen"
        if v >= 35: return "🟠", "Mäßig – lockeres Training oder Pause"
        return "🔴", "Niedrig – Erholung priorisieren"
    
    def bb_rating(v):
        if not v: return "–", "keine Daten"
        if v >= 75: return "🟢", "Hoch – volle Leistung möglich"
        if v >= 50: return "🟡", "Mittel – solides Training möglich"
        if v >= 25: return "🟠", "Niedrig – leichtes Training"
        return "🔴", "Sehr niedrig – Ruhetag empfohlen"
    
    def sleep_rating(v):
        if not v: return "–", "keine Daten"
        if v >= 80: return "🟢", "Ausgezeichnet"
        if v >= 60: return "🟡", "Gut"
        if v >= 40: return "🟠", "Mäßig"
        return "🔴", "Schlecht – mehr Schlaf einplanen"
    
    def rhr_rating(v):
        if not v: return "–", "keine Daten"
        if v <= 45: return "🟢", "Sehr niedrig – exzellente Form"
        if v <= 55: return "🟡", "Normal"
        if v <= 65: return "🟠", "Leicht erhöht – auf Übertraining achten"
        return "🔴", "Erhöht – Erholung prüfen"
    
    hrv_icon, hrv_text = hrv_rating(hrv)
    bb_icon, bb_text = bb_rating(bb)
    sleep_icon, sleep_text = sleep_rating(sleep_score)
    rhr_icon, rhr_text = rhr_rating(rhr)

    msg = f"""🌅 *Morgenreport – {today.strftime("%d. %B %Y")}*

*💤 Erholung & Bereitschaft*
{sleep_icon} Schlaf: {sleep_str} | Score: {sleep_score or "–"} – _{sleep_text}_
{hrv_icon} HRV: {f"{hrv:.0f}ms" if hrv else "–"} – _{hrv_text}_
{bb_icon} Body Battery: {bb or "–"} – _{bb_text}_
{rhr_icon} Resting HR: {rhr or "–"}bpm – _{rhr_text}_

*🏊🚴🏃 Woche bisher*
🏊 Swim – {fmt_distance(swim)} | {fmt_duration(swim)}
🚴 Bike – {fmt_distance(bike, 'km')} | {fmt_duration(bike)}
🏃 Run  – {fmt_distance(run, 'km')} | {fmt_duration(run)} | Ø {fmt_hr(run)}

📅 Gesamt: {total_h}h {total_m:02d}min | TSS: {total_tss:.0f}

*🎯 Sprint Triathlon 12. Juli*
Noch {days_left} Tage | Ziel: sub 1:30h"""

    await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    print("✅ Morgenreport gesendet")

if __name__ == "__main__":
    asyncio.run(send_daily_report())
