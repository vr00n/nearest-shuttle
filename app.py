import streamlit as st
from streamlit_js_eval import get_geolocation
import mygeotab
import pandas as pd
import folium
from streamlit_folium import folium_static
from shapely.geometry import Point, Polygon
from geopy.distance import geodesic

# Load shuttle data
@st.cache
def load_data():
    file_path = 'shuttles.csv'
    shuttle_data = pd.read_csv(file_path)
    return shuttle_data

# Function to get user location
def get_user_location():
    location = get_geolocation()
    if location:
        st.session_state['user_lat'] = location['coords']['latitude']
        st.session_state['user_lon'] = location['coords']['longitude']

# Detect user location on load
get_user_location()

# Load shuttle data
shuttle_data = load_data()

# Step 1: User selects the depot (destination)
destination = st.selectbox('Select your destination depot', shuttle_data['Destination (Depot)'].unique())

# Step 2: Filter shuttle stops for selected depot
filtered_shuttles = shuttle_data[shuttle_data['Destination (Depot)'] == destination]

# Step 3: Calculate distance to find nearest shuttle stop within 1 mile
if 'user_lat' in st.session_state and 'user_lon' in st.session_state:
    user_location = (st.session_state['user_lat'], st.session_state['user_lon'])

    def find_nearest_stop(row):
        stop_location = tuple(map(float, row['Locations longitude and latitude'].split(', ')))
        return geodesic(user_location, stop_location).miles

    filtered_shuttles['Distance'] = filtered_shuttles.apply(find_nearest_stop, axis=1)

    # Step 4: Check if there are any shuttle stops within 1 mile
    nearby_shuttles = filtered_shuttles[filtered_shuttles['Distance'] <= 1].sort_values('Distance')

    if not nearby_shuttles.empty:
        # If there are nearby shuttles, display the nearest one
        nearest_shuttle = nearby_shuttles.iloc[0]
        st.write(f"The nearest shuttle stop is {nearest_shuttle['Origin']}. It departs at {nearest_shuttle['Pickup Times AM']}. Make sure you are here by this time.")
        
        # Provide directions using Google Maps API
        directions_url = f"https://www.google.com/maps/dir/?api=1&origin={st.session_state['user_lat']},{st.session_state['user_lon']}&destination={nearest_shuttle['Locations longitude and latitude']}&key={st.secrets['google_maps_api_key']}"
        st.markdown(f"[Click here for directions]({directions_url})")
    else:
        # If no nearby shuttle stop is found
        st.write("No shuttle stops were found within a 1-mile radius of your current location.")
else:
    st.write("Could not detect your location. Please enable location access and reload the app.")
