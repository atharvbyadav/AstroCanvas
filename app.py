#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstroCanvas — Maharashtra Edition (Multilanguage)

This file is the Maharashtra-first Streamlit app with multilingual support (English, Marathi, Hindi)
and automatic language detection (browser param -> IP region fallback -> Marathi default).

Run:
    pip install streamlit pyswisseph matplotlib pandas timezonefinder pytz geopy requests
    streamlit run astrocanvas_maharashtra.py

Notes:
- Language auto-detection tries (in order): query param ?lang=, browser-sent lang via query param, IP geolocation.
- No cookies or persistent storage are used; manual language selection in sidebar overrides detection for the session.
"""

import math
import json
import requests
from io import BytesIO
from datetime import datetime, timedelta, date, time as dtime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import swisseph as swe

# Optional utilities
try:
    from timezonefinder import TimezoneFinder
    import pytz
    TZ_AVAILABLE = True
except Exception:
    TZ_AVAILABLE = False

try:
    from geopy.geocoders import Nominatim
    GEO_AVAILABLE = True
except Exception:
    GEO_AVAILABLE = False

# -------------------- Translations --------------------
translations = {
    'en': {
        'app_title': 'AstroCanvas — Maharashtra Edition',
        'subtitle': 'Maharashtra-first Vedic Kundali with multilingual support',
        'birth_data': 'Birth data',
        'lookup_city': 'Lookup by city (optional)',
        'city_input': 'City / Place name (e.g., Mumbai, India)',
        'birth_date': 'Birth Date',
        'birth_time': 'Birth Time (local)',
        'latitude': 'Latitude (°)',
        'longitude': 'Longitude (°)',
        'auto_tz': 'Auto-detect timezone',
        'tz_input': 'Timezone offset (hours)',
        'mode': 'Display mode',
        'mode_options': ['Maharashtra (North Kundali)','South Indian','Western (Tropical)'],
        'translit': 'Show Devanagari labels',
        'generate': 'Generate Kundali',
        'kundali': 'Kundali',
        'panchang': 'Panchang',
        'tithi': 'Tithi',
        'nakshatra': 'Nakshatra',
        'yoga': 'Yoga',
        'karana': 'Karana',
        'vimshottari': 'Vimshottari Mahadasha',
        'positions': 'Planetary positions',
        'download_png': 'Download Kundali PNG',
        'info_fill': 'Fill inputs in the sidebar and click Generate Kundali',
        'tz_auto_msg': 'Auto TZ: {tzname} (offset {tz} h)',
        'not_found': 'Location not found.',
        'geocode_err': 'Geocoding error: {err}',
        'panchang_na': 'Panchang could not be computed.'
    },
    'mr': {
        'app_title': 'AstroCanvas — महाराष्ट्र आवृत्ती',
        'subtitle': 'मराठी-प्राधान्य विकेतिक कौंडली आणि बहुभाषिक समर्थन',
        'birth_data': 'जन्म माहिती',
        'lookup_city': 'शहराने शोधा (ऐच्छिक)',
        'city_input': 'शहर / ठिकाण (उदा. मुंबई, भारत)',
        'birth_date': 'जन्माची तारीख',
        'birth_time': 'जन्माची वेळ (स्थानिक)',
        'latitude': 'अक्षांश (Latitude)',
        'longitude': 'रेखांश (Longitude)',
        'auto_tz': 'टाईमझोन आपोआप शोधा',
        'tz_input': 'टाईमझोन ऑफसेट (तास)',
        'mode': 'प्रदर्शन पद्धत',
        'mode_options': ['महाराष्ट्र (North Kundali)','दक्षिण भारतीय','पाश्चात्य (Tropical)'],
        'translit': 'देवनागरी लेबल दाखवा',
        'generate': 'कौंडली तयार करा',
        'kundali': 'कौंडली',
        'panchang': 'पंचांग',
        'tithi': 'तिठी',
        'nakshatra': 'नक्षत्र',
        'yoga': 'योग',
        'karana': 'करण',
        'vimshottari': 'विम्शोत्तरी महासंहिता',
        'positions': "ग्रहांची स्थिती",
        'download_png': 'कौंडली PNG डाउनलोड करा',
        'info_fill': 'साइडबार मधून माहिती भरा आणि "कौंडली तयार करा" क्लिक करा',
        'tz_auto_msg': 'ऑटो TZ: {tzname} (ऑफसेट {tz} तास)',
        'not_found': 'स्थळ सापडले नाही.',
        'geocode_err': 'Geocoding त्रुटी: {err}',
        'panchang_na': 'पंचांग मोजता आले नाही.'
    },
    'hi': {
        'app_title': 'AstroCanvas — महाराष्ट्र संस्करण',
        'subtitle': 'महाराष्ट्र-प्राथमिक वैदिक कुंडली और बहुभाषी समर्थन',
        'birth_data': 'जन्म जानकारी',
        'lookup_city': 'शहर से खोजें (वैकल्पिक)',
        'city_input': 'शहर / स्थान (उदा. मुंबई, भारत)',
        'birth_date': 'जन्म तारीख',
        'birth_time': 'जन्म समय (स्थानीय)',
        'latitude': 'अक्षांश (Latitude)',
        'longitude': 'रेखांश (Longitude)',
        'auto_tz': 'टाइमज़ोन स्वचालित रूप से खोजें',
        'tz_input': 'टाइमज़ोन ऑफसेट (घंटे)',
        'mode': 'प्रदर्शन मोड',
        'mode_options': ['महाराष्ट्र (North Kundali)','दक्षिण भारतीय','पश्चिमी (Tropical)'],
        'translit': 'देवनागरी लेबल दिखाएं',
        'generate': 'कुंडली बनाएं',
        'kundali': 'कुंडली',
        'panchang': 'पंचांग',
        'tithi': 'तिथि',
        'nakshatra': 'नक्षत्र',
        'yoga': 'योग',
        'karana': 'करण',
        'vimshottari': 'विम्शोत्तरी महामहादशा',
        'positions': 'ग्रह स्थिति',
        'download_png': 'कुंडली PNG डाउनलोड करें',
        'info_fill': 'साइडबार में जानकारी भरें और "कुंडली बनाएं" पर क्लिक करें',
        'tz_auto_msg': 'ऑटो TZ: {tzname} (ऑफसेट {tz} घँटे)',
        'not_found': 'स्थान नहीं मिला।',
        'geocode_err': 'Geocoding त्रुटि: {err}',
        'panchang_na': 'पंचांग की गणना नहीं हो सकी.'
    }
}

# -------------------- Marathi / Devanagari helpers --------------------
DEV_NUM = {0:'०',1:'१',2:'२',3:'३',4:'४',5:'५',6:'६',7:'७',8:'८',9:'९'}

def to_devanagari_num(n):
    s = str(n)
    return ''.join(DEV_NUM.get(int(ch), ch) for ch in s)

MAR_PLANET_SHORT = {
    'Sun':'सूर्य','Moon':'चं','Mercury':'बुध','Venus':'शुक्र','Mars':'मं','Jupiter':'गुरु','Saturn':'शनि','Rahu':'राहु','Ketu':'केतु'
}

MAR_TITHI = [
    'शुक्ल प्रतिपदा','शुक्ल द्वितीया','शुक्ल तृतीया','शुक्ल चतुर्थी','शुक्ल पंचमी','शुक्ल षष्ठी','शुक्ल सप्तमी','शुक्ल अष्टमी','शुक्ल नवमी','शुक्ल दशमी',
    'शुक्ल एकादशी','शुक्ल द्वादशी','शुक्ल त्रयोदशी','शुक्ल चतुर्दशी','पुर्णिमा/अमावास्या','कृष्ण प्रतिपदा','कृष्ण द्वितीया','कृष्ण तृतीया','कृष्ण चतुर्थी','कृष्ण पंचमी',
    'कृष्ण षष्ठी','कृष्ण सप्तमी','कृष्ण अष्टमी','कृष्ण नवमी','कृष्ण दशमी','कृष्ण एकादशी','कृष्ण द्वादशी','कृष्ण त्रयोदशी','कृष्ण चतुर्दशी','अमावास्या/पुर्णिमा'
]

MAR_NAK = [
    'अश्विनी','भरणी','कृत्तिका','रोहिणी','मृगशीर्ष','आर्द्रा','पुनर्वसु','पुष्य','आश्लेषा','मघा','पूर्व फाल्गुनी','उत्तर फाल्गुनी','हस्त','चित्रा','स्वाती','विशाखा',
    'अनुराधा','ज्येष्ठा','मूल','पूर्वाषाढा','उत्तराषाढा','श्रवण','धनिष्ठा','शतभिषा','पूर्वभाद्रपदा','उत्तरभाद्रपदा','रेवती'
]

# -------------------- Astrological constants --------------------
SIGNS_EN = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
SIGNS_DEV = ['मेष','वृषभ','मिथुन','कर्क','सिंह','कन्या','तुला','वृश्चिक','धनु','मकर','कुंभ','मीन']

VIM_DASHA_ORDER = ['Ketu','Venus','Sun','Moon','Mars','Rahu','Jupiter','Saturn','Mercury']
VIM_DASHA_YEARS = {'Ketu':7,'Venus':20,'Sun':6,'Moon':10,'Mars':7,'Rahu':18,'Jupiter':16,'Saturn':19,'Mercury':17}

# -------------------- Helpers --------------------
def normalize(lon):
    return lon % 360.0

def sign_index(lon):
    return int((lon % 360.0) // 30)

def dms(angle):
    angle = normalize(angle)
    deg = int(angle)
    rem = (angle - deg) * 60
    minute = int(rem)
    second = int((rem - minute) * 60)
    return deg, minute, second

# -------------------- Ayanamsa --------------------
def get_lahiri_ayanamsa(jd_ut):
    try:
        a = swe.get_ayanamsa_ut(jd_ut)
        return a / 3600.0
    except Exception:
        try:
            a = swe.get_ayanamsa(jd_ut)
            return a
        except Exception:
            return 0.0

# -------------------- Compute positions --------------------
def compute_chart(date_str, time_str, tz_hours, lat, lon, sidereal=True, topo=True):
    dt_local = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    dt_ut = dt_local - timedelta(hours=tz_hours)
    jd_ut = swe.julday(dt_ut.year, dt_ut.month, dt_ut.day, dt_ut.hour + dt_ut.minute/60.0, swe.GREG_CAL)

    if topo:
        swe.set_topo(lon, lat, 0)

    flags = swe.FLG_SWIEPH | swe.FLG_TOPOCTR

    bodies = [("Sun",swe.SUN),("Moon",swe.MOON),("Mercury",swe.MERCURY),("Venus",swe.VENUS),("Mars",swe.MARS),("Jupiter",swe.JUPITER),("Saturn",swe.SATURN)]
    pos = {}
    speed = {}
    ay = get_lahiri_ayanamsa(jd_ut) if sidereal else 0.0

    for name,bid in bodies:
        xx, serr = swe.calc_ut(jd_ut, bid, flags)
        lon_val = normalize(xx[0] - (ay if sidereal else 0.0))
        pos[name] = lon_val
        speed[name] = xx[3]

    # Nodes
    try:
        rn, serr = swe.calc_ut(jd_ut, swe.TRUE_NODE, flags)
        rn_lon = normalize(rn[0] - (ay if sidereal else 0.0))
        kn_lon = normalize(rn_lon + 180)
        pos['Rahu'] = rn_lon
        pos['Ketu'] = kn_lon
    except Exception:
        pos['Rahu'] = None
        pos['Ketu'] = None

    # Ascendant (whole sign for simple kundali mapping)
    try:
        ascmc, cusps = swe.houses(jd_ut, lat, lon, b'W')
        asc = normalize(ascmc[0] - (ay if sidereal else 0.0))
        mc = normalize(ascmc[1] - (ay if sidereal else 0.0))
    except Exception:
        asc, mc = None, None

    return {'jd_ut': jd_ut, 'dt_ut': dt_ut.isoformat(), 'positions':pos, 'speeds':speed, 'asc':asc, 'mc':mc}

# -------------------- Panchang & Vimshottari --------------------
def compute_panchang(pos):
    sun = pos.get('Sun')
    moon = pos.get('Moon')
    if sun is None or moon is None:
        return None
    diff = normalize(moon - sun)
    tithi_index = int(diff // 12)

    nak_index = int(moon // (360.0/27.0))

    yoga_val = normalize(sun + moon)
    yoga_index = int(yoga_val // (360.0/27.0))

    karana_index = (tithi_index * 2) % 11

    return {'tithi_idx':tithi_index, 'tithi_mar':MAR_TITHI[tithi_index], 'nak_idx':nak_index, 'nak_mar':MAR_NAK[nak_index], 'yoga_idx':yoga_index, 'karana_idx':karana_index}


def vimshottari(pos):
    moon_lon = pos.get('Moon')
    if moon_lon is None:
        return None
    nak_index = int(moon_lon // (360.0/27.0))
    order = VIM_DASHA_ORDER
    mapping = [order[i%9] for i in range(27)]
    start_lord = mapping[nak_index]
    nak_deg = moon_lon % (360.0/27.0)
    frac = nak_deg / (360.0/27.0)
    total_years = VIM_DASHA_YEARS[start_lord]
    balance = (1 - frac) * total_years
    seq = [{'lord':start_lord, 'years':balance, 'from_now':0.0}]
    idx0 = order.index(start_lord)
    running = balance
    for i in range(1,9):
        lord = order[(idx0 + i) % 9]
        years = VIM_DASHA_YEARS[lord]
        seq.append({'lord':lord, 'years':years, 'from_now':running})
        running += years
    return seq

# -------------------- Maharashtra-specific Kundali drawing --------------------

def draw_kundali_maharashtra(pos, asc, translit=True, highlight_mumbai=True):
    """Draw a North-Indian diamond kundali with Marathi labels and Devanagari numerals for houses.
    highlight_mumbai: if True, customize colors/icons used in Maharashtra style (subtle)
    """
    fig, ax = plt.subplots(figsize=(6,6))
    ax.set_xlim(0,4)
    ax.set_ylim(0,4)
    ax.axis('off')

    # Draw diamond
    diamond = [(2,0),(4,2),(2,4),(0,2),(2,0)]
    xs, ys = zip(*diamond)
    ax.plot(xs, ys, color='#2b2b2b', lw=2)

    # Compute sign centers around diamond (clockwise starting at top = Aries in North Indian)
    sign_centers = []
    for angle in [90,30,-30,-90,-150,-210,-270,-330,90,30,-30,-90][:12]:
        rad = math.radians(angle)
        x = 2 + 1.4 * math.cos(rad)
        y = 2 + 1.4 * math.sin(rad)
        sign_centers.append((x,y))

    # Place Devanagari numerals for houses in Maharashtra convention (1-12 in Devanagari)
    for i,(sx,sy) in enumerate(sign_centers):
        house_num = to_devanagari_num(i+1)
        ax.text(sx, sy+0.45, SIGNS_DEV[i], fontsize=12, ha='center', va='center', fontweight='bold')
        ax.text(sx, sy+0.22, house_num, fontsize=11, ha='center', va='center', color='#6b7280')

    # Place planets (Marathi short names)
    for name in ['Sun','Moon','Mercury','Venus','Mars','Jupiter','Saturn','Rahu','Ketu']:
        lon = pos.get(name)
        if lon is None:
            continue
        idx = sign_index(lon)
        x,y = sign_centers[idx]
        label = MAR_PLANET_SHORT.get(name, name if not translit else name)
        # Color by benefic/malefic simplified
        color = '#0b5394' if name in ['Sun','Moon','Venus','Jupiter','Mercury'] else '#b30000'
        bbox = dict(facecolor='white', edgecolor=color, boxstyle='round', alpha=0.9)
        ax.text(x, y-0.15, label, fontsize=12, ha='center', va='center', bbox=bbox)

    # Title & footer
    ax.set_title('आस्थ्रोकॅनव्हास — कौंडली (महाराष्ट्र शैली)', fontsize=13)
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=220)
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# -------------------- Language detection --------------------

def detect_language():
    # 1) Query params (allow ?lang= to override/detect browser-based language)
    q = st.experimental_get_query_params()
    lang_param = q.get('lang', [None])[0]
    if lang_param:
        lang = lang_param.lower()
        if lang.startswith('mr'):
            return 'mr'
        if lang.startswith('hi'):
            return 'hi'
        if lang.startswith('en'):
            return 'en'
    # 2) Try to use HTTP headers via Streamlit's _request_session (best-effort)
    # Note: Streamlit doesn't expose headers reliably; skip.
    # 3) IP-based geolocation fallback
    try:
        r = requests.get('https://ipapi.co/json/', timeout=3)
        if r.status_code == 200:
            info = r.json()
            region = info.get('region', '').lower()
            country = info.get('country_name', '')
            # Maharashtra region names check
            if 'maharashtra' in region or 'maharashtra' in info.get('region_code','').lower():
                return 'mr'
            if country == 'India':
                # default to Hindi for India unless browser says otherwise
                return 'hi'
    except Exception:
        pass
    # Fallback default
    return 'mr'

# -------------------- Streamlit UI --------------------

# Initial detection
detected_lang = detect_language()
# Session state: allow user override
if 'lang' not in st.session_state:
    st.session_state['lang'] = detected_lang

# Sidebar language selector
lang_labels = {'en': 'English', 'mr': 'मराठी', 'hi': 'हिन्दी'}
sel = st.sidebar.selectbox('Language / भाषा', options=[lang_labels[k] for k in lang_labels], index=list(lang_labels.keys()).index(st.session_state['lang']))
# Map back to code
inv = {v:k for k,v in lang_labels.items()}
st.session_state['lang'] = inv[sel]
L = translations[st.session_state['lang']]

# Page config and header
st.set_page_config(page_title=L['app_title'], page_icon='🪔', layout='wide')
st.title(L['app_title'])
st.write(L['subtitle'])

with st.sidebar:
    st.header(L['birth_data'])
    use_city = st.checkbox(L['lookup_city'], value=False)
    city_query = None
    if use_city:
        if not GEO_AVAILABLE:
            st.warning(L['geocode_err'].format(err='geopy not installed'))
            use_city = False
        else:
            city_query = st.text_input(L['city_input'])

    col1, col2 = st.columns(2)
    with col1:
        bdate: date = st.date_input(L['birth_date'], value=date(1990,1,1))
    with col2:
        btime: dtime = st.time_input(L['birth_time'], value=dtime(6,0))

    lat = st.number_input(L['latitude'], value=19.0760, format='%.6f')
    lon = st.number_input(L['longitude'], value=72.8777, format='%.6f')

    tz_auto = st.checkbox(L['auto_tz'], value=True)
    tz = None
    if tz_auto and TZ_AVAILABLE:
        try:
            tf = TimezoneFinder()
            tzname = tf.timezone_at(lat=lat, lng=lon)
            if tzname:
                tz_obj = pytz.timezone(tzname)
                local_dt = datetime.combine(bdate, btime)
                loc_dt = tz_obj.localize(local_dt, is_dst=None)
                tz = loc_dt.utcoffset().total_seconds() / 3600.0
                st.sidebar.write(L['tz_auto_msg'].format(tzname=tzname, tz=tz))
            else:
                tz = st.number_input(L['tz_input'], value=5.5, step=0.25)
        except Exception:
            tz = st.number_input(L['tz_input'], value=5.5, step=0.25)
    else:
        tz = st.number_input(L['tz_input'], value=5.5, step=0.25)

    st.header(L['mode'])
    mode = st.selectbox('', options=L['mode_options'])
    translit = st.checkbox(L['translit'], value=True)
    st.markdown('---')
    generate = st.button(L['generate'])

# Geocode city if requested
if use_city and city_query and GEO_AVAILABLE:
    geolocator = Nominatim(user_agent='astrocanvas_geo')
    try:
        loc = geolocator.geocode(city_query, timeout=10)
        if loc:
            lat, lon = round(loc.latitude,6), round(loc.longitude,6)
            st.sidebar.success(f"Found: {loc.address} -> ({lat}, {lon})")
        else:
            st.sidebar.error(L['not_found'])
    except Exception as e:
        st.sidebar.error(L['geocode_err'].format(err=e))

if generate:
    sidereal = not mode.startswith('Western') and not mode.startswith('पाश्चात्य')
    data = compute_chart(bdate.strftime('%Y-%m-%d'), btime.strftime('%H:%M'), float(tz), float(lat), float(lon), sidereal=sidereal)

    kundali_png = draw_kundali_maharashtra(data['positions'], data['asc'], translit=translit)

    panch = compute_panchang(data['positions'])
    dasha = vimshottari(data['positions']) if sidereal else None

    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        st.subheader(L['kundali'])
        st.image(kundali_png, use_column_width=True)
        st.download_button(L['download_png'], data=kundali_png, file_name='kundali_maharashtra.png', mime='image/png')
    with c2:
        st.subheader(L['panchang'])
        if panch:
            st.write(f"{L['tithi']}: {panch['tithi_mar']} (index {panch['tithi_idx']})")
            st.write(f"{L['nakshatra']}: {panch['nak_mar']} (index {panch['nak_idx']})")
            st.write(f"{L['yoga']}: index {panch['yoga_idx']}")
            st.write(f"{L['karana']}: index {panch['karana_idx']}")
        else:
            st.info(L['panchang_na'])

        st.markdown('---')
        st.subheader(L['vimshottari'])
        if dasha is None:
            st.info(L['panchang_na'])
        else:
            for entry in dasha:
                st.write(f"{entry['lord']}: {entry['years']:.3f} years (from {entry['from_now']:.3f})")

    # Planetary positions table
    rows = []
    for k,v in data['positions'].items():
        if v is None:
            continue
        deg, minute, second = dms(v)
        sign_en = SIGNS_EN[sign_index(v)]
        sign_dev = SIGNS_DEV[sign_index(v)]
        name_dev = MAR_PLANET_SHORT.get(k, k)
        rows.append({'Body_En':k, 'Body_Mar':name_dev, 'Longitude':round(v,6), 'Sign_En':sign_en, 'Sign_Mar':sign_dev, 'Deg':deg, 'Min':minute, 'Sec':second})
    df = pd.DataFrame(rows)
    st.subheader(L['positions'])
    if translit and st.session_state['lang'] in ['mr','hi']:
        st.dataframe(df[['Body_Mar','Longitude','Sign_Mar','Deg','Min','Sec']])
    else:
        st.dataframe(df[['Body_En','Longitude','Sign_En','Deg','Min','Sec']])

    st.caption(f"UTC: {data['dt_ut']} | Ayanamsa (deg): {get_lahiri_ayanamsa(data['jd_ut']):.6f}")
else:
    st.info(L['info_fill'])

# -------------------- End --------------------
