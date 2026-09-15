import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

# ==========================================
# 0. CLOUDBEDS API CONFIGURATION (v1.3) & LIVE DASHBOARD INTEGRATION
# ==========================================
API_KEY = "cbat_slAB9mMYYxC3yRMvroRK7fnFD8fTyZOl"  
HEADERS = {
    "accept": "application/json",
    "x-api-key": API_KEY
}
BASE_URL = "https://api.cloudbeds.com/api/v1.3"

def fetch_dashboard_data():
    print("🔄 Connecting to Cloudbeds API v1.3 and pulling Dashboard payload...")
    try:
        response = requests.get(f"{BASE_URL}/getDashboard", headers=HEADERS)
        if response.status_code != 200:
            print(f"⚠️ Dashboard API Error: {response.status_code}. Switching to mock loop.")
            raise requests.exceptions.RequestException()
        json_data = response.json()
        data = json_data.get('data', {})
        if not data:
            raise ValueError("Empty data payload")
            
    except Exception:
        print("💡 Dashboard connection unavailable. Utilizing localized v1.3 schema mock engine...")
        data = {
            "property_now": "2026-07-11 21:00:00", 
            "roomsOccupied": 4, 
            "percentageOccupied": 80, 
            "inHouse": 3, 
            "guestsInHouse": 8, 
            "roomsBlocked": 0, 
            "capacity": 5
        }

    return {
        'capacity': data.get('capacity', 5),
        'rooms_blocked': data.get('roomsBlocked', 0),
        'in_house_rooms': data.get('inHouse', 0),
        'in_house_guests': data.get('guestsInHouse', 0),
        'live_today_occ': data.get('percentageOccupied', 0),
        'property_now_str': data.get('property_now', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    }

# Fetch Global Dashboard Metrics
DASH_METRICS = fetch_dashboard_data()
CAPACITY = DASH_METRICS['capacity']
ROOMS_BLOCKED = DASH_METRICS['rooms_blocked']
IN_HOUSE_ROOMS = DASH_METRICS['in_house_rooms']
IN_HOUSE_GUESTS = DASH_METRICS['in_house_guests']
LIVE_TODAY_OCC = DASH_METRICS['live_today_occ']
PROPERTY_NOW_STR = DASH_METRICS['property_now_str']

# ==========================================
# 1. CLOUDBEDS DATA ADAPTER LAYER (v1.3 API -> df_pace)
# ==========================================
def fetch_and_build_pace():
    print("🔄 Connecting to Cloudbeds API v1.3 and pulling reservation payload...")
    
    try:
        response = requests.get(f"{BASE_URL}/getReservations", headers=HEADERS)
        if response.status_code != 200:
            print(f"⚠️ API Error: {response.status_code} - {response.text}. Switching to mock loop for validation.")
            raise requests.exceptions.RequestException()
        json_data = response.json()
    except Exception:
        print("💡 API connection unavailable or token blank. Utilizing localized v1.3 schema mock engine...")
        mock_today = datetime.today().date()
        json_data = [
            {"reservationID": "1001", "dateCreated": f"{mock_today - timedelta(days=45)} 10:00:00", "status": "confirmed", "startDate": f"{mock_today + timedelta(days=5)}", "endDate": f"{mock_today + timedelta(days=7)}", "balance": 310.00},
            {"reservationID": "1002", "dateCreated": f"{mock_today - timedelta(days=20)} 14:32:11", "status": "confirmed", "startDate": f"{mock_today + timedelta(days=5)}", "endDate": f"{mock_today + timedelta(days=6)}", "balance": 155.00},
            {"reservationID": "1003", "dateCreated": f"{mock_today - timedelta(days=2)} 09:15:00", "status": "confirmed", "startDate": f"{mock_today + timedelta(days=10)}", "endDate": f"{mock_today + timedelta(days=12)}", "balance": 290.00},
            {"reservationID": "1004", "dateCreated": f"{mock_today - timedelta(days=380)} 18:22:00", "status": "checked_out", "startDate": f"{mock_today - timedelta(days=365) + timedelta(days=5)}", "endDate": f"{mock_today - timedelta(days=365) + timedelta(days=7)}", "balance": 0.00}
        ]

    parsed_reservations = []
    reservations_list = json_data.get('data', json_data) if isinstance(json_data, dict) else json_data
    
    for res in sorted(reservations_list, key=lambda x: x.get('startDate', '')):
        status = str(res.get('status', '')).lower().strip()
        if status not in ['confirmed', 'checked_in', 'checked_out']:
            continue
            
        res_id = res.get('reservationID')
        created_raw = res.get('dateCreated', '')
        created_date = pd.to_datetime(created_raw).date() if created_raw else datetime.today().date()
        
        start_date = pd.to_datetime(res.get('startDate')).date()
        end_date = pd.to_datetime(res.get('endDate')).date()
        
        parsed_reservations.append({
            "Reservation_ID": res_id,
            "Created_Date": created_date,
            "CheckIn_Date": start_date,
            "CheckOut_Date": end_date,
            "Status": status
        })
        
    df_res = pd.DataFrame(parsed_reservations)
    
    expanded_nights = []
    if not df_res.empty:
        for _, row in df_res.iterrows():
            current_stay_date = row['CheckIn_Date']
            while current_stay_date < row['CheckOut_Date']:
                expanded_nights.append({
                    "Stay_Date": current_stay_date,
                    "Created_Date": row['Created_Date']
                })
                current_stay_date += timedelta(days=1)
                
    df_nights = pd.DataFrame(expanded_nights)
    if not df_nights.empty:
        df_nights['Stay_Date'] = pd.to_datetime(df_nights['Stay_Date'])
        df_nights['Created_Date'] = pd.to_datetime(df_nights['Created_Date'])
        
    today = pd.to_datetime(datetime.today().date())
    future_dates = pd.date_range(today, periods=90)
    room_types = ['Standard', 'Premium']
    pace_rows = []
    
    for s_date in future_dates:
        for r_type in room_types:
            hist_adr = 135.0 if r_type == 'Standard' else 160.0
            
            if not df_nights.empty:
                current_otb = len(df_nights[df_nights['Stay_Date'] == s_date])
                lead_time_days = (s_date - today).days
                hist_stay_date = s_date - pd.DateOffset(years=1)
                hist_checkpoint_date = hist_stay_date - pd.DateOffset(days=lead_time_days)
                
                hist_pool = df_nights[df_nights['Stay_Date'] == hist_stay_date]
                hist_otb_at_leadtime = len(hist_pool[hist_pool['Created_Date'] <= hist_checkpoint_date])
            else:
                current_otb = 0
                hist_otb_at_leadtime = 0
                lead_time_days = (s_date - today).days
                
            # Dynamic Occupancy Pipeline (Fixing Day 0 Anomaly)
            if lead_time_days == 0:
                current_occ = LIVE_TODAY_OCC
            else:
                current_occ = (current_otb / CAPACITY) * 100
            
            pace_rows.append({
                'Stay_Date': s_date,
                'Room_Type': r_type,
                'Historical_ADR': float(hist_adr),
                'Current_Occupancy': round(current_occ, 2),
                'Current_OTB_Rooms': int(current_otb),
                'Hist_OTB_At_Same_LeadTime': int(max(1, hist_otb_at_leadtime)) 
            })
            
    print("✅ Cloudbeds v1.3 Adapter Layer successfully generated df_pace matrix.")
    return pd.DataFrame(pace_rows)

# ==========================================
# 2. RUN COUPLING DATA FETCH
# ==========================================
df_pace = fetch_and_build_pace()

today = pd.to_datetime(datetime.today().date())
dates = pd.date_range(today, periods=90).date
df_holidays = pd.DataFrame({
    'Date': [pd.to_datetime(dates[5]), pd.to_datetime(dates[12])], 
    'Event_Name': ['F1 Weekend Race', 'National Day Holiday'],
    'Holiday_Factor': [1.50, 1.25] 
})
df_comp = pd.DataFrame({
    'Date': pd.to_datetime(dates),
    'Competitor_ADR': np.random.uniform(125, 175, 90).round(2)
})

# ==========================================
# 3. OPTIMIZED RMS PRICING ENGINE 
# ==========================================
df_model = df_pace.copy()
df_model['Stay_Date'] = pd.to_datetime(df_model['Stay_Date'])
df_holidays['Date'] = pd.to_datetime(df_holidays['Date'])
df_comp['Date'] = pd.to_datetime(df_comp['Date'])

df_model = pd.merge(df_model, df_holidays, left_on='Stay_Date', right_on='Date', how='left')
df_model = pd.merge(df_model, df_comp, left_on='Stay_Date', right_on='Date', how='left')

df_model['Holiday_Factor'] = df_model['Holiday_Factor'].fillna(1.0)
df_model['Event_Name'] = df_model['Event_Name'].fillna('None')

def get_room_factor(room_type):
    return 1.25 if room_type == 'Premium' else 1.00
df_model['RoomType_Factor'] = df_model['Room_Type'].apply(get_room_factor)
df_model['Base_Room_ADR'] = df_model['Historical_ADR'] * df_model['RoomType_Factor']

df_model['Day_of_Week'] = df_model['Stay_Date'].dt.dayofweek
def get_business_weekend_factor(dow):
    if dow == 4: return 1.05   
    elif dow == 5: return 1.00 
    elif dow == 6: return 0.95 
    else: return 1.00          
df_model['Weekend_Factor'] = df_model['Day_of_Week'].apply(get_business_weekend_factor)

# OPTIMIZATION A: Net Availability Yielding (Effective Occupancy)
active_capacity = max(1, CAPACITY - ROOMS_BLOCKED)
df_model['Effective_Occupancy'] = (df_model['Current_OTB_Rooms'] / active_capacity) * 100

def get_occupancy_factor(occ):
    if occ < 40: return 0.90
    elif 40 <= occ < 60: return 1.00
    elif 60 <= occ < 80: return 1.10
    elif 80 <= occ < 90: return 1.20
    else: return 1.35

# Feeding Effective_Occupancy instead of raw Current_Occupancy
df_model['Occupancy_Factor'] = df_model['Effective_Occupancy'].apply(get_occupancy_factor)

def calculate_pace_ratio(row):
    current = row['Current_OTB_Rooms']
    hist = row['Hist_OTB_At_Same_LeadTime']
    if current == 0 and hist == 0: return 1.0
    if current > 0 and hist == 0: return 1.5 
    return current / hist
df_model['Pace_Ratio'] = df_model.apply(calculate_pace_ratio, axis=1)

def get_pace_factor(ratio):
    if ratio > 1.5: return 1.25
    elif 1.2 < ratio <= 1.5: return 1.15
    elif 1.0 < ratio <= 1.2: return 1.05
    elif 0.8 <= ratio <= 1.0: return 1.00
    else: return 0.90
df_model['Booking_Pace_Factor'] = df_model['Pace_Ratio'].apply(get_pace_factor)

df_model['Days_to_Checkin'] = (df_model['Stay_Date'] - pd.to_datetime(today)).dt.days
def get_lead_time_factor(row):
    days = row['Days_to_Checkin']
    occ = row['Current_Occupancy']
    if days <= 3 and occ < 40: return 0.85 
    if days > 30: return 0.95
    elif 14 <= days <= 30: return 1.00
    elif 7 <= days < 14: return 1.05
    elif 3 < days < 7: return 1.10
    else: return 1.15
df_model['Lead_Time_Factor'] = df_model.apply(get_lead_time_factor, axis=1)

df_model['Competitor_Ratio'] = df_model['Competitor_ADR'] / df_model['Base_Room_ADR']
def get_comp_factor(ratio):
    if pd.isna(ratio): return 1.00
    if ratio > 1.5: return 1.20
    elif ratio > 1.2: return 1.10
    elif ratio < 0.8: return 0.90
    else: return 1.00
df_model['Competitor_Factor'] = df_model['Competitor_Ratio'].apply(get_comp_factor)

# Base Recommended ADR Calculation
df_model['Recommended_ADR'] = (
    df_model['Base_Room_ADR'] * df_model['Weekend_Factor'] * df_model['Holiday_Factor'] * df_model['Occupancy_Factor'] * df_model['Lead_Time_Factor'] * df_model['Booking_Pace_Factor'] * df_model['Competitor_Factor']
)

# OPTIMIZATION B & C WRAPPERS
prop_hour = pd.to_datetime(PROPERTY_NOW_STR).hour
guest_density = (IN_HOUSE_GUESTS / IN_HOUSE_ROOMS) if IN_HOUSE_ROOMS > 0 else 0

def apply_advanced_optimizations(row):
    adr = row['Recommended_ADR']
    
    # Optimization B: Same-Day Time Decay
    if row['Days_to_Checkin'] == 0:
        if row['Effective_Occupancy'] < 100:
            if prop_hour >= 22:
                adr *= 0.85
            elif prop_hour >= 20:
                adr *= 0.90
            elif prop_hour >= 18:
                adr *= 0.95
        elif row['Effective_Occupancy'] >= 100:
            adr *= 1.05
            
    # Optimization C: Guest Density Overcharge Factor
    if guest_density > 2.5 and row['Effective_Occupancy'] >= 70:
        adr *= 1.04
        
    return adr

df_model['Recommended_ADR'] = df_model.apply(apply_advanced_optimizations, axis=1)

# Apply Boundaries & RevPAR
df_model['MIN_ADR'] = df_model['Base_Room_ADR'] * 0.7
df_model['MAX_ADR'] = df_model['Base_Room_ADR'] * 2.0
df_model['Final_ADR'] = df_model[['Recommended_ADR', 'MIN_ADR']].max(axis=1)
df_model['Final_ADR'] = df_model[['Final_ADR', 'MAX_ADR']].min(axis=1).round(0)
df_model['Expected_RevPAR'] = (df_model['Final_ADR'] * (df_model['Current_Occupancy'] / 100)).round(2)

def calculate_confidence(row):
    score = 50 
    if row['Current_Occupancy'] >= 80: score += 15
    elif row['Current_Occupancy'] >= 60: score += 5
    if row['Pace_Ratio'] >= 1.5: score += 15
    elif row['Pace_Ratio'] > 1.0: score += 5
    elif row['Pace_Ratio'] < 0.8: score -= 10 
    if row['Event_Name'] != 'None': score += 10
    comp_ratio = row['Competitor_Ratio']
    if pd.notna(comp_ratio) and comp_ratio > 1.1: score += 10
    if pd.notna(comp_ratio) and comp_ratio < 0.9: score += 10 
    return min(score, 100)

df_model['Confidence_Score'] = df_model.apply(calculate_confidence, axis=1)

# ==========================================
# 4. STANDARD TECHNICAL EXPORT (With Date Suffix)
# ==========================================
output_cols = [
    'Stay_Date', 'Room_Type', 'Day_of_Week', 'Event_Name', 'Days_to_Checkin', 
    'Current_Occupancy', 'Pace_Ratio', 'Base_Room_ADR', 'Competitor_ADR', 
    'Final_ADR', 'Expected_RevPAR', 'Confidence_Score'
]
df_dashboard = df_model[output_cols].copy()
df_dashboard['Stay_Date'] = df_dashboard['Stay_Date'].dt.date

date_suffix = datetime.today().strftime('%Y-%m-%d')
tech_filename = f"Garden_Pod_RMS_V2_Live_Dashboard_{date_suffix}.csv"

try:
    df_dashboard.to_csv(tech_filename, index=False)
    print(f"✅ Technical Scientist View updated: '{tech_filename}'")
except PermissionError:
    alternative_name = f"Garden_Pod_RMS_V2_Live_Dashboard_{date_suffix}_{datetime.today().strftime('%H%M%S')}.csv"
    df_dashboard.to_csv(alternative_name, index=False)
    print(f"⚠️ Warning: '{tech_filename}' is open in Excel! Saved to alternative file instead: '{alternative_name}'")

# ==========================================
# 5. ADD MANAGER DASHBOARD VIEW ENGINE (With Date Suffix)
# ==========================================
print("🚀 Initiating Manager Dashboard view compiling algorithm...")

# A. Calculate Percentage Spread Change
raw_pct_change = ((df_model['Final_ADR'] - df_model['Base_Room_ADR']) / df_model['Base_Room_ADR']) * 100
df_model['ADR_Change_vs_Base'] = raw_pct_change.apply(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")

# B. Determine Intelligent Demand Status Level
def evaluate_demand_status(row):
    occ = row['Current_Occupancy']
    pace = row['Pace_Ratio']
    if occ >= 90: status_idx = 3    
    elif occ >= 70: status_idx = 2  
    elif occ >= 40: status_idx = 1  
    else: status_idx = 0            
    if pace > 1.2:
        status_idx = min(status_idx + 1, 3)
    status_map = {0: "Low Demand", 1: "Normal Demand", 2: "High Demand", 3: "Peak Demand"}
    return status_map[status_idx]

df_model['Demand_Status'] = df_model.apply(evaluate_demand_status, axis=1)

# C. Formulate Tactical Action Command Calls
def assign_manager_action(pct_val):
    if pct_val >= 25.0: return "Raise Aggressively"
    elif pct_val >= 10.0: return "Raise Rate"
    elif pct_val > -10.0: return "Hold Rate"
    else: return "Discount"

df_model['Action'] = raw_pct_change.apply(assign_manager_action)

# D. Generate Operational Business Reason Narratives
def extract_business_reason(row):
    if row['Event_Name'] != 'None':
        return f"Event Demand Spike: {row['Event_Name']}"
    elif row['Holiday_Factor'] > 1.0:
        return "Holiday Demand Window Triggered"
    elif row['Current_Occupancy'] >= 80 and row['Pace_Ratio'] > 1.2:
        return "Peak Occupancy + Strong Booking Pace"
    elif row['Current_Occupancy'] < 40 and row['Pace_Ratio'] < 0.8:
        return "Low Occupancy + Weak Booking Pace"
    elif row['Competitor_Ratio'] > 1.25:
        return "High Competitor Pricing Observed"
    else:
        return "Market Conditions Stable"

df_model['Reason'] = df_model.apply(extract_business_reason, axis=1)

# E. Format Visual Percentage Fields
df_model['Current_Occupancy_Str'] = df_model['Current_Occupancy'].apply(lambda x: f"{int(round(x))}%")

# F. Structure Final Columns and Export
manager_cols = [
    "Stay_Date", "Room_Type", "Current_Occupancy_Str", "Final_ADR", 
    "ADR_Change_vs_Base", "Demand_Status", "Action", "Confidence_Score", "Reason"
]

df_manager_view = df_model[manager_cols].copy()
df_manager_view.rename(columns={"Current_Occupancy_Str": "Current_Occupancy"}, inplace=True)

df_manager_view['Stay_Date'] = df_manager_view['Stay_Date'].dt.date
df_manager_view.sort_values(by=['Stay_Date', 'Room_Type'], ascending=[True, True], inplace=True)

manager_filename = f"Garden_Pod_RMS_Manager_View_{date_suffix}.csv"

try:
    df_manager_view.to_csv(manager_filename, index=False)
    print(f"✅ Executive Operational View compiled successfully: '{manager_filename}'")
except PermissionError:
    alternative_mgr_name = f"Garden_Pod_RMS_Manager_View_{date_suffix}_{datetime.today().strftime('%H%M%S')}.csv"
    df_manager_view.to_csv(alternative_mgr_name, index=False)
    print(f"⚠️ Warning: '{manager_filename}' is open in Excel! Saved to alternative file instead: '{alternative_mgr_name}'")