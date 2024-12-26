"""
Kelompok DKP:
Dhafa Nur Fadhilah - 1301213263
Ratin Kani - 1301213269
Putri Maharani - 1301213093
"""
# Imports
import streamlit as st # type: ignore
import pandas as pd # type: ignore
import pydeck as pdk # type: ignore
import geopandas as gpd # type: ignore
import json # type: ignore
import plotly.express as px # type: ignore

# Settings for the Site
st.set_page_config(
    page_title="World Happiness Dashboard",
    page_icon=":world_map:",
    layout="wide"
)

# Title and subheader
st.title("Happiness Index: A Global Analysis")
st.markdown(
    """
    <div style="text-align: justify;font-size: 14px;    ">
    The data used in this analysis is sourced from <a href="https://worldhappiness.report/" target="_blank" style="color: blue;">https://worldhappiness.report/</a>.
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("<br>", unsafe_allow_html=True)  

# Load Happiness Dataset
@st.cache_data
def load_data(path: str):
    return pd.read_csv(path, delimiter=';')

df = load_data("happy.csv")
df['Happiness Score'] = pd.to_numeric(df['Happiness Score'], errors='coerce')

# Sidebar filters
st.sidebar.title("Filters")

regions = df['Country'].unique()
all_regions = ["All"] + list(regions)
selected_region = st.sidebar.selectbox("Select a Country:", all_regions)

if selected_region == "All":
    years = sorted(df['Year'].unique(), reverse=True)
else:
    years = sorted(df[df['Country'] == selected_region]['Year'].unique(), reverse=True)
all_years = ["All"] + [str(year) for year in years]
selected_year = st.sidebar.selectbox("Select a Year:", all_years)

# Make df copy of the filtered data
filtered_data = df.copy()
filtered_data_map = df.copy()

# Filter data based on selection
if selected_region != "All":
    filtered_data = filtered_data[filtered_data['Country'] == selected_region]
        
# Filter data based on selection for map
if selected_year != "All":
    filtered_data_map = filtered_data_map[filtered_data_map['Year'] == int(selected_year)]
else:
    filtered_data_map = (
        filtered_data_map.groupby("Alpha-3_code", as_index=False)
        .agg({"Happiness Score": "mean"})
    )
    
# Settings for the Interactive Map
# Load map shape dataset
@st.cache_data
def load_shapefile():
    return gpd.read_file("country_map/ne_110m_admin_0_countries.shp")

world = load_shapefile()
world = world.rename(columns={"SOV_A3": "Alpha-3_code"})
world = world[world['ADMIN'] != 'Greenland'] # Mistake in the world dataset where the Greenland is set to Denmark
merged = world.merge(filtered_data_map[['Alpha-3_code', 'Happiness Score']], on="Alpha-3_code", how="left")

def get_country_color(score):
    if pd.isna(score):
        return [255, 255, 255, 150]
    if score >= 7.5:
        return [41,192,43, 200]
    elif score >= 7.0:
        return [170,209,32, 200]
    elif score >= 5.0:
        return [255, 255, 0, 150]
    elif score >= 2.0:
        return [255, 165, 0, 150]
    else:
        return [255, 0, 0, 150]

merged['color'] = merged['Happiness Score'].apply(get_country_color)
merged['Happiness Score Display'] = merged['Happiness Score'].apply(lambda x: '-' if pd.isna(x) else x)

geojson_data = json.loads(merged.to_json())

geo_layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_data,
    get_fill_color="properties.color",
    get_line_color=[0, 0, 0],
    get_line_width=1,
    auto_highlight=True,
    pickable=True,
)

def get_country_bounds(country_name):
    country = world[world['NAME'] == country_name]
    if country.empty:
        return None
    else:
        bounds = country.bounds.iloc[0]
        return bounds

if selected_region != "All":
    bounds = get_country_bounds(selected_region)
    if bounds is not None:
        minx, miny, maxx, maxy = bounds
        lat_center = (miny + maxy) / 2
        lon_center = (minx + maxx) / 2
        zoom_level = 4
    else:
        lat_center, lon_center, zoom_level = df["latitude"].mean(), df["longitude"].mean(), 1
else:
    lat_center, lon_center, zoom_level = df["latitude"].mean(), df["longitude"].mean(), 0.4

view_state = pdk.ViewState(
    latitude=lat_center,
    longitude=lon_center,
    zoom=zoom_level,
    pitch=2,
    min_zoom=0.1,
    max_zoom=4,
)

map_style = {
    "style": "mapbox://styles/mapbox/light-v10",
    "accessToken": "your_mapbox_access_token"
}

tooltip_html = f"""
    <b>Country:</b> {{NAME}} ({selected_year if selected_year != "All" else "All Year"})<br>
    <b>Happiness Score:</b> {{Happiness Score Display}}
"""

deck = pdk.Deck(
    layers=[geo_layer],
    initial_view_state=view_state,
    map_style=map_style['style'],
    tooltip={"html": tooltip_html, "style": {"backgroundColor": "rgba(0, 0, 0, 0.7)", "color": "white"}}
)

# Inject custom CSS to make the table full width
st.markdown("""
    <style>
        .streamlit-expanderHeader {
            font-size: 16px;
            font-weight: bold;
        }
        .stDataFrame, .stTable {
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

with st.expander("Click to preview data table"):
    df_sorted = df.sort_values(by='Happiness Score', ascending=False).reset_index(drop=True)
    df_sorted.index += 1
    df_sorted['Year'] = df_sorted['Year'].apply(lambda x: f"{x:.0f}")
    df_sorted = df_sorted.drop(columns=['latitude', 'longitude'])
    st.dataframe(df_sorted, use_container_width=True)
    st.markdown(
        """
        <div style="text-align: justify;">
        The table above ranks countries based on their Happiness Score for all available years (2015-2024). 
        Finland consistently leads the rankings, showcasing the exceptional quality of life in Nordic countries. 
        The data highlights notable trends and shifts in happiness levels globally.
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)  
    
with st.expander("Click to preview ranking over time (2015-2024)"):
    # Ensure your DataFrame is sorted by 'Year' and 'Happiness Score' in descending order
    df['Rank'] = df.groupby('Year')['Happiness Score'].rank(method='first', ascending=False)

    # Filter the top 5 countries for each year based on the rank
    df_top_5 = df[df['Rank'] <= 5].copy()

    # Ensure correct sorting for animation
    df_top_5 = df_top_5.sort_values(by=['Year', 'Rank'])
    # Add colors for countries
    unique_countries = df_top_5['Country'].unique()
    color_map = {c: px.colors.qualitative.Plotly[i % 10] for i, c in enumerate(unique_countries)}

    # Generate animation frames
    frames = []
    years = sorted(df_top_5['Year'].unique())
    for year in years:
        year_data = df_top_5[df_top_5['Year'] == year].sort_values(by='Happiness Score', ascending=False)
        
        # Ensure 'text' column is created
        year_data = year_data.copy()  # Ensure we don't modify the original DataFrame
        year_data['text'] = "  " + year_data['Happiness Score'].round(2).astype(str)
        
        frame = dict(
            data=[ 
                dict(
                    type="bar",
                    x=year_data['Happiness Score'],
                    y=year_data['Country'],
                    orientation="h",
                    marker=dict(color=year_data['Country'].map(color_map)),
                    text=year_data['text'],  # Add text to display on bars
                    textposition='inside',  # Position text inside the bars
                    insidetextanchor='start',  # Ensure text is centered within the bar
                    textfont=dict(
                        family="Arial, sans-serif",
                        size=14,
                        color="white",  # Make the text white
                    ),
                )
            ],
            name=str(year),
            layout=dict(title=f"Top 5 Countries by Happiness Score in {year}"),
        )
        frames.append(frame)

    # Base figure
    fig = dict(
        data=[
            dict(
                type="bar",
                x=df_top_5[df_top_5['Year'] == years[0]]['Happiness Score'],
                y=df_top_5[df_top_5['Year'] == years[0]]['Country'],
                orientation="h",
                marker=dict(color=df_top_5[df_top_5['Year'] == years[0]]['Country'].map(color_map)),
                text="  " + df_top_5[df_top_5['Year'] == years[0]]['Happiness Score'].round(2).astype(str),
                textposition='inside',  # Text inside bars
                insidetextanchor='start',  # Center text within the bars
                textfont=dict(
                    family="Arial, sans-serif",
                    size=14,
                    color="white",  # Ensure text is white
                    weight="bold"
                ),
                hoverinfo='none', 
            )
        ],
        layout=dict(
            title="Top 5 Countries by Happiness Score in 2015",
            xaxis=dict(title="Happiness Score", range=[0, 8]),  # Set x-axis to start at 2
            yaxis=dict(
                title="Country", 
                categoryorder="array", 
                categoryarray=[], 
                autorange='reversed',  # Ensure the rank is displayed in ascending order (1 at the top)
            ),
            updatemenus=[
                dict(
                    type="buttons",
                    showactive=False,
                    x=0,  # Center the play button horizontally
                    y=-0.25,  # Position the button at the bottom
                    xanchor="center",
                    yanchor="bottom",
                    buttons=[
                        dict(
                            label="Play",
                            method="animate",
                            args=[None, dict(frame=dict(duration=2000, redraw=True), fromcurrent=True, loop=True)],
                        )
                    ],
                )
            ],
        ),
        frames=frames,
    )

    # Display in Streamlit
    st.plotly_chart(fig)
    st.markdown(
        """
        <div style="text-align: justify;">
        Above is an engaging animation displaying the evolution of the top 5 happiest countries  over the years. 
        Finland has held the top position since 2018, with Denmark and Iceland consistently maintaining their places in 
        the top 5. Switzerland, which ranked first in 2015, saw a gradual decline and fell out of the top 5 in 2019, 
        possibly due to the pandemic's impact. Although it made a comeback in 2020, it dropped out of the top 5 again in 
        2023 and has yet to return.
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)  
# Columns
colLinebar, colIMap = st.columns([1.4, 1.6])
colDropdown = st.columns(1)
colBarchart, colScatterplot = st.columns(2)


# Linebar
with colLinebar:
    if selected_region != "All":
        filtered_data = df[df['Country'] == selected_region]
        trend_data = filtered_data.sort_values(by='Year')
        fig = px.line(trend_data, x='Year', y='Happiness Score', title=f'Happiness Score Trend for {selected_region}')
        fig.update_layout(dragmode=False)
        st.plotly_chart(fig)
    else:
        avg_trend = df.groupby('Year')['Happiness Score'].mean().reset_index()
        fig = px.line(avg_trend, x='Year', y='Happiness Score', title="Happiness Score Trends (2015-2024)")
        fig.update_layout(dragmode=False)
        st.plotly_chart(fig)
    st.markdown(
        """
        <div style="text-align: justify;">
        A line chart tracking the average Happiness Scores of countries over the years.  The scores showed a steady rise 
        from 2017 until 2022, when they began to decline, potentially due to the rising inflation and cost of living crisis, 
        which placed significant financial stress on individuals and households worldwide.
        </div>
        """,
        unsafe_allow_html=True
    )

# Interactive Map
with colIMap:
    st.pydeck_chart(deck, height=400)
    st.markdown(
        """
        <div style="text-align: justify;">
        <br> <br>A color-coded world map displaying Happiness Scores, with five shades ranging from dark green (very high scores) to red 
        (very low scores). Afghanistan is the least happy country in 2024 (red zone), while Finland and other Nordic countries 
        are in the dark green zone with scores of 7.5 or higher, emphasizing their exceptional quality of life and well-being.
        </div>
        """,
        unsafe_allow_html=True
    )
# Dropdown
with colDropdown[0]:
    st.markdown("<br><br>", unsafe_allow_html=True)  
    dimensions = ['Economy (GDP per Capita)', 'Family (Social support)', 'Health (Life Expectancy)', 'Freedom to make life choices', 'Generosity', 'Trust (Government Corruption)']
    selected_dimension = st.selectbox("Select a Dimension to Compare with Happiness Score:", dimensions)


# Ranked Dimensions with Barchart
with colBarchart:
    filtered_data_barchart = filtered_data.copy()

    if selected_region != "All":
        if selected_year != "All":
            filtered_data_barchart = filtered_data_barchart[filtered_data['Year'] == int(selected_year)]
            suffix = f" in {selected_region} ({selected_year})"
        else:
            suffix = f" in {selected_region}"
    else:
        suffix = ""
    
    # Make a new df to calc the correlations and sort
    correlations = {
        dim: filtered_data_barchart[dim].iloc[0]
        if len(filtered_data_barchart) == 1 else filtered_data_barchart[dim].corr(filtered_data_barchart['Happiness Score']) 
        for dim in dimensions
    }
    correlation_df = pd.DataFrame(list(correlations.items()), columns=['Dimension', 'Correlation'])
    correlation_df['Percentage Impact'] = (correlation_df['Correlation'].abs() / correlation_df['Correlation'].abs().sum()) * 100
    correlation_df = correlation_df.sort_values(by='Percentage Impact', ascending=True)

    bar_title = f"Dimension Impact on Happiness Score{suffix}"
    bar_fig = px.bar(
        correlation_df,
        x='Percentage Impact',
        y='Dimension',
        title=bar_title,
        orientation='h',
        labels={'Percentage Impact': 'Percentage Impact (%)'},
        color_discrete_sequence=["#26c227"], 
        text='Percentage Impact',
    )
    bar_fig.update_traces(
        texttemplate='%{text:.2f}%',
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(family="Arial, sans-serif", size=14, color="white"),
    )
    correlation_df.loc[:, 'text_position'] = correlation_df['Percentage Impact'].apply(lambda value: 'inside' if value >= 7 else 'outside')
    correlation_df.loc[:, 'text_color'] = correlation_df['Percentage Impact'].apply(lambda value: 'white' if value >= 7 else 'black')
    bar_fig.update_traces(
        textposition=correlation_df['text_position'],
        textfont=dict(color=correlation_df['text_color']),
        hoverinfo='none'
    )
    st.plotly_chart(bar_fig)
    st.markdown(
        """
        <div style="text-align: justify;">
        This bar chart highlights the top contributors to happiness from the World Happiness Report. Economy (GDP per Capita) leads at 23.09%, 
        emphasizing the importance of financial stability. Health (Life Expectancy) follows at 22.02%, underlining the critical role of physical 
        well-being, while Family (Social Support) at 21.54% highlights the value of strong social connections. Together, these factors form the 
        foundation of societal happiness.
        </div>
        """,
        unsafe_allow_html=True
    )
    

# Scatter Plot
with colScatterplot:
    if selected_region != "All":
        region_suffix = f" in {selected_region}"
    else:
        region_suffix = ""
        
    filtered_data['Country - Year'] = filtered_data['Country'] + " (" + filtered_data['Year'].astype(str) + ")"
    scatter_title = f"Happiness Score vs {selected_dimension}{region_suffix}"
    scatter_fig = px.scatter(
        filtered_data,
        x=selected_dimension,
        y='Happiness Score',
        color='Happiness Score',
        hover_name='Country - Year',
        title=scatter_title,
        color_continuous_scale="Viridis"
    )
    st.plotly_chart(scatter_fig)
    st.markdown(
        """
        <div style="text-align: justify;">
        The scatter plot displays the relationship between happiness scores and the selected metric (e.g., Economy). Most metrics show a positive 
        correlation, meaning higher values lead to higher happiness. However, High happiness scores can still occur even when metrics like "Generosity" 
        and "Trust (Government Corruption)" are at lower levels. This may be because happiness in many countries is driven more by other factors like social 
        support, economic stability, and health, which can offset the impact of low generosity or high corruption.
        </div>
        """,
        unsafe_allow_html=True
    )
