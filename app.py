import streamlit as st
from streamlit_js_eval import get_geolocation
import mygeotab
import pandas as pd
import folium
from streamlit_folium import folium_static
from shapely.geometry import Point, Polygon
from geopy.distance import geodesic
import requests
from datetime import datetime

@st.cache
def load_data():
    file_path = 'shuttles.csv'
    shuttle_data = pd.read_csv(file_path)
    # Strip leading/trailing spaces from the relevant columns
    shuttle_data['Origin'] = shuttle_data['Origin'].str.strip()
    shuttle_data['Destination (Depot)'] = shuttle_data['Destination (Depot)'].str.strip()
    return shuttle_data

# Function to get user location
def get_user_location():
    location = get_geolocation()
    if location:
        st.session_state['user_lat'] = location['coords']['latitude']
        st.session_state['user_lon'] = location['coords']['longitude']

# Function to convert latitude and longitude to an address using Google Maps API
def reverse_geocode(lat, lon):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={st.secrets['google_maps_api_key']}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            return data['results'][0]['formatted_address']
    return "Unknown Location"

# Function to log visit details
def log_visit(address):
    current_time = datetime.now()
    log_entry = {
        "Date": current_time.strftime("%Y-%m-%d"),
        "Time": current_time.strftime("%H:%M:%S"),
        "Address": address
    }
    # Append the log entry to a CSV file
    log_file = 'visit_log.csv'
    
    # Check if the log file exists, otherwise create it with headers
    try:
        log_df = pd.read_csv(log_file)
    except FileNotFoundError:
        log_df = pd.DataFrame(columns=["Date", "Time", "Address"])

    # Add the new log entry
    log_df = log_df.append(log_entry, ignore_index=True)

    # Save the updated log file
    log_df.to_csv(log_file, index=False)
    
# Detect user location on load
get_user_location()

# Load shuttle data
shuttle_data = load_data()

# Add a header for the shuttle stop information
st.header("Nearest Shuttle Stop")

# Add a link to the static shuttle map
st.markdown("[Static Shuttle Map](https://shuttles-fall24.s3.us-east-1.amazonaws.com/nyc_shuttles_map.html)")


# Step 1: User selects the depot (destination)
destination = st.selectbox('Select your destination depot', shuttle_data['Destination (Depot)'].unique())

# Step 2: Filter shuttle stops for the selected depot (no "Depot" filtering applied)
filtered_shuttles = shuttle_data[shuttle_data['Destination (Depot)'] == destination]

# Step 3: Calculate distance to find the nearest shuttle stop
if 'user_lat' in st.session_state and 'user_lon' in st.session_state:
    user_location = (st.session_state['user_lat'], st.session_state['user_lon'])

    # Convert detected lat/long to a readable address
    detected_address = reverse_geocode(st.session_state['user_lat'], st.session_state['user_lon'])
    st.write(f"We detected your location as {detected_address}")

    def find_nearest_stop(row):
        try:
            stop_location = tuple(map(float, row['Locations longitude and latitude'].split(', ')))
            return geodesic(user_location, stop_location).miles
        except ValueError:
            # If there's an issue with the location data, return a large distance to exclude the stop
            return float('inf')

    # Calculate distances and find the nearest shuttle stop
    filtered_shuttles['Distance'] = filtered_shuttles.apply(find_nearest_stop, axis=1)
    
    if not filtered_shuttles.empty:
        nearest_shuttle = filtered_shuttles.sort_values('Distance').iloc[0]

        # Step 4: Output nearest shuttle stop details
        st.write(f"The nearest shuttle stop is **{nearest_shuttle['Origin']}**. It departs at **{nearest_shuttle['Pickup Times']}**. Make sure you are here by this time.")

        # Clean and fix Google Maps link formatting
        directions_url = f"https://www.google.com/maps/dir/?api=1&origin={st.session_state['user_lat']},{st.session_state['user_lon']}&destination={nearest_shuttle['Locations longitude and latitude']}&key={st.secrets['google_maps_api_key']}".replace(' ', '%20')
        st.markdown(f"[Click here for directions to this stop]({directions_url})")
    else:
        st.write("No shuttle stops found for the selected depot.")
else:
    st.write("Could not detect your location. Please enable location access and reload the app.")
