# ==============================================================================
# 1. IMPORTS & CONFIGURATION
# ==============================================================================
import io
import os
from datetime import datetime

import folium
import mysql.connector
import pandas as pd
import requests
import streamlit as st
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from gtts import gTTS
from streamlit_folium import st_folium

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # <-- Enter your MySQL password here
    "database": "agri_analysis"
}

DATA_GOV_API_KEY = ""  # <-- Paste your data.gov.in API key here
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

SUMMARY_CSV_PATH = "farmer_mandi_summary.csv"
FORECAST_CSV_PATH = "farmer_day_by_day_forecast.csv"
FEEDBACK_CSV_PATH = "farmer_feedback.csv"

geolocator = Nominatim(user_agent="telangana_pincode_mandi_map_v5")


# ==============================================================================
# 2. LOCALIZATION TEXT & CONSTANTS (ENGLISH & TELUGU)
# ==============================================================================
UI_TEXT = {
    "English": {
        "title": "Telangana Smart Mandi Advisor",
        "subtitle": "Enter any Telangana village pincode and target mandi pincode to calculate exact map distance, weather risk, and 7-day profit.",
        "village_label": "Your Village / Mandal Name",
        "farmer_pin_label": "Your Village Pincode (Any 6-digit Telangana PIN)",
        "district_label": "Your District",
        "mandi_label": "Target Mandi Name",
        "mandi_pin_label": "Target Mandi Pincode (Optional, for exact map pin)",
        "crop_label": "Crop Name (e.g., Maize, Cotton, Tomato, Paddy)",
        "qty_label": "Quantity (Quintals)",
        "share_truck": "Share transport vehicle with neighbor (40% freight discount)",
        "calc_btn": "Calculate Map Distance & 7-Day Profit",
        "weather_risk": "Weather Alert: {rain} mm rain / {temp}°C expected in 7 days (Higher spoilage risk).",
        "weather_safe": "Weather Clear: Only {rain} mm rain forecast over next 7 days.",
        "dist_metric": "Map Road Distance",
        "today_metric": "Net Profit Today",
        "week_metric": "Net Profit in 7 Days",
        "map_header": "Live Map: Your Village Pincode to Target Mandi",
        "decision_header": "Final Recommendation",
        "voice_caption": "Listen to Advice (Audio):",
        "wait_7": "WAIT 7 DAYS",
        "sell_now": "SELL TODAY",
        "fb_header": "Ask Doubts & Suggest Improvements",
        "fb_sub": "Have a question about mandi prices or an idea to improve this app? Share it below!",
        "fb_type": "Select Topic",
        "fb_types": ["Doubt / Question", "Suggest an Improvement", "Report Price / Map Issue"],
        "fb_name": "Your Name / Village (Optional)",
        "fb_msg": "Write your doubt or improvement suggestion here...",
        "fb_btn": "Submit Feedback",
        "fb_warn": "Please enter your doubt or suggestion before submitting.",
        "fb_success": "Thank you! Your message has been saved and will help us improve."
    },
    "Telugu": {
        "title": "తెలంగాణ స్మార్ట్ మండి సలహాదారు",
        "subtitle": "ఏదైనా తెలంగాణ గ్రామం పిన్‌కోడ్ మరియు మండి పిన్‌కోడ్ నమోదు చేసి మ్యాప్ దూరం, వాతావరణం మరియు 7 రోజుల లాభం తెలుసుకోండి.",
        "village_label": "మీ గ్రామం / మండలం పేరు",
        "farmer_pin_label": "మీ గ్రామం పిన్‌కోడ్ (ఏదైనా 6 అంకెల తెలంగాణ పిన్)",
        "district_label": "మీ జిల్లా",
        "mandi_label": "మీరు అమ్మాలనుకుంటున్న మండి పేరు",
        "mandi_pin_label": "మండి పిన్‌కోడ్ (ఐచ్ఛికం - ఖచ్చితమైన మ్యాప్ కోసం)",
        "crop_label": "పంట పేరు (ఉదా: Maize, Cotton, Tomato, Paddy)",
        "qty_label": "పరిమాణం (క్వింటాళ్లలో)",
        "share_truck": "పక్క రైతుతో వాహనాన్ని పంచుకోండి (40% రవాణా ఖర్చు ఆదా)",
        "calc_btn": "మ్యాప్ దూరం & 7 రోజుల లాభం చూడండి",
        "weather_risk": "వాతావరణ హెచ్చరిక: వచ్చే 7 రోజుల్లో {rain} మి.మీ వర్షం / {temp}°C ఉష్ణోగ్రత ఉంది (పంట పాడయ్యే ప్రమాదం ఎక్కువ).",
        "weather_safe": "వాతావరణం అనుకూలంగా ఉంది: వచ్చే 7 రోజుల్లో {rain} మి.మీ మాత్రమే వర్షం సూచన.",
        "dist_metric": "మ్యాప్ రవాణా దూరం",
        "today_metric": "ఈరోజు నికర లాభం",
        "week_metric": "7 రోజుల తర్వాత నికర లాభం",
        "map_header": "లైవ్ మ్యాప్: మీ గ్రామం నుండి మండి వరకు",
        "decision_header": "తుది సిఫార్సు",
        "voice_caption": "సలహా వినండి (తెలుగు ఆడియో):",
        "wait_7": "7 రోజులు ఆగండి (WAIT 7 DAYS)",
        "sell_now": "ఈరోజే అమ్మండి (SELL TODAY)",
        "fb_header": "సందేహాలు అడగండి & సలహాలు ఇవ్వండి",
        "fb_sub": "మండి ధరలపై సందేహాలు ఉన్నాయా లేదా ఈ యాప్‌ను మెరుగుపరచడానికి సలహాలు ఉన్నాయా? క్రింద రాయండి!",
        "fb_type": "విషయాన్ని ఎంచుకోండి",
        "fb_types": ["సందేహం / ప్రశ్న (Doubt)", "కొత్త సలహా / మెరుగుదల (Improvement)", "ధర / మ్యాప్ సమస్య (Issue)"],
        "fb_name": "మీ పేరు / గ్రామం (ఐచ్ఛికం)",
        "fb_msg": "మీ సందేహం లేదా సలహాను ఇక్కడ రాయండి...",
        "fb_btn": "సందేశం పంపండి",
        "fb_warn": "దయచేసి పంపే ముందు మీ సందేహం లేదా సలహాను రాయండి.",
        "fb_success": "ధన్యవాదాలు! మీ సందేశం నమోదు చేయబడింది."
    }
}

