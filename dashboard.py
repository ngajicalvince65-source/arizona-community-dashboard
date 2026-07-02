
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import warnings
import os
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="Arizona Community Development Dashboard",
    page_icon="🗺️",
    layout="wide"
)

# Relative paths — works both locally and on Streamlit Cloud
BASE = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_data():
    unemp = pd.read_csv(os.path.join(BASE, "USA_Unemployment_data.csv"))
    az_u = unemp[(unemp["State"]=="Arizona") &
                 (unemp["Year"]==unemp[unemp["State"]=="Arizona"]["Year"].max()) &
                 (unemp["Month"]=="January")].copy()
    az_u["County_Name"] = az_u["County"].str.replace(" County","",regex=False).str.strip()

    edu   = pd.read_csv(os.path.join(BASE, "arizona_education.csv"))
    crime = pd.read_csv(os.path.join(BASE, "arizona_crime.csv"))

    counties = gpd.read_file(os.path.join(BASE, "tl_2023_us_county.shp"))
    az_c = counties[counties["STATEFP"]=="04"].copy().to_crs(epsg=4326)
    az_c["NAME"] = az_c["NAME"].str.strip()

    master = az_c.merge(az_u[["County_Name","Rate"]], left_on="NAME", right_on="County_Name", how="left")
    master = master.rename(columns={"Rate":"Unemployment_Rate"})
    master = master.merge(edu,   left_on="NAME", right_on="County", how="left")
    master = master.merge(crime, left_on="NAME", right_on="County", how="left")

    resources = gpd.read_file(os.path.join(BASE, "phoenix_community_resources.geojson"))
    res_clean = resources[["amenity","name","geometry"]].copy()
    res_clean["amenity"] = res_clean["amenity"].fillna("unknown")
    res_clean = res_clean.to_crs(epsg=4326)

    joined = gpd.sjoin(res_clean, master[["NAME","geometry"]], how="left", predicate="within")
    counts = joined.groupby("NAME").size().reset_index(name="Resource_Count")
    master = master.merge(counts, on="NAME", how="left")
    master["Resource_Count"] = master["Resource_Count"].fillna(0).astype(int)

    master["Vulnerability_Score"] = (
        master["Unemployment_Rate"].rank(ascending=True) +
        master["Less_than_HS_pct"].rank(ascending=True) +
        master["Violent_Crime_Rate"].rank(ascending=True) -
        master["Resource_Count"].rank(ascending=True)
    ).round(1)

    return master, res_clean

master, res_clean = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("Dashboard Filters")
all_counties = sorted(master["NAME"].dropna().tolist())
selected_counties = st.sidebar.multiselect("Select Counties", all_counties, default=all_counties)

layer = st.sidebar.radio(
    "Map Data Layer",
    ["Unemployment Rate","Vulnerability Score","Violent Crime Rate",
     "Less than HS Education %","Bachelors Degree %"]
)

show_resources = st.sidebar.checkbox("Show Community Resources on Map", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Data Sources**")
st.sidebar.markdown("- Bureau of Labor Statistics (2016)")
st.sidebar.markdown("- US Census ACS 2022")
st.sidebar.markdown("- OpenStreetMap (2026)")
st.sidebar.markdown("- FBI UCR Crime Estimates")

filtered = master[master["NAME"].isin(selected_counties)].copy()

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("Arizona Community Development Dashboard")
st.markdown("Explore unemployment, education, crime, and community resource access across Arizona counties.")

# ── KPI Row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Avg Unemployment Rate",    f"{filtered['Unemployment_Rate'].mean():.1f}%")
k2.metric("Avg Violent Crime Rate",   f"{filtered['Violent_Crime_Rate'].mean():.0f} per 100k")
k3.metric("Avg HS Graduate or Higher",f"{filtered['HS_graduate_pct'].mean():.1f}%")
k4.metric("Total Community Resources",f"{filtered['Resource_Count'].sum():,}")

st.markdown("---")

layer_col_map = {
    "Unemployment Rate":        ("Unemployment_Rate",        "YlOrRd"),
    "Vulnerability Score":      ("Vulnerability_Score",      "OrRd"),
    "Violent Crime Rate":       ("Violent_Crime_Rate",       "PuRd"),
    "Less than HS Education %": ("Less_than_HS_pct",         "YlOrBr"),
    "Bachelors Degree %":       ("Bachelors_or_higher_pct",  "BuGn"),
}
col_name, colorscale = layer_col_map[layer]

# ── Map + Bar ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader(f"Map: {layer}")
    m = folium.Map(location=[34.0, -111.5], zoom_start=6, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=filtered.__geo_interface__,
        data=filtered,
        columns=["NAME", col_name],
        key_on="feature.properties.NAME",
        fill_color=colorscale,
        fill_opacity=0.7,
        line_opacity=0.5,
        legend_name=layer,
        nan_fill_color="lightgrey"
    ).add_to(m)

    folium.GeoJson(
        filtered.__geo_interface__,
        style_function=lambda x: {"fillColor":"transparent","color":"#444","weight":1},
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME","Unemployment_Rate","Violent_Crime_Rate",
                    "Less_than_HS_pct","Resource_Count","Vulnerability_Score"],
            aliases=["County","Unemployment %","Violent Crime Rate",
                     "Less than HS %","Resources","Vulnerability Score"]
        )
    ).add_to(m)

    if show_resources:
        color_map = {"clinic":"blue","hospital":"red","school":"green",
                     "place_of_worship":"purple","unknown":"gray"}
        for _, row in res_clean[res_clean.geometry.notnull()].iterrows():
            amenity = row["amenity"]
            color   = color_map.get(amenity, "gray")
            name    = row["name"] if pd.notnull(row["name"]) else amenity
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=3, color=color, fill=True,
                fill_color=color, fill_opacity=0.6,
                tooltip=f"{amenity}: {name}"
            ).add_to(m)

    st_folium(m, width=700, height=480)

