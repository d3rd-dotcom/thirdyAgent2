"""
skills_free_science.py — Science & Math skill pack for thirdyAgent2
5 skills: space_explorer, math_solver, earth_watch, astronomy_feed, science_facts
All free, zero API keys needed.
"""
import requests
import urllib.parse
import datetime


def handle_space_explorer(params):
    """
    Real-time space data: ISS position + crew + upcoming launches
    APIs: open-notify.org (no key) + thespacedevs.com (no key)
    """
    data = {}

    # ISS current position
    try:
        iss = requests.get("http://api.open-notify.org/iss-now.json", timeout=5).json()
        data["lat"] = iss.get("iss_position", {}).get("latitude", "?")
        data["lon"] = iss.get("iss_position", {}).get("longitude", "?")
    except: pass

    # People currently in space
    try:
        astros = requests.get("http://api.open-notify.org/astros.json", timeout=5).json()
        data["people_count"] = astros.get("number", "?")
        data["crew"] = [p["name"] for p in astros.get("people", [])[:4]]
    except: pass

    # Next upcoming launch
    try:
        r = requests.get(
            "https://lldev.thespacedevs.com/2.2.0/launch/upcoming/?limit=2&format=json",
            timeout=6
        ).json()
        launches = r.get("results", [])
        if launches:
            l = launches[0]
            data["next_launch"]     = l.get("name", "?")
            data["next_launch_net"] = l.get("net", "?")[:10]
            data["rocket"]         = l.get("rocket", {}).get("configuration", {}).get("name", "?")
    except: pass

    crew_str = ", ".join(data.get("crew", [])) or "N/A"

    return {
        "result": (
            f"🚀 [SPACE EXPLORER]\n"
            f"🛸 ISS Location  : Lat {data.get('lat','?')}, Lon {data.get('lon','?')}\n"
            f"👨‍🚀 People in Space: {data.get('people_count','?')}\n"
            f"🧑‍✈️ Crew          : {crew_str}\n"
            f"🚀 Next Launch   : {data.get('next_launch','?')}\n"
            f"📅 Launch Date   : {data.get('next_launch_net','?')}\n"
            f"🔭 Rocket        : {data.get('rocket','?')}"
        ),
        "data": data
    }


def handle_math_solver(params):
    """
    Solve math expressions: simplify, factor, derive, integrate, zeroes
    API: newton.vercel.app (no key)
    """
    operation  = params.get("operation", "simplify")
    expression = params.get("expression", "x^2+2x")

    valid_ops = [
        "simplify", "factor", "derive", "integrate", "zeroes",
        "tangent", "area", "cos", "sin", "tan",
        "arccos", "arcsin", "arctan", "abs", "log"
    ]

    if operation not in valid_ops:
        return {
            "result": (
                f"❌ Unknown operation: '{operation}'\n"
                f"✅ Valid operations: {', '.join(valid_ops)}\n"
                f"Example: operation=derive, expression=x^3+2x"
            ),
            "data": {}
        }

    try:
        encoded = urllib.parse.quote(str(expression))
        r = requests.get(
            f"https://newton.vercel.app/api/v2/{operation}/{encoded}",
            timeout=8
        ).json()
        result = r.get("result", "No result")
        expr   = r.get("expression", expression)
        return {
            "result": (
                f"🔢 [MATH SOLVER]\n"
                f"Operation  : {operation}\n"
                f"Expression : {expr}\n"
                f"Result     : {result}"
            ),
            "data": r
        }
    except Exception as e:
        return {"result": f"Math error: {e}", "data": {}}


def handle_earth_watch(params):
    """
    Real-time earth data: significant earthquakes this week + air quality
    APIs: USGS Earthquake (no key) + Open-Meteo air quality (no key)
    """
    city = params.get("city", "Manila")
    data = {}

    # Significant earthquakes this week
    try:
        eq = requests.get(
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson",
            timeout=6
        ).json()
        quakes = eq.get("features", [])[:5]
        data["earthquakes"] = [
            {
                "place": q["properties"].get("place", "?"),
                "mag":   q["properties"].get("mag", "?"),
            }
            for q in quakes
        ]
        data["total_quakes"] = eq.get("metadata", {}).get("count", len(quakes))
    except: pass

    # Air quality for city
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "format": "json"},
            timeout=5
        ).json()
        if geo.get("results"):
            loc = geo["results"][0]
            aq = requests.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={
                    "latitude":  loc["latitude"],
                    "longitude": loc["longitude"],
                    "current":   "pm2_5,pm10,carbon_monoxide,ozone,european_aqi"
                },
                timeout=5
            ).json().get("current", {})
            data["city"]    = loc["name"]
            data["aqi"]     = aq.get("european_aqi", "?")
            data["pm25"]    = aq.get("pm2_5", "?")
            data["ozone"]   = aq.get("ozone", "?")
    except: pass

    if data.get("earthquakes"):
        eq_lines = "\n".join([f"• M{q['mag']} — {q['place']}" for q in data["earthquakes"]])
    else:
        eq_lines = "No significant earthquakes this week ✅"

    aqi_val = data.get("aqi", "?")
    aqi_label = (
        "Good 🟢" if isinstance(aqi_val, (int,float)) and aqi_val < 50
        else "Moderate 🟡" if isinstance(aqi_val, (int,float)) and aqi_val < 100
        else "Unhealthy 🔴" if isinstance(aqi_val, (int,float))
        else "?"
    )

    return {
        "result": (
            f"🌍 [EARTH WATCH]\n"
            f"📍 Air Quality ({data.get('city', city)}): AQI={aqi_val} ({aqi_label}) | "
            f"PM2.5={data.get('pm25','?')} | Ozone={data.get('ozone','?')}\n\n"
            f"🌋 Significant Earthquakes This Week ({data.get('total_quakes',0)}):\n"
            f"{eq_lines}"
        ),
        "data": data
    }