TELANGANA_DISTRICTS = [
    "Peddapalli", "Karimnagar", "Warangal", "Hanamkonda", "Khammam", "Nizamabad",
    "Siddipet", "Nalgonda", "Suryapet", "Mahabubnagar", "Adilabad", "Mancherial",
    "Jagtial", "Rajanna Sircilla", "Kamareddy", "Sangareddy", "Medak", "Rangareddy",
    "Vikarabad", "Bhadradri Kothagudem", "Mahabubabad", "Jangaon", "Jayashankar Bhupalpally",
    "Mulugu", "Komaram Bheem Asifabad", "Nirmal", "Wanaparthy", "Nagarkurnool",
    "Jogulamba Gadwal", "Narayanpet", "Yadadri Bhuvanagiri", "Medchal-Malkajgiri", "Hyderabad"
]


# ==============================================================================
# 3. HELPER FUNCTIONS (GEOCODING, WEATHER, VOICE & DATA PIPELINE)

def geocode_by_pincode_or_place(place_name: str, pincode: str, district: str):
    queries = []
    clean_pin = pincode.strip()
    if clean_pin.isdigit() and len(clean_pin) == 6:
        queries.append(f"{clean_pin}, Telangana, India")
        queries.append(f"{clean_pin}, India")
    if place_name.strip():
        queries.append(f"{place_name.strip()}, {district}, Telangana, India")
        queries.append(f"{place_name.strip()}, Telangana, India")
    queries.append(f"{district}, Telangana, India")

    for q in queries:
        try:
            loc = geolocator.geocode(q, timeout=8)
            if loc:
                return (loc.latitude, loc.longitude)
        except Exception:
            continue
    return None


def speak_audio(text: str, lang_code: str = "te"):
    try:
        tts = gTTS(text=text, lang=lang_code)
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        st.audio(audio_bytes, format="audio/mp3")
    except Exception:
        pass


