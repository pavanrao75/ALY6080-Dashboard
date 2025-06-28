#!/usr/bin/env python
# coding: utf-8

# In[1]:


import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_excel("dashboard_ready_scaled.xlsx")
    df['visit_count'] = pd.to_numeric(df['visit_count'], errors='coerce')
    df['huff_predicted_visits_scaled'] = pd.to_numeric(df['huff_predicted_visits_scaled'], errors='coerce')
    df['visits_gap_scaled'] = pd.to_numeric(df['visits_gap_scaled'], errors='coerce')
    return df.dropna(subset=['latitude', 'longitude', 'visit_count', 'huff_predicted_visits_scaled'])

df = load_data()

# --- Sidebar Filters ---
st.sidebar.title("Filters")
if 'cluster' in df.columns:
    cluster_options = sorted(df['cluster'].dropna().unique())
    selected_clusters = st.sidebar.multiselect("Select Cluster", cluster_options, default=cluster_options)
    df = df[df['cluster'].isin(selected_clusters)]

if 'income_group' in df.columns:
    income_options = [str(g) for g in df['income_group'].dropna().unique()]
    selected_income = st.sidebar.multiselect("Select Income Group", income_options, default=income_options)
    df = df[df['income_group'].astype(str).isin(selected_income)]

gap_min, gap_max = int(df['visits_gap_scaled'].min()), int(df['visits_gap_scaled'].max())
gap_range = st.sidebar.slider("Difference (Actual - Predicted):", gap_min, gap_max, (gap_min, gap_max))
df = df[(df['visits_gap_scaled'] >= gap_range[0]) & (df['visits_gap_scaled'] <= gap_range[1])]

# --- Page Title ---
st.title("Boston Grocery Store Mobility Dashboard")
st.markdown("""
Analyze and explore foot traffic data for Boston grocery stores, comparing actual visits to predictions from a spatial (Huff) model.
""")

# --- Dashboard Summary Metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Actual Visits", int(df['visit_count'].sum()))
col2.metric("Total Huff Predicted (Scaled)", int(df['huff_predicted_visits_scaled'].sum()))
col3.metric("Average Gap (Actual - Predicted)", round(df['visits_gap_scaled'].mean(), 1))

st.markdown("Negative gap: fewer visits than predicted; Positive gap: exceeds predictions.")

# --- Collapsible Help/Info Box ---
with st.expander("ℹ️ How to Use this Dashboard"):
    st.markdown("""
    - **Map**: Click markers for store details.
    - **Filters**: Focus on clusters, income, or gap.
    - **Bar/Scatter Plots**: Compare actual vs. predicted visits.
    - **Gap**: Indicates potential areas for improvement.
    - **Download**: Export data for analysis.
    """)

# --- Map Marker Colors + Legend ---
color_map = {0: "red", 1: "blue", 2: "green"}
st.markdown("""
**Map Marker Colors:**  
- <span style="color:red">Red</span>: Cluster 0  
- <span style="color:blue">Blue</span>: Cluster 1  
- <span style="color:green">Green</span>: Cluster 2  
""", unsafe_allow_html=True)

# --- Map Visualization ---
st.subheader("Store Map")
m = folium.Map(location=[df["latitude"].mean(), df["longitude"].mean()], zoom_start=12)
marker_cluster = MarkerCluster().add_to(m)
for _, row in df.iterrows():
    popup = f"""
    <b>{row['location_name']}</b><br>
    Actual Visits: {int(row['visit_count'])}<br>
    Huff Predicted (scaled): {round(row['huff_predicted_visits_scaled'], 1)}<br>
    Gap: {round(row['visits_gap_scaled'], 1)}<br>
    Cluster: {row.get('cluster', 'N/A')}<br>
    Income Group: {row.get('income_group', 'N/A')}
    """
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=6,
        color=color_map.get(row.get("cluster"), "gray"),
        fill=True,
        fill_opacity=0.7,
        popup=popup
    ).add_to(marker_cluster)
st_folium(m, width=700, height=500)

# --- Bar Chart: Highlighting Top 20 Stores ---
st.subheader("Top 20 Stores: Actual vs. Predicted Visits")
top_df = df.sort_values("visit_count", ascending=False).head(20)
fig = px.bar(top_df, x="location_name", y=["visit_count", "huff_predicted_visits_scaled"],
             barmode="group", labels={"value": "Visits", "variable": "Type"})
st.plotly_chart(fig, use_container_width=True)

# --- Scatter Plot ---
st.subheader("Actual vs. Predicted Visits (All Stores)")
scatter_fig = px.scatter(df, x="huff_predicted_visits_scaled", y="visit_count",
                         hover_name="location_name", color="cluster",
                         labels={"huff_predicted_visits_scaled": "Predicted Visits",
                                 "visit_count": "Actual Visits"}, opacity=0.7)
scatter_fig.add_shape(type="line", line=dict(dash="dash", color="gray"),
                      x0=0, y0=0, x1=df['huff_predicted_visits_scaled'].max(), y1=df['huff_predicted_visits_scaled'].max())
st.plotly_chart(scatter_fig, use_container_width=True)

# --- Categorize stores into actionable segments ---
df['abs_gap'] = df['visits_gap_scaled'].abs()
highlight_df = df.sort_values('abs_gap', ascending=False)

def categorize_gap(row):
    if row['visits_gap_scaled'] > 20:
        return 'Strong Performer'
    elif row['visits_gap_scaled'] < -20:
        return 'Opportunity Area'
    else:
        return 'On Target'

highlight_df['Performance Segment'] = highlight_df.apply(categorize_gap, axis=1)

# --- Display categorized table ---
st.subheader("Store Performance Opportunity Segments")

table_cols_segmented = [
    "location_name", "visit_count", "huff_predicted_visits_scaled", 
    "visits_gap_scaled", "Performance Segment", "cluster", "income_group", 
    "latitude", "longitude"
]

st.dataframe(
    highlight_df[table_cols_segmented].sort_values('visits_gap_scaled', ascending=False), 
    use_container_width=True
)

st.download_button(
    label="Download Segmented Data as CSV",
    data=highlight_df[table_cols_segmented].to_csv(index=False),
    file_name="boston_store_performance_segments.csv",
    mime="text/csv"
)

# --- Segment Explanations ---
st.markdown("""
**Performance Segment Definitions:**
- **Strong Performer:** Stores significantly exceed expected visits. Consider leveraging successful strategies.
- **On Target:** Stores meeting expectations; maintain current strategies.
- **Opportunity Area:** Stores significantly below predictions; investigate competition, pricing, or marketing.
""")


# --- Recommendations ---
st.subheader("Quick Business Recommendations")
st.markdown("""
- **Negative gaps**: Investigate marketing, competition, or local pricing.
- **Positive gaps**: Reinforce successful strategies.
""")

st.markdown("---")
st.markdown("**Data Source:** Advan Weekly Patterns, U.S. Census, Huff Model | Dashboard for Intelmatix strategic exploration.")


# In[ ]:




