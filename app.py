import streamlit as st
import pandas as pd
import random

# --- THE SIMULATION LOGIC ---
class AgriEconSimulation:
    def __init__(self):
        # Baseline Real-World Data (Modeled on Brazil 2024)
        self.gdp_per_capita = 10310.0
        self.population = 212.0  # In Millions
        self.treasury = 100000.0 # In Millions
        
        # Market Baselines
        self.world_food_price = 100.0
        self.domestic_price = 100.0
        self.environmental_health = 100.0 
        self.year = 1
        
        # Curve Intercepts
        self.demand_intercept = 350000.0 
        self.supply_intercept = 200000.0 
        self.supply_shock_multiplier = 1.0 # For temporary event shocks
        
        # Policy Variables
        self.subsidy_rate = 0.0          
        self.tariff_rate = 0.0           
        self.income_tax_rate = 0.15      # Baseline 15% income tax
        self.fiscal_spending = 0.0       
        self.interest_rate = 0.05        
        self.public_goods_spending = 0.0 

        # Initial Endogenous Variables
        self.elasticity = 0.54
        self.pop_growth = 0.0044
        self.income_growth = 0.02
        self.demand_growth_rate = 0.0
        
        # Event Tracking
        self.current_event = "Normal Year"
        self.current_event_desc = "No major global or ecological events."
        self.current_event_type = "neutral"
        
        self.history = []
        self._record_history(0, 100.0, 250000.0, 250000.0, 0.0, 0.0)

    def set_policies(self, subsidy, tariff, income_tax, fiscal, monetary, public_goods):
        self.subsidy_rate = max(0.0, subsidy)
        self.tariff_rate = max(0.0, tariff)
        self.income_tax_rate = max(0.0, income_tax)
        self.fiscal_spending = max(0.0, fiscal)
        self.interest_rate = max(0.01, monetary)
        self.public_goods_spending = max(0.0, public_goods)

    def trigger_events(self):
        # Reset temporary shocks from last year
        self.supply_shock_multiplier = 1.0
        
        # Slowly normalize world food price if it spiked previously
        if self.world_food_price > 100.0:
             self.world_food_price = max(100.0, self.world_food_price * 0.9)

        # 20% chance of a major event occurring
        if random.random() < 0.20:
            events = [
                {
                    "name": "☀️ Severe Drought", "type": "bad", 
                    "desc": "A massive regional drought has devastated crops. Domestic supply collapses by 30% this year.", 
                    "effect": "drought"
                },
                {
                    "name": "📉 Fertilizer Shortage", "type": "bad", 
                    "desc": "Global supply chains break down. World food prices spike by 50%!", 
                    "effect": "fertilizer"
                },
                {
                    "name": "🧬 Agritech Breakthrough", "type": "good", 
                    "desc": "Farmers adopt a new high-yield, drought-resistant crop. Base supply increases permanently by 10%.", 
                    "effect": "tech"
                },
                {
                    "name": "🚀 Economic Boom", "type": "good", 
                    "desc": "Global trade flourishes. The treasury receives a massive windfall of $50,000 Million from foreign investment.", 
                    "effect": "boom"
                }
            ]
            event = random.choice(events)
            self.current_event = event['name']
            self.current_event_desc = event['desc']
            self.current_event_type = event['type']
            
            # Apply the specific effects
            if event['effect'] == 'drought':
                self.supply_shock_multiplier = 0.70 
            elif event['effect'] == 'fertilizer':
                self.world_food_price *= 1.50 
            elif event['effect'] == 'tech':
                self.supply_intercept *= 1.10 
            elif event['effect'] == 'boom':
                self.treasury += 50000.0
        else:
            self.current_event = "Normal Year"
            self.current_event_desc = "No major global or ecological events occurred."
            self.current_event_type = "neutral"

    def simulate_year(self):
        # 1. Roll for random events before market calculations
        self.trigger_events()
        
        # 2. Update Macro Variables Endogenously
        self.elasticity = max(0.1, min(0.85, 0.85 - (0.00003 * self.gdp_per_capita)))
        self.pop_growth = max(0.001, min(0.03, 0.025 - (0.000002 * self.gdp_per_capita)))
        
        # --- Economic Growth Drivers & Drags ---
        stimulus_boost = (self.public_goods_spending / 100000.0) * 0.05 
        rate_penalty = (self.interest_rate - 0.05) * 0.2
        tax_penalty = (self.income_tax_rate - 0.15) * 0.1 # Increasing taxes beyond 15% slows down the economy
        
        self.income_growth = 0.02 + stimulus_boost - rate_penalty - tax_penalty

        # 3. Apply Food Equation for NEXT year's demand curve
        self.demand_growth_rate = self.pop_growth + (self.income_growth * self.elasticity)
        self.demand_intercept *= (1 + self.demand_growth_rate)
        
        self.population *= (1 + self.pop_growth)
        self.gdp_per_capita *= (1 + self.income_growth)

        # 4. Government Treasury Updates (Spending)
        self.treasury -= (self.fiscal_spending + self.public_goods_spending)
        
        # 5. Market Mechanics
        self.domestic_price = self.world_food_price * (1 + self.tariff_rate)
        
        # Demand Calculation
        interest_penalty = (self.interest_rate - 0.05) * 10000 
        quantity_demanded = max(0, self.demand_intercept - (1000 * self.domestic_price) - interest_penalty)
        
        # Environmental Feedback Loop on Supply
        yield_multiplier = min(1.0, self.environmental_health / 80.0)
        
        infrastructure_bonus = self.public_goods_spending * 2.0
        base_supply = max(0, self.supply_intercept + (500 * self.domestic_price) + (200000 * self.subsidy_rate))
        
        # Calculate final supply
        quantity_supplied = (base_supply * yield_multiplier * self.supply_shock_multiplier) + infrastructure_bonus
        
        # Subsidy cost applied to treasury
        self.treasury -= (quantity_supplied * self.subsidy_rate * 50)
        
        # 6. Trade & Revenue (Taxes + Tariffs)
        net_trade = quantity_demanded - quantity_supplied
        imports = max(0, net_trade)
        exports = max(0, -net_trade)
        
        tariff_revenue = (imports * self.world_food_price * self.tariff_rate)
        total_gdp = self.gdp_per_capita * self.population
        income_tax_revenue = (total_gdp * self.income_tax_rate) 
        
        self.treasury += (tariff_revenue + income_tax_revenue)
        
        # 7. Environmental Impact
        production_degradation = quantity_supplied * 0.0001
        mitigation = self.public_goods_spending * 0.002
        self.environmental_health = min(100.0, max(0.0, self.environmental_health - production_degradation + mitigation))
        
        self._record_history(self.year, self.domestic_price, quantity_demanded, quantity_supplied, imports, exports)
        self.year += 1

    def _record_history(self, yr, price, qd, qs, imp, exp):
        self.history.append({
            "Year": yr,
            "Price": round(price, 2),
            "Demand": round(qd, 2),
            "Supply": round(qs, 2),
            "Imports": round(imp, 2),
            "Exports": round(exp, 2),
            "Treasury": round(self.treasury, 2),
            "Environment Score": round(self.environmental_health, 2),
            "GDP per Capita": round(self.gdp_per_capita, 2),
            "Pop Growth %": round(self.pop_growth * 100, 3),
            "Elasticity": round(self.elasticity, 3),
            "Demand Growth %": round(self.demand_growth_rate * 100, 3)
        })