with col2:
    st.subheader("County Comparison")
    bar_df = filtered[["NAME", col_name]].dropna().sort_values(col_name, ascending=True)
    fig_bar = px.bar(
        bar_df, x=col_name, y="NAME", orientation="h",
        color=col_name, color_continuous_scale=colorscale,
        labels={col_name: layer, "NAME": "County"}, height=480
    )
    fig_bar.update_layout(showlegend=False, margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ── Scatter + Vulnerability ───────────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("Unemployment vs Education Gap")
    sdf = filtered.dropna(subset=["Less_than_HS_pct","Unemployment_Rate","Resource_Count"]).copy()
    sdf["size_col"] = sdf["Resource_Count"].clip(lower=1)
    fig_sc = px.scatter(
        sdf, x="Less_than_HS_pct", y="Unemployment_Rate",
        size="size_col", color="Vulnerability_Score",
        color_continuous_scale="OrRd", hover_name="NAME", size_max=40,
        labels={"Less_than_HS_pct":"Less than HS %",
                "Unemployment_Rate":"Unemployment Rate %",
                "size_col":"Resource Count"}
    )
    fig_sc.update_layout(margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig_sc, use_container_width=True)

with col4:
    st.subheader("Vulnerability Score by County")
    fig_vuln = px.bar(
        filtered.sort_values("Vulnerability_Score", ascending=False),
        x="NAME", y="Vulnerability_Score",
        color="Vulnerability_Score", color_continuous_scale="OrRd",
        labels={"NAME":"County","Vulnerability_Score":"Vulnerability Score"}
    )
    fig_vuln.update_layout(margin=dict(l=10,r=10,t=10,b=10), xaxis_tickangle=-45)
    st.plotly_chart(fig_vuln, use_container_width=True)

st.markdown("---")

# ── Data Table ────────────────────────────────────────────────────────────────
st.subheader("Underlying Data Table")
show_cols = ["NAME","Unemployment_Rate","Less_than_HS_pct","Bachelors_or_higher_pct",
             "Violent_Crime_Rate","Property_Crime_Rate","Resource_Count","Vulnerability_Score"]
display_df = filtered[show_cols].rename(columns={
    "NAME":"County","Unemployment_Rate":"Unemployment %",
    "Less_than_HS_pct":"Less than HS %","Bachelors_or_higher_pct":"Bachelors %",
    "Violent_Crime_Rate":"Violent Crime Rate","Property_Crime_Rate":"Property Crime Rate",
    "Resource_Count":"Resources","Vulnerability_Score":"Vulnerability Score"
}).sort_values("Vulnerability Score", ascending=False).reset_index(drop=True)

st.dataframe(display_df, use_container_width=True)
csv = display_df.to_csv(index=False).encode("utf-8")
st.download_button("Download Data as CSV", csv, "arizona_community_data.csv", "text/csv")

st.markdown("---")
st.caption("Dashboard developed for GCU Geospatial Computing | Data: BLS, Census ACS 2022, OpenStreetMap, FBI UCR")
