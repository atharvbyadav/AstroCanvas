#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit App: Whole Sign / Placidus Natal Chart with Wheel + Aspect Lines

Features
- Interactive inputs (date, time, tz, lat, lon, house system, orbs, toggles)
- Live chart rendering with aspect lines
- Retrograde marking
- Planet positions table (sign/deg/min, retrograde)
- Download buttons (PNG chart, CSV & JSON positions)

Requirements
    pip install streamlit pyswisseph matplotlib pandas

Run
    streamlit run app.py

Note
- This app uses a numeric timezone offset (e.g., 5.5 for IST). If you want auto TZ from place, add a geocoder/timezone lookup.
"""

import math
import json
import csv
from io import BytesIO
from datetime import datetime, timedelta, date, time as dtime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import swisseph as swe

# ----------------------------- Constants -----------------------------
SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

SIGN_GLYPHS = [
    "\u2648","\u2649","\u264A","\u264B","\u264C","\u264D",
    "\u264E","\u264F","\u2650","\u2651","\u2652","\u2653"
]

PLANETS = [
    ("Sun", swe.SUN, "\u2609"),
    ("Moon", swe.MOON, "\u263D"),
    ("Mercury", swe.MERCURY, "\u263F"),
    ("Venus", swe.VENUS, "\u2640"),
    ("Mars", swe.MARS, "\u2642"),
    ("Jupiter", swe.JUPITER, "\u2643"),
    ("Saturn", swe.SATURN, "\u2644"),
    ("Uranus", swe.URANUS, "\u2645"),
    ("Neptune", swe.NEPTUNE, "\u2646"),
    ("Pluto", swe.PLUTO, "\u2647"),
]

DEFAULT_ASPECTS = [
    ("Conjunction", 0,   8, "#6b7280", 1.6),  # gray
    ("Sextile",     60,  4, "#10b981", 1.6),  # green
    ("Square",      90,  6, "#ef4444", 1.8),  # red
    ("Trine",       120, 6, "#3b82f6", 1.8),  # blue
    ("Opposition",  180, 8, "#8b5cf6", 1.8),  # purple
]

HOUSE_SYSTEMS = {
    "Whole Sign": b"W",
    "Placidus": b"P",
    "Equal": b"E",
}

# ----------------------------- Helpers -----------------------------

def normalize(lon: float) -> float:
    return lon % 360.0


def sign_index(lon: float) -> int:
    return int((lon % 360.0) // 30)


def lon_in_sign(lon: float):
    lon = lon % 360.0
    idx = sign_index(lon)
    deg_in_sign = lon - 30 * idx
    d = int(deg_in_sign)
    m = int((deg_in_sign - d) * 60)
    return SIGNS[idx], d, m


def min_angle(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def angle_to_xy(angle_deg: float, radius: float, asc_deg: float):
    theta = math.radians((angle_deg - asc_deg + 180) % 360)
    return radius * math.cos(theta), radius * math.sin(theta)


# ------------------------- Core Ephemeris Logic -------------------------

def compute_chart(date_str: str, time_str: str, tz_hours: float, lat: float, lon: float,
                  house_system_code: bytes = b"W", use_moshier: bool = True):
    flags = swe.FLG_MOSEPH if use_moshier else swe.FLG_SWIEPH

    dt_local = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    dt_ut = dt_local - timedelta(hours=tz_hours)
    jd_ut = swe.julday(
        dt_ut.year, dt_ut.month, dt_ut.day,
        dt_ut.hour + dt_ut.minute/60.0 + dt_ut.second/3600.0, swe.GREG_CAL
    )

    positions = {}
    speeds = {}
    for name, pid, _ in PLANETS:
        xx, _ = swe.calc_ut(jd_ut, pid, flags)
        lon_ecl = normalize(xx[0])
        positions[name] = lon_ecl
        speeds[name] = xx[3]  # longitude speed; retrograde if negative

    ascmc, cusps = swe.houses(jd_ut, lat, lon, house_system_code)
    asc = normalize(ascmc[0])
    mc = normalize(ascmc[1])

    # Whole Sign cusp handling (override cusps to whole signs from Asc sign)
    if house_system_code == b"W":
        asc_sign = sign_index(asc)
        ws_cusps = [(30 * ((asc_sign + i) % 12)) for i in range(12)]
    else:
        # Use system cusps from Swiss Ephemeris
        ws_cusps = [normalize(c) for c in cusps]

    return {
        "jd_ut": jd_ut,
        "dt_ut": dt_ut.isoformat(),
        "positions": positions,
        "speeds": speeds,
        "asc": asc,
        "mc": mc,
        "cusps": ws_cusps,
    }


def build_aspects(positions: dict, aspects_def: list):
    keys = [name for (name, _, _) in PLANETS]
    found = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            p1, p2 = keys[i], keys[j]
            d = min_angle(positions[p1], positions[p2])
            for aname, aangle, orb, color, lw in aspects_def:
                if abs(d - aangle) <= orb:
                    found.append({
                        "p1": p1, "p2": p2,
                        "sep": d, "aspect": aname,
                        "color": color, "lw": lw
                    })
    return found


# ------------------------------ Drawing ------------------------------

def draw_chart(data: dict, aspects_def: list, show_aspects: bool = True,
               mark_retrograde: bool = True) -> bytes:
    pos = data["positions"]
    asc = data["asc"]
    mc = data["mc"]
    cusps = data["cusps"]
    speeds = data.get("speeds", {})

    R_outer = 1.00
    R_signs = 1.07
    R_plan = 0.78
    R_aspect_inner = 0.15

    fig, ax = plt.subplots(figsize=(8.8, 8.8))
    ax.set_aspect("equal")
    ax.axis("off")

    circ_out = plt.Circle((0, 0), R_outer, fill=False, lw=2.0)
    circ_in = plt.Circle((0, 0), R_plan, fill=False, lw=1.0, linestyle=":")
    ax.add_artist(circ_out)
    ax.add_artist(circ_in)

    # House/sign boundaries
    for cusp in cusps:
        x1, y1 = angle_to_xy(cusp, 0.0, asc)
        x2, y2 = angle_to_xy(cusp, R_outer, asc)
        ax.plot([x1, x2], [y1, y2], lw=1.1, color="#000000")

    # Sign glyphs at house centers (works for Whole Sign and looks fine for others)
    for cusp in cusps:
        mid = (cusp + 15) % 360
        xs, ys = angle_to_xy(mid, R_signs, asc)
        ax.text(xs, ys, SIGN_GLYPHS[sign_index(cusp)], fontsize=18,
                ha="center", va="center")

    # Planet glyphs (mark retrograde as small "R" if enabled)
    for (name, _, glyph) in PLANETS:
        x, y = angle_to_xy(pos[name], R_plan, asc)
        ax.text(x, y, glyph, fontsize=16, ha="center", va="center")
        if mark_retrograde and speeds.get(name, 0) < 0:
            ax.text(x, y - 0.05, "R", fontsize=8, ha="center", va="center")

    # ASC & MC labels
    x_asc, y_asc = angle_to_xy(asc, R_signs, asc)
    ax.text(x_asc, y_asc, "ASC", fontsize=10, ha="center", va="center")

    x_mc, y_mc = angle_to_xy(mc, R_signs, asc)
    ax.text(x_mc, y_mc, "MC", fontsize=10, ha="center", va="center")

    # Aspect lines
    if show_aspects:
        aspects = build_aspects(pos, aspects_def)
        for a in aspects:
            x1, y1 = angle_to_xy(pos[a["p1"]], R_plan - R_aspect_inner, asc)
            x2, y2 = angle_to_xy(pos[a["p2"]], R_plan - R_aspect_inner, asc)
            ax.plot([x1, x2], [y1, y2], color=a["color"], lw=a["lw"], alpha=0.9)

        legend_items = []
        for name, angle, _, color, lw in aspects_def:
            legend_items.append(plt.Line2D([0], [0], color=color, lw=lw, label=name))
        ax.legend(handles=legend_items, loc="upper center", bbox_to_anchor=(0.5, -0.05),
                  ncol=3, frameon=False, fontsize=9)

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ------------------------------ UI App ------------------------------
st.set_page_config(page_title="Interactive Natal Chart", page_icon="🪐", layout="wide")
st.title("🪐 Interactive Natal Chart Generator")
st.caption("Whole Sign / Placidus wheel with aspects, retrograde markers, downloads.")

with st.sidebar:
    st.header("Input")
    colA, colB = st.columns(2)
    with colA:
        bdate: date = st.date_input("Birth Date", value=date(2005, 5, 22))
    with colB:
        btime: dtime = st.time_input("Birth Time", value=dtime(2, 6))

    tz = st.number_input("Timezone offset (hours)", value=5.5, step=0.25, help="e.g., 5.5 for IST")
    lat = st.number_input("Latitude (N+ / S-)", value=26.45, format="%.6f")
    lon = st.number_input("Longitude (E+ / W-)", value=80.33, format="%.6f")

    house_label = st.selectbox("House System", list(HOUSE_SYSTEMS.keys()), index=0)
    use_moshier = st.checkbox("Use Moshier Ephemeris", value=True)

    st.header("Aspects & Options")
    show_aspects = st.checkbox("Show Aspects", value=True)
    mark_retro = st.checkbox("Mark Retrograde", value=True)

    # Custom orbs per aspect
    st.subheader("Orbs (degrees)")
    orb_conj = st.slider("Conjunction", 0.0, 12.0, 8.0, 0.5)
    orb_sext = st.slider("Sextile", 0.0, 10.0, 4.0, 0.5)
    orb_sqr  = st.slider("Square", 0.0, 10.0, 6.0, 0.5)
    orb_tri  = st.slider("Trine", 0.0, 10.0, 6.0, 0.5)
    orb_opp  = st.slider("Opposition", 0.0, 12.0, 8.0, 0.5)

    generate = st.button("Generate Chart", use_container_width=True)

# Compute on demand
if generate:
    date_str = bdate.strftime("%Y-%m-%d")
    time_str = btime.strftime("%H:%M")

    aspects_def = [
        ("Conjunction", 0,   orb_conj, "#6b7280", 1.6),
        ("Sextile",     60,  orb_sext, "#10b981", 1.6),
        ("Square",      90,  orb_sqr,  "#ef4444", 1.8),
        ("Trine",       120, orb_tri,  "#3b82f6", 1.8),
        ("Opposition",  180, orb_opp,  "#8b5cf6", 1.8),
    ]

    data = compute_chart(
        date_str=date_str,
        time_str=time_str,
        tz_hours=float(tz),
        lat=float(lat),
        lon=float(lon),
        house_system_code=HOUSE_SYSTEMS[house_label],
        use_moshier=use_moshier,
    )

    # Chart bytes
    png_bytes = draw_chart(data, aspects_def, show_aspects=show_aspects, mark_retrograde=mark_retro)

    # Build positions table
    rows = []
    for name, lon_deg in data["positions"].items():
        s, d, m = lon_in_sign(lon_deg)
        rows.append({
            "Body": name,
            "Longitude (°)": round(lon_deg, 6),
            "Sign": s,
            "Deg": d,
            "Min": m,
            "Retrograde": data["speeds"].get(name, 0) < 0,
        })
    df = pd.DataFrame(rows)

    # Aspect list
    aspect_list = build_aspects(data["positions"], aspects_def) if show_aspects else []
    aspect_rows = [
        {"Aspect": a["aspect"], "Body 1": a["p1"], "Body 2": a["p2"], "Separation (°)": round(a["sep"], 2)}
        for a in aspect_list
    ]
    df_aspects = pd.DataFrame(aspect_rows)

    # Layout
    col1, col2 = st.columns([1.05, 0.95])

    with col1:
        st.subheader("Chart Wheel")
        st.image(png_bytes, caption=f"ASC {data['asc']:.2f}°, MC {data['mc']:.2f}° | UT: {data['dt_ut']}", use_column_width=True)
        st.download_button("Download Chart PNG", data=png_bytes, file_name="natal_chart.png", mime="image/png")

    with col2:
        st.subheader("Planetary Positions")
        st.dataframe(df, use_container_width=True)

        # CSV & JSON downloads
        csv_buf = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Positions CSV", data=csv_buf, file_name="natal_positions.csv", mime="text/csv")

        json_obj = {k: float(v) for k, v in data["positions"].items()}
        json_bytes = json.dumps(json_obj, indent=2).encode("utf-8")
        st.download_button("Download Positions JSON", data=json_bytes, file_name="natal_positions.json", mime="application/json")

        if show_aspects:
            st.subheader("Aspects Found")
            if len(df_aspects) == 0:
                st.info("No aspects found within the selected orbs.")
            else:
                st.dataframe(df_aspects, use_container_width=True)

    # Footer info
    st.caption(f"Julian Day (UT): {data['jd_ut']:.5f} | House system: {house_label}")
else:
    st.info("Set your inputs on the left and click **Generate Chart**.")