def handle_astronomy_feed(params):
    """
    Astronomy data: sunrise/sunset for any location + moon phase
    APIs: sunrise-sunset.org (no key) + open-meteo (no key)
    """
    lat  = params.get("lat", "14.5995")
    lng  = params.get("lng", "120.9842")
    city = params.get("city", "Manila")
    data = {}

    # Geocode city if provided
    if city and city != "Manila":
        try:
            geo = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "format": "json"},
                timeout=5
            ).json()
            if geo.get("results"):
                loc = geo["results"][0]
                lat = loc["latitude"]
                lng = loc["longitude"]
                data["city"] = loc["name"]
        except: pass

    # Sunrise/Sunset
    try:
        sun = requests.get(
            "https://api.sunrise-sunset.org/json",
            params={"lat": lat, "lng": lng, "formatted": 0},
            timeout=5
        ).json()
        r = sun.get("results", {})
        data["sunrise"]    = r.get("sunrise", "?")[:19] if r.get("sunrise") else "?"
        data["sunset"]     = r.get("sunset", "?")[:19] if r.get("sunset") else "?"
        data["solar_noon"] = r.get("solar_noon", "?")[:19] if r.get("solar_noon") else "?"
        data["day_length"] = r.get("day_length", "?")
    except: pass

    # Moon phase estimation
    now       = datetime.datetime.now()
    known_new = datetime.datetime(2000, 1, 6)
    cycle     = 29.53058867
    days_since = (now - known_new).days
    phase_day  = days_since % cycle
    if phase_day < 1:    moon = "🌑 New Moon"
    elif phase_day < 8:  moon = "🌒 Waxing Crescent"
    elif phase_day < 9:  moon = "🌓 First Quarter"
    elif phase_day < 15: moon = "🌔 Waxing Gibbous"
    elif phase_day < 16: moon = "🌕 Full Moon"
    elif phase_day < 23: moon = "🌖 Waning Gibbous"
    elif phase_day < 24: moon = "🌗 Last Quarter"
    else:                moon = "🌘 Waning Crescent"

    return {
        "result": (
            f"🌅 [ASTRONOMY FEED] — {data.get('city', city)} ({lat}, {lng})\n"
            f"🌄 Sunrise    : {data.get('sunrise','?')} UTC\n"
            f"🌞 Solar Noon : {data.get('solar_noon','?')} UTC\n"
            f"🌆 Sunset     : {data.get('sunset','?')} UTC\n"
            f"⏱️  Day Length  : {data.get('day_length','?')} seconds\n"
            f"🌙 Moon Phase : {moon}"
        ),
        "data": data
    }


def handle_science_facts(params):
    """
    Random science + number facts from multiple sources
    APIs: numbersapi.com (no key) + uselessfacts.jsph.pl (no key) + catfact.ninja (no key)
    """
    number = params.get("number", "42")
    mode   = params.get("mode", "all")
    data   = {}

    # Number fact
    try:
        fact = requests.get(
            f"http://numbersapi.com/{number}/math",
            timeout=5
        ).text
        data["number_fact"] = fact
    except: pass

    # Random interesting fact
    try:
        r = requests.get(
            "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en",
            timeout=5
        ).json()
        data["random_fact"] = r.get("text", "?")
    except: pass

    # Cat fact (agents love these!)
    try:
        r = requests.get("https://catfact.ninja/fact", timeout=5).json()
        data["cat_fact"] = r.get("fact", "?")
    except: pass

    # Advice slip
    try:
        r = requests.get("https://api.adviceslip.com/advice", timeout=5).json()
        data["advice"] = r.get("slip", {}).get("advice", "?")
    except: pass

    lines = [f"🔬 [SCIENCE FACTS]"]
    if data.get("number_fact"):
        lines.append(f"🔢 Number {number}: {data['number_fact']}")
    if data.get("random_fact"):
        lines.append(f"💡 Fun Fact: {data['random_fact']}")
    if data.get("cat_fact"):
        lines.append(f"🐱 Cat Fact: {data['cat_fact']}")
    if data.get("advice"):
        lines.append(f"💭 Advice: {data['advice']}")

    return {
        "result": "\n".join(lines),
        "data": data
    }


SKILLS_PACK = {
    "space_explorer":  handle_space_explorer,
    "math_solver":     handle_math_solver,
    "earth_watch":     handle_earth_watch,
    "astronomy_feed":  handle_astronomy_feed,
    "science_facts":   handle_science_facts,
}
