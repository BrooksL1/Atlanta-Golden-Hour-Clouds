import requests, datetime as dt, uuid, os

# ---- Settings ----
# Atlanta
LAT, LON = 33.749, -84.388
FORECAST_DAYS = 5
TZNAME = "America/New_York"

OM_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&hourly=cloud_cover_low,cloud_cover_mid,cloud_cover_high"
    "&daily=sunrise,sunset"
    f"&forecast_days={FORECAST_DAYS}"
    f"&timezone={TZNAME.replace('/', '%2F')}"
)

def ics_dt(t: dt.datetime) -> str:
    # Times from Open-Meteo are local (no 'Z'); format as local with tzid line
    return t.strftime("%Y%m%dT%H%M%S")

def vevent(summary: str, start_dt: dt.datetime, end_dt: dt.datetime, uid_suffix: str) -> str:
    uid = f"{uid_suffix}@atl-solar"
    return (
        "BEGIN:VEVENT\n"
        f"UID:{uid}\n"
        f"DTSTAMP:{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n"
        f"DTSTART;TZID={TZNAME}:{ics_dt(start_dt)}\n"
        f"DTEND;TZID={TZNAME}:{ics_dt(end_dt)}\n"
        f"SUMMARY:{summary}\n"
        "END:VEVENT\n"
    )

def nearest_index(times, target):
    # times and target are naive local datetimes
    return min(range(len(times)), key=lambda i: abs(times[i] - target))

def main():
    r = requests.get(OM_URL, timeout=20)
    r.raise_for_status()
    data = r.json()

    # Parse hourly timeline (local times)
    hourly_times = [dt.datetime.fromisoformat(t) for t in data["hourly"]["time"]]
    h_low  = data["hourly"]["cloud_cover_low"]
    h_mid  = data["hourly"]["cloud_cover_mid"]
    h_high = data["hourly"]["cloud_cover_high"]

    # Parse daily sunrise/sunset (local times)
    sunrises = [dt.datetime.fromisoformat(t) for t in data["daily"]["sunrise"]]
    sunsets  = [dt.datetime.fromisoformat(t) for t in data["daily"]["sunset"]]

    ics = []
    ics.append("BEGIN:VCALENDAR\n")
    ics.append("PRODID:-//Atlanta Golden Hour Clouds//EN\n")
    ics.append("VERSION:2.0\nCALSCALE:GREGORIAN\nMETHOD:PUBLISH\n")
    ics.append("X-WR-CALNAME:Atlanta — Sunrise/Sunset Cloud Layers\n")
    ics.append(f"X-WR-TIMEZONE:{TZNAME}\n")

    # For each day, create two events: Sunrise and Sunset
    for i in range(min(len(sunrises), len(sunsets))):
        for label, t in (("Sunrise", sunrises[i]), ("Sunset", sunsets[i])):
            idx = nearest_index(hourly_times, t)
            low, mid, high = h_low[idx], h_mid[idx], h_high[idx]
            title = f"{label} — L/M/H clouds: {low}%/{mid}%/{high}%"
            start = t
            end   = t + dt.timedelta(minutes=5)  # 5-min marker; adjust if you prefer
            ics.append(vevent(title, start, end, f"{label}-{t.date()}-{uuid.uuid4().hex[:8]}"))

    ics.append("END:VCALENDAR\n")

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.ics", "w", encoding="utf-8") as f:
        f.write("".join(ics))

if __name__ == "__main__":
    main()