def get_weather_risk(lat: float, lon: float) -> dict:
    try:
        weather_url = "https:" + chr(47) + chr(47) + "://open-meteo.com" + chr(47) + "v1" + chr(47) + "forecast"
        r = requests.get(
            weather_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "precipitation_sum,temperature_2m_max",
                "timezone": "Asia/Kolkata"
            },
            timeout=8
        ).json()
        rain_mm = round(sum(r["daily"]["precipitation_sum"][:7]), 1)
        max_temp = max(r["daily"]["temperature_2m_max"][:7])
        return {
            "rain_mm": rain_mm,
            "max_temp": max_temp,
            "high_risk": rain_mm > 20.0 or max_temp > 40.0
        }
    except Exception:
        return {"rain_mm": 0.0, "max_temp": 32.0, "high_risk": False}


def fetch_and_store_mandi_price(crop_name: str, mandi_name: str, mandi_coords: tuple, crop_variety: str = "All Varieties"):

    clean_crop = crop_name.strip().title()
    clean_mandi = mandi_name.strip().title()

    live_price = None
    if DATA_GOV_API_KEY != "":
        try:
            api_url = "https:" + chr(47) + chr(47) + "api.data.gov.in" + chr(47) + "resource" + chr(47) + RESOURCE_ID
            resp = requests.get(
                api_url,
                params={
                    "api-key": DATA_GOV_API_KEY,
                    "format": "json",
                    "limit": 50,
                    "filters[state]": "Telangana",
                    "filters[commodity]": clean_crop
                },
                timeout=8
            ).json()
            for rec in resp.get("records", []):
                if clean_mandi.lower() in rec.get("market", "").lower():
                    live_price = float(rec["modal_price"])
                    break
        except Exception:
            pass

        # Pull latest real modal price from your 72,000-row historical CSV if API didn't return one
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telangana_full_multiyear_data.csv")
    if not live_price and os.path.exists(csv_path):
        try:
            multi_df = pd.read_csv(csv_path)
            multi_df.columns = [c.strip().lower() for c in multi_df.columns]

            # Use .str.contains() so "Paddy" matches "Paddy(Dhan)(Common)"
            crop_match = multi_df[multi_df["commodity"].astype(str).str.lower().str.contains(clean_crop.lower(), na=False, regex=False)].copy()
            if crop_variety != "All Varieties" and "variety" in crop_match.columns:
                var_match = crop_match[crop_match["variety"].astype(str).str.lower().str.contains(crop_variety.lower(), na=False, regex=False)]
                if not var_match.empty:
                    crop_match = var_match

            mandi_match = crop_match[crop_match["market"].astype(str).str.lower().str.contains(clean_mandi.lower(), na=False, regex=False)]
            target_df = mandi_match if not mandi_match.empty else crop_match

            if not target_df.empty:
                target_df["dt"] = pd.to_datetime(target_df["arrival_date"], dayfirst=True, errors="coerce")
                target_df["modal_price"] = pd.to_numeric(target_df["modal_price"], errors="coerce")
                target_df = target_df.dropna(subset=["modal_price"]).sort_values("dt", ascending=False)
                if not target_df.empty:
                    live_price = float(target_df["modal_price"].iloc[0])
        except Exception as e:
            st.warning(f"CSV Lookup Note: {e}")

    if not live_price:
        live_price = 2450.00

    history_df = pd.DataFrame()
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT CROP_ID FROM DIM_CROP WHERE LOWER(CROP_NAME) = LOWER(%s)", (clean_crop,))
        crop_row = cursor.fetchone()
        if crop_row:
            crop_id = crop_row[0]
        else:
            cursor.execute("INSERT INTO DIM_CROP (CROP_NAME, CROP_CATEGORY) VALUES (%s, %s)", (clean_crop, "General"))
            conn.commit()
            crop_id = cursor.lastrowid

        cursor.execute("SELECT MANDI_ID FROM DIM_MANDI WHERE LOWER(MANDI_NAME) = LOWER(%s)", (clean_mandi,))
        mandi_row = cursor.fetchone()
        if mandi_row:
            mandi_id = mandi_row[0]
        else:
            cursor.execute(
                "INSERT INTO DIM_MANDI (MANDI_NAME, LATITUDE, LONGITUDE) VALUES (%s, %s, %s)",
                (clean_mandi, mandi_coords[0], mandi_coords[1])
            )
            conn.commit()
            mandi_id = cursor.lastrowid

        today = datetime.now()
        date_id = int(today.strftime("%Y%m%d"))
        cursor.execute("""
            INSERT IGNORE INTO DIM_DATE (DATE_ID, FULL_DATE, DAY_NUMBER, DAY_NAME, MONTH_NUMBER, MONTH_NAME, QUARTER, YEAR, SEASON)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            date_id, today.strftime("%Y-%m-%d"), today.day, today.strftime("%A"),
            today.month, today.strftime("%B"), (today.month - 1) // 3 + 1, today.year, "Rabi"
        ))

        cursor.execute("""
            INSERT INTO FACT_MARKET_PRICES (CROP_ID, MANDI_ID, DATE_ID, MODAL_PRICE_PER_QUINTAL)
            VALUES (%s, %s, %s, %s)
        """, (crop_id, mandi_id, date_id, live_price))
        conn.commit()

        history_df = pd.read_sql("""
            SELECT d.FULL_DATE, f.MODAL_PRICE_PER_QUINTAL
            FROM FACT_MARKET_PRICES f
            JOIN DIM_DATE d ON f.DATE_ID = d.DATE_ID
            WHERE f.CROP_ID = %s AND f.MANDI_ID = %s
            ORDER BY d.FULL_DATE ASC
        """, conn, params=(crop_id, mandi_id))

        cursor.close()
        conn.close()
    except Exception:
        pass

    return live_price, history_df


def log_farmer_search_to_db_and_csv(summary_row: dict, daily_df: pd.DataFrame) -> bool:
    """Stores farmer query into MySQL and exports both summary & 8-day forecast CSVs for Power BI."""
    db_saved = False

    forecast_export = daily_df.copy()
    forecast_export.insert(0, "Check_Timestamp", summary_row["Check_Timestamp"])
    forecast_export.insert(1, "District", summary_row["District"])
    forecast_export.insert(2, "Farmer_Village", summary_row["Farmer_Village"])
    forecast_export.insert(3, "Target_Mandi", summary_row["Target_Mandi"])
    forecast_export.insert(4, "Crop_Name", summary_row["Crop_Name"])

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FARMER_PRICE_CHECKS (
                CHECK_ID INT AUTO_INCREMENT PRIMARY KEY,
                CHECK_TIMESTAMP DATETIME,
                FARMER_VILLAGE VARCHAR(100),
                FARMER_PINCODE VARCHAR(10),
                DISTRICT VARCHAR(100),
                TARGET_MANDI VARCHAR(100),
                MANDI_PINCODE VARCHAR(10),
                CROP_NAME VARCHAR(50),
                QUANTITY_QUINTALS DECIMAL(10,2),
                SHARED_TRUCK VARCHAR(10),
                ROAD_DISTANCE_KM DECIMAL(10,2),
                TRANSPORT_COST DECIMAL(10,2),
                TODAY_PRICE_PER_QTL DECIMAL(10,2),
                NET_PROFIT_TODAY DECIMAL(10,2),
                OPTIMAL_SELL_DAY VARCHAR(30),
                PEAK_NET_PROFIT DECIMAL(10,2),
                PROFIT_GAIN_VS_TODAY DECIMAL(10,2),
                RAIN_7D_MM DECIMAL(10,2),
                MAX_TEMP_C DECIMAL(10,2),
                WEATHER_RISK VARCHAR(20)
            )
        """)

        cursor.execute("""
            INSERT INTO FARMER_PRICE_CHECKS (
                CHECK_TIMESTAMP, FARMER_VILLAGE, FARMER_PINCODE, DISTRICT,
                TARGET_MANDI, MANDI_PINCODE, CROP_NAME, QUANTITY_QUINTALS,
                SHARED_TRUCK, ROAD_DISTANCE_KM, TRANSPORT_COST, TODAY_PRICE_PER_QTL,
                NET_PROFIT_TODAY, OPTIMAL_SELL_DAY, PEAK_NET_PROFIT,
                PROFIT_GAIN_VS_TODAY, RAIN_7D_MM, MAX_TEMP_C, WEATHER_RISK
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, tuple(summary_row.values()))
        conn.commit()

        db_summary_df = pd.read_sql("SELECT * FROM FARMER_PRICE_CHECKS", conn)
        db_summary_df.to_csv(SUMMARY_CSV_PATH, index=False)

        cursor.close()
        conn.close()
        db_saved = True
    except Exception:
        pd.DataFrame([summary_row]).to_csv(
            SUMMARY_CSV_PATH, mode="a", header=not os.path.exists(SUMMARY_CSV_PATH), index=False
        )

    forecast_export.to_csv(
        FORECAST_CSV_PATH, mode="a", header=not os.path.exists(FORECAST_CSV_PATH), index=False
    )
    return db_saved


def save_farmer_feedback(fb_type: str, user_name: str, message: str, language: str):
    """Stores farmer doubts & improvement suggestions into MySQL and CSV."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_name = user_name.strip() if user_name.strip() else "Anonymous"
    clean_msg = message.strip()

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FARMER_FEEDBACK (
                FEEDBACK_ID INT AUTO_INCREMENT PRIMARY KEY,
                SUBMITTED_AT DATETIME,
                FEEDBACK_TYPE VARCHAR(60),
                USER_NAME_VILLAGE VARCHAR(100),
                LANGUAGE VARCHAR(20),
                MESSAGE TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO FARMER_FEEDBACK (SUBMITTED_AT, FEEDBACK_TYPE, USER_NAME_VILLAGE, LANGUAGE, MESSAGE)
            VALUES (%s, %s, %s, %s, %s)
        """, (ts, fb_type, clean_name, language, clean_msg))
        conn.commit()

        df_fb = pd.read_sql("SELECT * FROM FARMER_FEEDBACK", conn)
        df_fb.to_csv(FEEDBACK_CSV_PATH, index=False)
        cursor.close()
        conn.close()
    except Exception:
        fb_row = pd.DataFrame([{
            "Submitted_At": ts,
            "Feedback_Type": fb_type,
            "User_Name_Village": clean_name,
            "Language": language,
            "Message": clean_msg
        }])
        fb_row.to_csv(
            FEEDBACK_CSV_PATH, mode="a", header=not os.path.exists(FEEDBACK_CSV_PATH), index=False
        )


# ==============================================================================
# 4. STREAMLIT UI & USER INPUT# ==============================================================================
# 4. STREAMLIT UI & USER INPUTS
# ==============================================================================
st.set_page_config(page_title="Telangana Smart Mandi Advisor", page_icon="🌾", layout="wide")

lang_choice = st.sidebar.radio("Language / భాష", ["English", "తెలుగు (Telugu)"])
lang_key = "Telugu" if "Telugu" in lang_choice else "English"
t = UI_TEXT[lang_key]

st.title(f"🌾 {t['title']}")
st.caption(t["subtitle"])

col1, col2 = st.columns(2)
with col1:
    farmer_village = st.text_input(t["village_label"], value="", placeholder="e.g., Kalva Srirampur / Siddipet / Nalgonda")
    farmer_pincode = st.text_input(t["farmer_pin_label"], value="", placeholder="e.g., 505153", max_chars=6)
    farmer_district = st.selectbox(t["district_label"], TELANGANA_DISTRICTS, index=0)

with col2:
    target_mandi = st.text_input(t["mandi_label"], value="", placeholder="e.g., Peddapalli / Warangal / Bowenpally")
    mandi_pincode = st.text_input(t["mandi_pin_label"], value="", placeholder="e.g., 505172", max_chars=6)
    crop_name = st.text_input(t["crop_label"], value="Paddy")

    # Dynamically pull all real varieties for the entered crop from your 72,000-row CSV
    variety_options = ["All Varieties", "Common", "Grade-A", "Fine", "Sona Masoori", "RNR-15048", "MTU-1010", "BPT-5204", "1001", "HMT"]
    if os.path.exists("telangana_full_multiyear_data.csv") and crop_name.strip():
        try:
            _vdf = pd.read_csv("telangana_full_multiyear_data.csv", usecols=["Commodity", "Variety"])
            _matched = _vdf[_vdf["Commodity"].str.lower().str.contains(crop_name.strip().lower(), na=False)]
            _real_vars = sorted(_matched["Variety"].dropna().astype(str).str.strip().unique().tolist())
            if _real_vars:
                variety_options = ["All Varieties"] + _real_vars
        except Exception:
            pass

    crop_variety = st.selectbox(
        "Crop Variety / Grade (Optional)" if lang_key == "English" else "పంట రకం / గ్రేడ్ (ఐచ్ఛికం)",
        variety_options
    )
    qty_quintals = st.number_input(t["qty_label"], min_value=1.0, value=20.0, step=1.0)

shared_truck = st.checkbox(t["share_truck"], value=True)


# ==============================================================================
# 5. PROFIT & DISTANCE CALCULATION ENGINE
# ==============================================================================
if st.button(f"{t['calc_btn']} 🚀"):
    if not farmer_pincode and not farmer_village:
        st.warning("Please enter your 6-digit village pincode or village name.")
    elif not target_mandi and not mandi_pincode:
        st.warning("Please enter the target mandi name or pincode.")
    else:
        with st.spinner("Locating pincodes on map & calculating Day 0 to Day 7 profit..."):
            farmer_coords = geocode_by_pincode_or_place(farmer_village, farmer_pincode, farmer_district)
            mandi_coords = geocode_by_pincode_or_place(target_mandi, mandi_pincode, farmer_district)

        if not farmer_coords or not mandi_coords:
            st.error("Could not locate one of the pincodes. Please verify the 6-digit Telangana pincode.")
        else:
            straight_km = geodesic(farmer_coords, mandi_coords).km
            road_km = round(straight_km * 1.25, 1)
            freight = (400 + road_km * 18) * (0.60 if shared_truck else 1.0)
            transport_cost = round(freight + (qty_quintals * 25), 2)

            mandi_display = target_mandi if target_mandi else f"Mandi ({mandi_pincode})"
            village_display = farmer_village if farmer_village else f"Village ({farmer_pincode})"

            today_price, hist_df = fetch_and_store_mandi_price(crop_name, mandi_display, mandi_coords, crop_variety)

            if len(hist_df) >= 2:
                prev_price = float(hist_df.iloc[-2]["MODAL_PRICE_PER_QUINTAL"])
                weekly_growth = max(min((today_price - prev_price) / prev_price, 0.15), -0.15)
            elif os.path.exists("telangana_full_multiyear_data.csv"):
                try:
                    multi_df = pd.read_csv("telangana_full_multiyear_data.csv")
                    sub = multi_df[multi_df["Commodity"].str.lower().str.contains(crop_name.strip().lower(), na=False)].copy()
                    if crop_variety != "All Varieties" and "Variety" in sub.columns:
                        var_sub = sub[sub["Variety"].str.lower().str.contains(crop_variety.lower(), na=False, regex=False)]
                        if len(var_sub) >= 10:
                            sub = var_sub
                    dist_sub = sub[sub["District"].str.lower() == farmer_district.lower()]
                    if len(dist_sub) >= 10:
                        sub = dist_sub
                    if len(sub) >= 10:
                        sub["Modal_Price"] = pd.to_numeric(sub["Modal_Price"], errors="coerce")
                        sub = sub.dropna(subset=["Modal_Price"])
                        recent_avg = sub["Modal_Price"].iloc[:5].mean()
                        older_avg = sub["Modal_Price"].iloc[5:10].mean()
                        weekly_growth = max(min((recent_avg - older_avg) / older_avg, 0.15), -0.15)
                    else:
                        weekly_growth = 0.03
                except Exception:
                    weekly_growth = 0.03
            else:
                weekly_growth = 0.03

            weather = get_weather_risk(farmer_coords[0], farmer_coords[1])
            daily_growth = weekly_growth / 7.0
            daily_spoilage = (0.10 if weather["high_risk"] else 0.03) / 7.0

            # Day-by-Day Calculation (Day 0 = Today through Day 7) — No Storage Costs
            daily_rows = []
            for day in range(0, 8):
                est_price = round(today_price * (1 + daily_growth * day), 2)
                sellable_qty = qty_quintals * max(0.0, (1 - daily_spoilage * day))
                net_profit = round((est_price * sellable_qty) - transport_cost, 2)
                day_label = "Today (Day 0)" if day == 0 else f"Day {day}"
                daily_rows.append({
                    "Day": day_label,
                    "Day_Num": day,
                    "Est. Price (₹/qtl)": est_price,
                    "Sellable Qty (qtl)": round(sellable_qty, 2),
                    "Net Profit (₹)": net_profit
                })

            daily_df = pd.DataFrame(daily_rows)
            best_idx = daily_df["Net Profit (₹)"].idxmax()
            best_day_row = daily_df.loc[best_idx]
            profit_diff = round(best_day_row["Net Profit (₹)"] - daily_df.loc[0, "Net Profit (₹)"], 2)

            crop_label_for_log = f"{crop_name.strip().title()} ({crop_variety})" if crop_variety != "All Varieties" else crop_name.strip().title()

            summary_record = {
                "Check_Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Farmer_Village": village_display,
                "Farmer_Pincode": farmer_pincode,
                "District": farmer_district,
                "Target_Mandi": mandi_display,
                "Mandi_Pincode": mandi_pincode,
                "Crop_Name": crop_label_for_log,
                "Quantity_Quintals": qty_quintals,
                "Shared_Truck": "Yes" if shared_truck else "No",
                "Road_Distance_KM": road_km,
                "Transport_Cost": transport_cost,
                "Today_Price_Per_Qtl": today_price,
                "Net_Profit_Today": daily_df.loc[0, "Net Profit (₹)"],
                "Optimal_Sell_Day": best_day_row["Day"],
                "Peak_Net_Profit": best_day_row["Net Profit (₹)"],
                "Profit_Gain_Vs_Today": profit_diff,
                "Rain_7D_MM": weather["rain_mm"],
                "Max_Temp_C": weather["max_temp"],
                "Weather_Risk": "High" if weather["high_risk"] else "Low"
            }
            db_ok = log_farmer_search_to_db_and_csv(summary_record, daily_df)

            st.session_state["calc_result"] = {
                "farmer_coords": farmer_coords,
                "mandi_coords": mandi_coords,
                "road_km": road_km,
                "transport_cost": transport_cost,
                "today_price": today_price,
                "net_today": daily_df.loc[0, "Net Profit (₹)"],
                "best_day_label": best_day_row["Day"],
                "best_day_num": int(best_day_row["Day_Num"]),
                "best_profit": best_day_row["Net Profit (₹)"],
                "diff": profit_diff,
                "daily_df": daily_df,
                "weather": weather,
                "village_display": village_display,
                "farmer_pincode": farmer_pincode,
                "mandi_display": mandi_display,
                "db_ok": db_ok
            }

#6. RESULTS DISPLAY, VOICE ADVICE, CHARTS & LIVE MAP

if "calc_result" in st.session_state:
    res = st.session_state["calc_result"]
    weather = res["weather"]

    if weather["high_risk"]:
        st.warning(t["weather_risk"].format(rain=weather["rain_mm"], temp=weather["max_temp"]))
    else:
        st.success(t["weather_safe"].format(rain=weather["rain_mm"]))

    m1, m2, m3 = st.columns(3)
    m1.metric(t["dist_metric"], f"{res['road_km']} km", f"₹{res['transport_cost']:,.0f}")
    m2.metric(t["today_metric"], f"₹{res['net_today']:,.0f}", f"₹{res['today_price']:,.0f}/qtl")
    m3.metric(
        f"Peak Profit ({res['best_day_label']})" if lang_key == "English" else f"గరిష్ట లాభం ({res['best_day_label']})",
        f"₹{res['best_profit']:,.0f}",
        f"{res['diff']:+,.0f} ₹ vs Today"
    )

    if res["best_day_num"] == 0:
        verdict_en = (
            f"Distance from {res['village_display']} (PIN {res['farmer_pincode']}) to {res['mandi_display']} is {res['road_km']} km. "
            f"Best Action: SELL TODAY for ₹{res['net_today']:,.0f} net profit (holding further reduces profit due to spoilage risk)."
        )
        verdict_te = (
            f"{res['village_display']} (పిన్‌కోడ్ {res['farmer_pincode']}) నుండి {res['mandi_display']} మండికి దూరం {res['road_km']} కిలోమీటర్లు. "
            f"ఉత్తమ సలహా: ఈరోజే అమ్మండి (₹{res['net_today']:,.0f} నికర లాభం). ఎక్కువ రోజులు ఆగితే పంట పాడయ్యే ప్రమాదం వల్ల లాభం తగ్గుతుంది."
        )
    else:
        verdict_en = (
            f"Distance from {res['village_display']} (PIN {res['farmer_pincode']}) to {res['mandi_display']} is {res['road_km']} km. "
            f"Best Action: WAIT UNTIL {res['best_day_label'].upper()} to sell! "
            f"Peak net profit is ₹{res['best_profit']:,.0f} ({res['diff']:+,.0f} ₹ more than selling today)."
        )
        verdict_te = (
            f"{res['village_display']} (పిన్‌కోడ్ {res['farmer_pincode']}) నుండి {res['mandi_display']} మండికి దూరం {res['road_km']} కిలోమీటర్లు. "
            f"ఉత్తమ సలహా: {res['best_day_label']} వరకు ఆగి అమ్మండి! "
            f"అప్పుడు గరిష్ట నికర లాభం ₹{res['best_profit']:,.0f} వస్తుంది (ఈరోజు కంటే ₹{res['diff']:+,.0f} అదనం)."
        )

    st.subheader(f"🏆 {t['decision_header']}")
    st.info(verdict_te if lang_key == "Telugu" else verdict_en)

    st.caption(f"🔊 {t['voice_caption']}")
    speak_audio(
        verdict_te if lang_key == "Telugu" else verdict_en,
        lang_code="te" if lang_key == "Telugu" else "en"
    )

    st.subheader("📈 Day-by-Day Net Profit Forecast (Day 0 to Day 7)" if lang_key == "English" else "📈 రోజువారీ నికర లాభం అంచనా (ఈరోజు నుండి 7వ రోజు వరకు)")
    chart_df = res["daily_df"].set_index("Day")[["Net Profit (₹)"]]
    st.line_chart(chart_df)
    st.dataframe(res["daily_df"].drop(columns=["Day_Num"]), use_container_width=True)

    st.subheader(f"🗺️ {t['map_header']}")
    f_coords = res["farmer_coords"]
    m_coords = res["mandi_coords"]
    center_lat = (f_coords[0] + m_coords[0]) / 2
    center_lon = (f_coords[1] + m_coords[1]) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=9)

    folium.Marker(
        f_coords,
        popup=f"Farmer: {res['village_display']} ({res['farmer_pincode']})",
        icon=folium.Icon(color="green", icon="home")
    ).add_to(m)

    folium.Marker(
        m_coords,
        popup=f"Target Mandi: {res['mandi_display']}",
        icon=folium.Icon(color="red", icon="shopping-cart")
    ).add_to(m)

    folium.PolyLine(
        [f_coords, m_coords],
        color="blue",
        weight=4,
        tooltip=f"Road Distance: ~{res['road_km']} km"
    ).add_to(m)

    st_folium(m, width=700, height=400, returned_objects=[])

    st.divider()
    st.success(f"Data logged to {'MySQL (`FARMER_PRICE_CHECKS`) and ' if res['db_ok'] else ''}CSV files for Power BI.")
    if os.path.exists(SUMMARY_CSV_PATH):
        with open(SUMMARY_CSV_PATH, "rb") as f:
            st.download_button(
                label="📥 Download Farmer Summary CSV (For Power BI)",
                data=f,
                file_name=SUMMARY_CSV_PATH,
                mime="text/csv"
            )




#7. FARMER DOUBTS & IMPROVEMENTS SECTION

st.divider()
st.subheader(f"💬 {t['fb_header']}")
st.caption(t["fb_sub"])

with st.form("farmer_feedback_form", clear_on_submit=True):
    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        fb_category = st.selectbox(t["fb_type"], t["fb_types"])
    with fb_col2:
        fb_user = st.text_input(t["fb_name"], placeholder="e.g., Ramesh / Peddapalli")

    fb_text = st.text_area(t["fb_msg"], height=100)
    voice_label = "🎙️ Or Record Your Voice Message (Speak in Telugu / English)" if lang_key == "English" else "🎙️ లేదా మీ వాయిస్ మెసేజ్ రికార్డ్ చేయండి (తెలుగు / ఇంగ్లీష్‌లో మాట్లాడండి)"
    fb_voice = st.audio_input(voice_label)
    fb_submitted = st.form_submit_button(f"{t['fb_btn']} 📩")

    if fb_submitted:
        if not fb_text.strip() and fb_voice is None:
            st.warning(t["fb_warn"])
        else:
            final_msg = fb_text.strip()
            if fb_voice is not None:
                os.makedirs("farmer_voice_notes", exist_ok=True)
                audio_file = os.path.join("farmer_voice_notes", f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
                with open(audio_file, "wb") as f:
                    f.write(fb_voice.getbuffer())
                final_msg = f"{final_msg} [Voice Note: {audio_file}]".strip()

            save_farmer_feedback(fb_category, fb_user, final_msg, lang_key)
            st.success(t["fb_success"])
