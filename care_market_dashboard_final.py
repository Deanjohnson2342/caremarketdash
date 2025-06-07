import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# --- Banner ---
st.markdown("""
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: red; font-size: 64px; margin:0;'>LFA</h1>
        <div style='font-size: 48px;'>❤️</div>
    </div>
""", unsafe_allow_html=True)

# --- Load data from Google Sheets as CSV ---
@st.cache_data
def load_data():
    csv_url = (
        "https://docs.google.com/spreadsheets/"
        "d/1iz-rjfmBNkfBj4KUxLWBHwaqTOvtfmbu"
        "/export?format=csv"
    )
    df = pd.read_csv(csv_url)
    # ensure types
    df["Care homes beds"] = pd.to_numeric(df["Care homes beds"], errors='coerce')
    df["Publication Date"] = pd.to_datetime(df["Publication Date"], errors='coerce')
    # drop rows missing key fields
    return df.dropna(subset=[
        "Brand Name",
        "Care homes beds",
        "Location Inspection Directorate"
    ])

df = load_data()
# filter to Adult social care
df = df[df["Location Inspection Directorate"] == "Adult social care"]

# --- Sidebar filters ---
st.sidebar.header("🔍 Filters")

brands = ["All"] + sorted(df["Brand Name"].dropna().unique())
selected_brand = st.sidebar.selectbox("Brand (optional)", brands)

las = ["All"] + sorted(df["Location Local Authority"].dropna().unique())
selected_la = st.sidebar.selectbox("Local Authority (optional)", las)

beds = df["Care homes beds"].dropna()
min_b, max_b = int(beds.min()), int(beds.max())
bed_range = st.sidebar.slider("Bed Count", min_b, max_b, (min_b, max_b))

ratings = sorted(df["Location Latest Overall Rating"].dropna().unique())
selected_ratings = st.sidebar.multiselect("Rating", ratings, default=ratings)

# apply filters
f = df.copy()
if selected_brand != "All":
    f = f[f["Brand Name"] == selected_brand]
if selected_la != "All":
    f = f[f["Location Local Authority"] == selected_la]
f = f[
    f["Care homes beds"].between(bed_range[0], bed_range[1]) &
    f["Location Latest Overall Rating"].isin(selected_ratings)
]

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🏢 Brand Overview",
    "⭐ Ratings",
    "📅 Inspection Activity",
    "🗺️ Map View"
])

with tab1:
    st.title("🏢 Brand & Provider Overview")
    st.metric("Total Beds", f"{int(f['Care homes beds'].sum()):,}")
    st.metric("Total Providers", f["Provider Name"].nunique())
    st.metric("Total Locations", f["Location ID"].nunique())

    st.subheader("Provider Segmentation by Bed Count")
    pb = f.groupby("Provider Name")["Care homes beds"].sum().reset_index()
    st.write(f"🔹 ≤20 beds: {len(pb[pb['Care homes beds']<=20])}")
    st.write(f"🔹 21–100 beds: {len(pb[(pb['Care homes beds']>20)&(pb['Care homes beds']<=100)])}")
    st.write(f"🔹 >100 beds: {len(pb[pb['Care homes beds']>100])}")

    st.subheader("Top 10 Brands by Bed Share")
    tb = df.groupby("Brand Name")["Care homes beds"].sum().reset_index()
    tb["Market Share (%)"] = 100 * tb["Care homes beds"] / df["Care homes beds"].sum()
    st.dataframe(tb.sort_values("Care homes beds", ascending=False).head(10))

with tab2:
    st.title("⭐ Rating Overview")
    rc = f["Location Latest Overall Rating"].value_counts().rename_axis("Rating").reset_index(name="Count")
    rc["%"] = 100 * rc["Count"] / rc["Count"].sum()
    st.dataframe(rc)
    st.metric("% Good", f"{rc.loc[rc['Rating']=='Good','%'].iloc[0]:.1f}%" if 'Good' in rc['Rating'].values else "N/A")
    st.metric("% Outstanding", f"{rc.loc[rc['Rating']=='Outstanding','%'].iloc[0]:.1f}%" if 'Outstanding' in rc['Rating'].values else "N/A")

with tab3:
    st.title("📅 Recent Inspection Activity")
    ins = f.dropna(subset=["Publication Date"])
    by_month = ins["Publication Date"].dt.to_period("M").value_counts().sort_index().reset_index()
    by_month.columns = ["Month", "Count"]
    st.line_chart(by_month.set_index("Month"))

with tab4:
    st.title("🗺️ Map of Locations")
    m = folium.Map(location=[52.5, -1.5], zoom_start=6)
    for _, r in f.iterrows():
        lat, lon = r["Location Latitude"], r["Location Longitude"]
        if pd.notna(lat) and pd.notna(lon):
            folium.CircleMarker(
                [lat, lon],
                radius=min(r["Care homes beds"]/10, 10),
                fill=True, fill_opacity=0.6
            ).add_to(m)
    st_folium(m, width=900, height=600)
