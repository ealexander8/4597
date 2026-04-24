import streamlit as st
import pandas as pd

# --- THE SIMULATION LOGIC ---
class AgriEconSimulation:
    def __init__(self):
        self.world_food_price = 100.0
        self.domestic_price = 100.0
        self.population = 1000
        self.base_income = 50.0
        self.treasury = 5000.0
        self.environmental_health = 100.0 
        self.year = 1
        
        self.subsidy_rate = 0.0          
        self.tariff_rate = 0.0           
        self.fiscal_spending = 0.0       
        self.interest_rate = 0.05        
        self.public_goods_spending = 0.0 
        
        # Initialize history with a baseline Year 0
        self.history = [{
            "Year": 0, "Price": 100.0, "Demand": 5000.0, "Supply": 2500.0,
            "Imports": 2500.0, "Exports": 0.0, "Treasury": 5000.0, "Environment Score": 100.0
        }]

    def set_policies(self, subsidy, tariff, fiscal, monetary, public_goods):
        self.subsidy_rate = max(0.0, subsidy)
        self.tariff_rate = max(0.0, tariff)
        self.fiscal_spending = max(0.0, fiscal)
        self.interest_rate = max(0.01, monetary)
        self.public_goods_spending = max(0.0, public_goods)

    def simulate_year(self):
        # 1. Government Spending
        self.treasury -= (self.fiscal_spending + self.public_goods_spending)
        
        # 2. Demand Mechanics
        consumer_income = self.base_income + (self.fiscal_spending / self.population)
        interest_penalty = (self.interest_rate - 0.05) * 10 
        self.domestic_price = self.world_food_price * (1 + self.tariff_rate)
        quantity_demanded = max(0, 5000 - (20 * self.domestic_price) + (50 * consumer_income) - interest_penalty)
        
        # 3. Supply Mechanics
        infrastructure_bonus = self.public_goods_spending * 0.1
        quantity_supplied = max(0, 1000 + (15 * self.domestic_price) + (5000 * self.subsidy_rate) + infrastructure_bonus)
        
        self.treasury -= (quantity_supplied * self.subsidy_rate * 0.5)
        
        # 4. Trade & Revenue Mechanics
        net_trade = quantity_demanded - quantity_supplied
        imports = max(0, net_trade)
        exports = max(0, -net_trade)
        
        self.treasury += (imports * self.world_food_price * self.tariff_rate)
        self.treasury += ((consumer_income * self.population) * 0.15) # Tax revenue
        
        # 5. Environmental Impact
        production_degradation = quantity_supplied * 0.002
        mitigation = self.public_goods_spending * 0.005
        self.environmental_health = min(100.0, max(0.0, self.environmental_health - production_degradation + mitigation))
        
        # Record keeping
        report = {
            "Year": self.year,
            "Price": round(self.domestic_price, 2),
            "Demand": round(quantity_demanded, 2),
            "Supply": round(quantity_supplied, 2),
            "Imports": round(imports, 2),
            "Exports": round(exports, 2),
            "Treasury": round(self.treasury, 2),
            "Environment Score": round(self.environmental_health, 2)
        }
        self.history.append(report)
        self.year += 1

# --- STREAMLIT WEB APP INTERFACE ---

# Initialize the simulation in Streamlit's "session state" so it remembers data between clicks
if 'sim' not in st.session_state:
    st.session_state.sim = AgriEconSimulation()

st.set_page_config(page_title="Agri-Econ Simulator", layout="wide")

st.title("🌾 Agri-Econ Policy Simulator")
st.markdown("Take control of the nation's agricultural and economic policies. Balance the budget, feed the population, and protect the environment!")

# Layout: Left column for inputs, right column for graphs and outputs
col_inputs, col_charts = st.columns([1, 2])

with col_inputs:
    st.header("🏛️ Set Government Policy")
    st.markdown(f"**Current Year: {st.session_state.sim.year}**")
    
    subsidy_input = st.slider("Agricultural Subsidies (%)", min_value=0, max_value=100, value=0, help="Subsidizes production costs to boost domestic supply.") / 100.0
    tariff_input = st.slider("Import Tariffs (%)", min_value=0, max_value=100, value=0, help="Taxes imported food, raising domestic prices.") / 100.0
    monetary_input = st.slider("Interest Rate (%)", min_value=1, max_value=20, value=5, help="Higher rates slow the economy; lower rates stimulate borrowing and demand.") / 100.0
    
    fiscal_input = st.number_input("Fiscal Stimulus Spending ($)", min_value=0.0, max_value=5000.0, value=0.0, step=100.0, help="Direct payments to citizens to boost consumer income.")
    public_goods_input = st.number_input("Public Goods & Green Tech ($)", min_value=0.0, max_value=5000.0, value=0.0, step=100.0, help="Investments in infrastructure. Boosts supply efficiency and mitigates environmental damage.")
    
    if st.button("📈 Simulate Next Year", type="primary"):
        # Apply policies and advance the simulation
        st.session_state.sim.set_policies(subsidy_input, tariff_input, fiscal_input, monetary_input, public_goods_input)
        st.session_state.sim.simulate_year()
        st.rerun() # Refresh the page with new data

    if st.button("🔄 Reset Simulation"):
        st.session_state.sim = AgriEconSimulation()
        st.rerun()

with col_charts:
    # Convert history dictionary to a pandas DataFrame for easy charting
    history_df = pd.DataFrame(st.session_state.sim.history)
    history_df.set_index("Year", inplace=True)
    
    # Display Current Status as bold metrics
    st.header("📊 National Dashboard")
    latest = st.session_state.sim.history[-1]
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Treasury", f"${latest['Treasury']:,}")
    m2.metric("Environment Health", f"{latest['Environment Score']}/100")
    m3.metric("Domestic Food Price", f"${latest['Price']}")
    m4.metric("Net Imports", f"{latest['Imports']} units")
    
    st.divider()
    
    # Charts
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Supply vs. Demand")
        st.line_chart(history_df[['Supply', 'Demand']])
        
        st.subheader("Food Prices")
        st.line_chart(history_df[['Price']])
        
    with chart_col2:
        st.subheader("National Treasury")
        st.line_chart(history_df[['Treasury']], color="#2E8B57") # Green line
        
        st.subheader("Environmental Health")
        st.line_chart(history_df[['Environment Score']], color="#8B0000") # Red line