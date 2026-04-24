import streamlit as st
import pandas as pd

# --- THE SIMULATED DATABASE ---
# In Phase 2, this will be replaced by a Google Sheet or Supabase connection.
def init_db():
    if 'global_year' not in st.session_state:
        st.session_state.global_year = 1
        st.session_state.world_price = 100.0
        
        # Initial baseline data for 4 distinct countries
        st.session_state.countries = {
            "Agraria (High Income, Exporter)": {"gdp": 45000, "pop": 50, "treasury": 500000, "env": 100, "base_supply": 400000, "base_demand": 200000},
            "Brazoria (Middle Income, Growing)": {"gdp": 10000, "pop": 200, "treasury": 100000, "env": 100, "base_supply": 200000, "base_demand": 350000},
            "Caledon (High Income, Importer)": {"gdp": 55000, "pop": 80, "treasury": 800000, "env": 100, "base_supply": 50000, "base_demand": 300000},
            "Deltaland (Low Income, Vulnerable)": {"gdp": 2500, "pop": 150, "treasury": 20000, "env": 100, "base_supply": 100000, "base_demand": 150000}
        }
        
        # Track who has submitted their turn
        st.session_state.submissions = {}
        st.session_state.history = []

if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# --- ROUTING & NAVIGATION ---
st.set_page_config(page_title="Global Agri-Econ Sim", layout="wide")

# Sidebar Navigation
st.sidebar.title("🌍 Global Agri-Econ Sim")
role = st.sidebar.radio("Select Role:", ["Lobby", "Student (Country View)", "Teacher (Global Dashboard)"])

# --- SCREEN 1: LOBBY ---
if role == "Lobby":
    st.title("Welcome to the Global Economy")
    st.markdown("Please select your role from the sidebar to continue.")
    st.info("💡 **How to test this prototype:**\n1. Go to the Student view and submit policies for all 4 countries.\n2. Go to the Teacher view and click 'Resolve Year'.\n3. Go back to the Student view to see the results!")

# --- SCREEN 2: STUDENT VIEW ---
elif role == "Student (Country View)":
    st.title("🏛️ National Government Dashboard")
    
    country_choice = st.selectbox("Select your assigned country:", list(st.session_state.countries.keys()))
    
    # Load country data
    c_data = st.session_state.countries[country_choice]
    
    # Check if they already submitted this year
    if country_choice in st.session_state.submissions:
        st.success(f"✅ Policies for {country_choice} have been locked in for Year {st.session_state.global_year}. Please wait for the Teacher to resolve the global market.")
    else:
        st.markdown(f"### Current Status: Year {st.session_state.global_year}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Treasury", f"${c_data['treasury']:,.0f}M")
        m2.metric("GDP per Capita", f"${c_data['gdp']:,.0f}")
        m3.metric("Population", f"{c_data['pop']:,.0f}M")
        m4.metric("Environment", f"{c_data['env']}/100")
        
        st.info(f"🌐 **Current World Food Price:** ${st.session_state.world_price:,.2f} per unit")
        
        st.divider()
        st.subheader("Draft Next Year's Policies")
        
        col1, col2 = st.columns(2)
        with col1:
            tax = st.slider("Income Tax Rate (%)", 0, 50, 15) / 100.0
            tariff = st.slider("Import Tariffs (%)", 0, 100, 0) / 100.0
            subsidy = st.slider("Agricultural Subsidies (%)", 0, 100, 0) / 100.0
        with col2:
            monetary = st.slider("Interest Rate (%)", 1, 20, 5) / 100.0
            fiscal = st.number_input("Fiscal Stimulus ($ Millions)", 0.0, float(c_data['treasury']), 0.0, step=1000.0)
            public_goods = st.number_input("Public Goods & Tech ($ Millions)", 0.0, float(c_data['treasury']), 0.0, step=1000.0)
            
        if st.button("🔒 Lock in Policies", type="primary"):
            st.session_state.submissions[country_choice] = {
                "tax": tax, "tariff": tariff, "subsidy": subsidy,
                "monetary": monetary, "fiscal": fiscal, "public_goods": public_goods
            }
            st.rerun()

