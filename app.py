import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

# --- DATABASE CONNECTION ---
# We cache this so Streamlit doesn't constantly reconnect to Google on every click
@st.cache_resource
def get_db():
    creds_dict = json.loads(st.secrets["gcp_credentials"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    # MAKE SURE this perfectly matches the name of your Google Sheet
    return client.open("Agri-Econ Database")

db = get_db()
sheet_global = db.worksheet("Global")
sheet_countries = db.worksheet("Countries")
sheet_submissions = db.worksheet("Submissions")

# --- DATABASE INITIALIZATION ---
# If the sheets are empty, populate them with the starting sandbox data
def init_db():
    if len(sheet_global.get_all_values()) == 0:
        sheet_global.append_row(["Year", "World_Price"])
        sheet_global.append_row([1, 100.0])
        
    if len(sheet_countries.get_all_values()) == 0:
        headers = ["Country", "gdp", "pop", "treasury", "env", "base_supply", "base_demand"]
        sheet_countries.append_row(headers)
        initial_countries = [
            ["Agraria (High Income, Exporter)", 45000.0, 50.0, 500000.0, 100.0, 400000.0, 200000.0],
            ["Brazoria (Middle Income, Growing)", 10000.0, 200.0, 100000.0, 100.0, 200000.0, 350000.0],
            ["Caledon (High Income, Importer)", 55000.0, 80.0, 800000.0, 100.0, 50000.0, 300000.0],
            ["Deltaland (Low Income, Vulnerable)", 2500.0, 150.0, 20000.0, 100.0, 100000.0, 150000.0]
        ]
        sheet_countries.append_rows(initial_countries)
            
    if len(sheet_submissions.get_all_values()) == 0:
        sheet_submissions.append_row(["Country", "Year", "Tax", "Tariff", "Subsidy", "Monetary", "Fiscal", "Public_Goods"])

init_db()

# --- PULL CURRENT CLOUD DATA ---
global_data = sheet_global.get_all_records()
current_year = global_data[-1]["Year"]
current_world_price = global_data[-1]["World_Price"]

countries_data = sheet_countries.get_all_records()

# --- BULLETPROOF DATA CLEANER ---
# This forces any text with commas or dollar signs back into pure math numbers
for row in countries_data:
    for key in ["gdp", "pop", "treasury", "env", "base_supply", "base_demand"]:
        # We turn it into a string, strip out bad characters, and force it to be a float
        row[key] = float(str(row[key]).replace(',', '').replace('$', ''))

country_names = [c["Country"] for c in countries_data]

submissions_data = sheet_submissions.get_all_records()
# Filter to only look at submissions for the active year
current_submissions = {s["Country"]: s for s in submissions_data if s["Year"] == current_year}

# --- ROUTING & NAVIGATION ---
st.set_page_config(page_title="Global Agri-Econ Sim", layout="wide")
st.sidebar.title("🌍 Global Agri-Econ Sim")
role = st.sidebar.radio("Select Role:", ["Lobby", "Student (Country View)", "Teacher (Global Dashboard)"])

# --- SCREEN 1: LOBBY ---
if role == "Lobby":
    st.title("Welcome to the Global Economy")
    st.markdown("Please select your role from the sidebar to continue.")

# --- SCREEN 2: STUDENT VIEW ---
elif role == "Student (Country View)":
    st.title("🏛️ National Government Dashboard")
    country_choice = st.selectbox("Select your assigned country:", country_names)
    
    # Locate the active country's row in the database
    c_data = next((item for item in countries_data if item["Country"] == country_choice), None)
    
    # Check if they have already played this round
    if country_choice in current_submissions:
        st.success(f"✅ Policies for {country_choice} have been locked in for Year {current_year}. Please wait for the Teacher to resolve the global market.")
    else:
        st.markdown(f"### Current Status: Year {current_year}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Treasury", f"${c_data['treasury']:,.0f}M")
        m2.metric("GDP per Capita", f"${c_data['gdp']:,.0f}")
        m3.metric("Population", f"{c_data['pop']:,.0f}M")
        m4.metric("Environment", f"{c_data['env']}/100")
        
        st.info(f"🌐 **Current World Food Price:** ${current_world_price:,.2f} per unit")
        
        st.divider()
        st.subheader("Draft Next Year's Policies")
        
        col1, col2 = st.columns(2)
        with col1:
            tax = st.slider("Income Tax Rate (%)", 0, 50, 15) / 100.0
            tariff = st.slider("Import Tariffs (%)", 0, 100, 0) / 100.0
            subsidy = st.slider("Agricultural Subsidies (%)", 0, 100, 0) / 100.0
        with col2:
            monetary = st.slider("Interest Rate (%)", 1, 20, 5) / 100.0
            fiscal = st.number_input("Fiscal Stimulus ($ Millions)", 0.0, float(max(0, c_data['treasury'])), 0.0, step=1000.0)
            public_goods = st.number_input("Public Goods & Tech ($ Millions)", 0.0, float(max(0, c_data['treasury'])), 0.0, step=1000.0)
            
        if st.button("🔒 Lock in Policies", type="primary"):
            new_sub = [country_choice, current_year, tax, tariff, subsidy, monetary, fiscal, public_goods]
            sheet_submissions.append_row(new_sub)
            st.rerun()

# --- SCREEN 3: TEACHER VIEW ---
elif role == "Teacher (Global Dashboard)":
    st.title("👨‍🏫 Teacher Control Panel")
    st.markdown(f"**Current Year:** {current_year} | **World Food Price:** ${current_world_price:,.2f}")
    
    st.subheader("Submission Status")
    status_list = []
    for c in country_names:
        status = "✅ Submitted" if c in current_submissions else "❌ Waiting"
        status_list.append({"Country": c, "Status": status})
    st.dataframe(pd.DataFrame(status_list), use_container_width=True)
    
    ready_to_resolve = len(current_submissions) == len(country_names)
    
    if not ready_to_resolve:
        st.warning("Waiting for all countries to lock in their policies before resolving the year.")
    
    if st.button("⚖️ Resolve Year & Calculate Global Market", disabled=not ready_to_resolve, type="primary"):
        total_global_supply = 0
        total_global_demand = 0
        new_countries_data = []
        
        # 1. Process each country's internal economy using submitted policies
        for data in countries_data:
            name = data['Country']
            p = current_submissions[name]
            
            # Simple Macro updates
            elasticity = max(0.1, 0.85 - (0.00003 * data['gdp']))
            pop_growth = max(0.001, 0.025 - (0.000002 * data['gdp']))
            income_growth = 0.02 + ((p['Public_Goods']/100000)*0.05) - ((p['Monetary']-0.05)*0.2) - ((p['Tax']-0.15)*0.1)
            
            data['pop'] *= (1 + pop_growth)
            data['gdp'] *= (1 + income_growth)
            data['base_demand'] *= (1 + pop_growth + (income_growth * elasticity))
            data['treasury'] -= (p['Fiscal'] + p['Public_Goods'])
            
            # Calculate Supply and Demand at CURRENT world price
            domestic_price = current_world_price * (1 + p['Tariff'])
            
            yield_mult = min(1.0, data['env'] / 80.0)
            qs = ((data['base_supply'] + (500*domestic_price) + (200000*p['Subsidy'])) * yield_mult) + (p['Public_Goods']*2.0)
            qd = data['base_demand'] - (1000*domestic_price) - ((p['Monetary']-0.05)*10000)
            
            qs = max(0, qs)
            qd = max(0, qd)
            
            data['treasury'] -= (qs * p['Subsidy'] * 50) 
            data['treasury'] += (data['gdp'] * data['pop'] * p['Tax']) 
            
            data['env'] = min(100.0, max(0.0, data['env'] - (qs * 0.0001) + (p['Public_Goods'] * 0.002)))
            
            total_global_supply += qs
            total_global_demand += qd
            
            data['temp_qd'] = qd
            data['temp_qs'] = qs
            data['temp_tariff'] = p['Tariff']

        # 2. Calculate New World Price 
        net_global_difference = total_global_demand - total_global_supply
        price_adjustment = net_global_difference * 0.0001 
        new_world_price = max(10.0, min(500.0, current_world_price + price_adjustment))
        
        # 3. Finalize Trade and Tariff Revenue based on new price
        for data in countries_data:
            net_trade = data['temp_qd'] - data['temp_qs']
            imports = max(0, net_trade)
            data['treasury'] += (imports * new_world_price * data['temp_tariff'])
            
            # Format row for Google Sheets upload
            new_row = [data['Country'], data['gdp'], data['pop'], data['treasury'], data['env'], data['base_supply'], data['base_demand']]
            new_countries_data.append(new_row)
            
        # 4. Write new reality to Google Sheets
        sheet_countries.clear()
        sheet_countries.append_row(["Country", "gdp", "pop", "treasury", "env", "base_supply", "base_demand"])
        sheet_countries.append_rows(new_countries_data)
            
        sheet_global.append_row([current_year + 1, new_world_price])
        
        st.success(f"Year resolved! The new World Food Price is ${new_world_price:,.2f}.")
        st.rerun()