# --- STREAMLIT WEB APP INTERFACE ---
if 'sim' not in st.session_state:
    st.session_state.sim = AgriEconSimulation()

st.set_page_config(page_title="Agri-Econ Simulator", layout="wide")

st.title("🌾 Agri-Econ Policy Simulator")
st.markdown("Balance the budget, feed the population, and manage the macroeconomic transition of a developing nation!")

col_inputs, col_charts = st.columns([1, 2])

with col_inputs:
    st.header("🏛️ Government Policy")
    st.markdown(f"**Current Year: {st.session_state.sim.year}**")
    
    st.subheader("Taxes & Trade")
    tax_input = st.slider("Income Tax Rate (%)", min_value=0, max_value=50, value=15, help="Higher taxes generate more revenue but drag down GDP per capita growth.") / 100.0
    tariff_input = st.slider("Import Tariffs (%)", min_value=0, max_value=100, value=0) / 100.0
    
    st.subheader("Spending & Money Supply")
    subsidy_input = st.slider("Agricultural Subsidies (%)", min_value=0, max_value=100, value=0) / 100.0
    monetary_input = st.slider("Interest Rate (%)", min_value=1, max_value=20, value=5) / 100.0
    fiscal_input = st.number_input("Fiscal Stimulus ($ Millions)", min_value=0.0, max_value=50000.0, value=0.0, step=1000.0)
    public_goods_input = st.number_input("Public Goods & Tech ($ Millions)", min_value=0.0, max_value=50000.0, value=0.0, step=1000.0)
    
    if st.button("📈 Simulate Next Year", type="primary"):
        st.session_state.sim.set_policies(subsidy_input, tariff_input, tax_input, fiscal_input, monetary_input, public_goods_input)
        st.session_state.sim.simulate_year()
        st.rerun() 

    if st.button("🔄 Reset Simulation"):
        st.session_state.sim = AgriEconSimulation()
        st.rerun()

with col_charts:
    history_df = pd.DataFrame(st.session_state.sim.history)
    history_df.set_index("Year", inplace=True)
    latest = st.session_state.sim.history[-1]
    
    st.header("📊 National Dashboard")
    
    # Event Banner Display
    if st.session_state.sim.year > 1:
        if st.session_state.sim.current_event_type == "bad":
            st.error(f"**{st.session_state.sim.current_event}**\n\n{st.session_state.sim.current_event_desc}")
        elif st.session_state.sim.current_event_type == "good":
            st.success(f"**{st.session_state.sim.current_event}**\n\n{st.session_state.sim.current_event_desc}")
        else:
            st.info(f"**{st.session_state.sim.current_event}**\n\n{st.session_state.sim.current_event_desc}")

    # Environmental Warning Alert
    if latest['Environment Score'] < 80.0:
        st.warning(f"⚠️ **Ecological Crisis!** The environment score has dropped to {latest['Environment Score']}. Soil degradation and water scarcity are actively destroying crop yields.")
        
    macro1, macro2, macro3, macro4 = st.columns(4)
    macro1.info(f"**GDP per Capita:**\n${latest['GDP per Capita']:,.0f}")
    macro2.info(f"**Pop. Growth:**\n{latest['Pop Growth %']}%")
    macro3.info(f"**Income Elasticity:**\n{latest['Elasticity']}")
    macro4.info(f"**Demand Growth:**\n{latest['Demand Growth %']}%")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Treasury ($ Millions)", f"${latest['Treasury']:,.0f}")
    m2.metric("Environment Health", f"{latest['Environment Score']}/100")
    m3.metric("Domestic Food Price", f"${latest['Price']}")
    m4.metric("Net Imports (Units)", f"{latest['Imports']:,.0f}")
    
    st.divider()
    
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("Supply vs. Demand")
        st.line_chart(history_df[['Supply', 'Demand']])
    with chart_col2:
        st.subheader("Environmental Health")
        st.line_chart(history_df[['Environment Score']], color="#8B0000")