# --- SCREEN 3: TEACHER VIEW ---
elif role == "Teacher (Global Dashboard)":
    st.title("👨‍🏫 Teacher Control Panel")
    st.markdown(f"**Current Year:** {st.session_state.global_year} | **World Food Price:** ${st.session_state.world_price:,.2f}")
    
    st.subheader("Submission Status")
    
    status_df = []
    for c in st.session_state.countries.keys():
        status = "✅ Submitted" if c in st.session_state.submissions else "❌ Waiting"
        status_df.append({"Country": c, "Status": status})
    st.dataframe(pd.DataFrame(status_df), use_container_width=True)
    
    ready_to_resolve = len(st.session_state.submissions) == len(st.session_state.countries)
    
    if not ready_to_resolve:
        st.warning("Waiting for all countries to lock in their policies before resolving the year.")
    
    if st.button("⚖️ Resolve Year & Calculate Global Market", disabled=not ready_to_resolve, type="primary"):
        total_global_supply = 0
        total_global_demand = 0
        
        # 1. Process each country's internal economy
        for name, data in st.session_state.countries.items():
            p = st.session_state.submissions[name]
            
            # Simple Macro updates
            elasticity = max(0.1, 0.85 - (0.00003 * data['gdp']))
            pop_growth = max(0.001, 0.025 - (0.000002 * data['gdp']))
            income_growth = 0.02 + ((p['public_goods']/100000)*0.05) - ((p['monetary']-0.05)*0.2) - ((p['tax']-0.15)*0.1)
            
            data['pop'] *= (1 + pop_growth)
            data['gdp'] *= (1 + income_growth)
            data['base_demand'] *= (1 + pop_growth + (income_growth * elasticity))
            
            data['treasury'] -= (p['fiscal'] + p['public_goods'])
            
            # Calculate Supply and Demand at CURRENT world price
            domestic_price = st.session_state.world_price * (1 + p['tariff'])
            
            yield_mult = min(1.0, data['env'] / 80.0)
            qs = ((data['base_supply'] + (500*domestic_price) + (200000*p['subsidy'])) * yield_mult) + (p['public_goods']*2.0)
            qd = data['base_demand'] - (1000*domestic_price) - ((p['monetary']-0.05)*10000)
            
            qs = max(0, qs)
            qd = max(0, qd)
            
            data['treasury'] -= (qs * p['subsidy'] * 50) # Pay for subsidies
            data['treasury'] += (data['gdp'] * data['pop'] * p['tax']) # Collect income tax
            
            # Environment
            data['env'] = min(100.0, max(0.0, data['env'] - (qs * 0.0001) + (p['public_goods'] * 0.002)))
            
            # Add to global pool
            total_global_supply += qs
            total_global_demand += qd
            
            # Save temporary states for trade resolution
            data['temp_qd'] = qd
            data['temp_qs'] = qs
            data['temp_tariff'] = p['tariff']

        # 2. Calculate New World Price (Basic Walrasian Auctioneer logic)
        # If supply > demand, price drops. If demand > supply, price rises.
        net_global_difference = total_global_demand - total_global_supply
        price_adjustment = net_global_difference * 0.0001 # Sensitivity factor
        
        # Apply bounds to prevent negative or infinite prices
        st.session_state.world_price = max(10.0, min(500.0, st.session_state.world_price + price_adjustment))
        
        # 3. Finalize Trade and Tariff Revenue based on new price
        for name, data in st.session_state.countries.items():
            net_trade = data['temp_qd'] - data['temp_qs']
            imports = max(0, net_trade)
            data['treasury'] += (imports * st.session_state.world_price * data['temp_tariff'])
            
        # 4. Advance Time
        st.session_state.submissions = {} # Clear submissions for next round
        st.session_state.global_year += 1
        
        st.success(f"Year resolved! The new World Food Price is ${st.session_state.world_price:,.2f}. Check the Student view.")
        st.rerun()

    if st.button("🔄 Hard Reset Simulation"):
        st.session_state.clear()
        st.rerun()
