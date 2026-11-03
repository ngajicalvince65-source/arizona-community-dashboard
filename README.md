# Arizona Community Development Dashboard

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://arizona-community-dashboard-hcab45ufxwu2gaanyapp6i7.streamlit.app)

**Live dashboard:** https://arizona-community-dashboard-hcab45ufxwu2gaanyapp6i7.streamlit.app

```math
\begin{aligned}
&\textbf{Geospatial dashboard for Arizona's 15 counties} \\[4pt]
&V_c = \operatorname{rank}(\text{Unemployment}_c) + \operatorname{rank}(\text{Less than high school}_c) + \operatorname{rank}(\text{Violent crime}_c) - \operatorname{rank}(\text{Resources}_c) \\[4pt]
&\text{Higher } V_c \text{ means greater need and fewer community resources}
\end{aligned}
```

## Overview
A geospatial Streamlit dashboard that combines unemployment, education, crime and the location of community resources to compare development needs across Arizona counties. It joins tabular statistics to Census county boundaries, counts community resources inside each county with a spatial join, and ranks counties with a composite vulnerability score.

## Features
- **Choropleth map** (Folium) with five selectable layers: unemployment rate, vulnerability score, violent crime rate, share of adults without a high school diploma, and share with a bachelor's degree.
- **Community resources** plotted as points (clinics, hospitals, schools, places of worship) from OpenStreetMap.
- **County comparison** bar chart for the selected layer.
- **Unemployment against the education gap** scatter plot, sized by resource count and coloured by vulnerability.
- **Vulnerability ranking** of all counties.
- **County filter** and a downloadable data table.

## Geospatial processing
1. County boundaries come from the US Census TIGER/Line 2023 shapefile (downloaded automatically at first run) and are reprojected to WGS 84 (EPSG:4326).
2. Unemployment, education and crime tables are merged on county name.
3. Community resources are assigned to counties with a point-in-polygon spatial join (GeoPandas `sjoin`).
4. The vulnerability score above is computed from county ranks.

## Run locally
```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

## Data sources
- US Bureau of Labor Statistics, county unemployment rates
- US Census Bureau, American Community Survey 2022 (education) and TIGER/Line 2023 county boundaries
- FBI Uniform Crime Reporting, crime rate estimates
- OpenStreetMap, community resources in the Phoenix area

## Tools
Python, GeoPandas, Folium, streamlit-folium, Plotly, pandas, Streamlit

## Author
Ngaji Calvince Otieno
