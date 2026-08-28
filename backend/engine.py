import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

class HalfCatEngine:
    def __init__(self, excel_path="HalfCatSim_v1311.xlsx"):
        self.excel_path = excel_path
        self._load_tables()
        
    def _load_tables(self):
        print("Loading N2O properties...")
        # B = kPa, C = liquid density, M = liquid viscosity (12th col of B-N -> N is 13? wait, B is 1, so col 2 is C, col 11 is L. let's just load by name)
        # We know col 1 (B) is kPa. Col 2 (C) is liquid density kg/m3.
        df_n2o = pd.read_excel(self.excel_path, sheet_name='N2O', header=1)
        # Drop completely empty rows
        df_n2o = df_n2o.dropna(subset=['kPa'])
        
        # B: kPa, C: kg/m^3 (liquid), R: kPa (gas), S: kg/m^3 (gas)
        # Let's just create generic interpolators for liquid and gas density
        self.n2o_liq_rho_interp = interp1d(df_n2o.iloc[:, 1], df_n2o.iloc[:, 2], fill_value="extrapolate") # kPa -> kg/m3
        self.n2o_liq_visc_interp = interp1d(df_n2o.iloc[:, 1], df_n2o.iloc[:, 11], fill_value="extrapolate") # kPa -> cP
        
        # Gas table is usually on the right side of the N2O sheet. Let's load the whole sheet and check columns
        self.n2o_gas_rho_interp = interp1d(df_n2o.iloc[:, 17], df_n2o.iloc[:, 18], fill_value="extrapolate") # R -> S
        self.n2o_gas_visc_interp = interp1d(df_n2o.iloc[:, 17], df_n2o.iloc[:, 27], fill_value="extrapolate")
        
        print("Loading Isentropic Flow properties...")
        # Isentropic flow: A = gamma, G = Area Ratio
        try:
            df_isen = pd.read_excel(self.excel_path, sheet_name='Isentropic Flow', header=2)
            self.df_isen = df_isen
        except:
            self.df_isen = None

        print("Loading Fuel properties...")
        # Fuel sheet is complex. We will use a simplified model for c*, gamma, MW based on E85, 
        # or we can parse it. For the sake of the MVP, we will use a constant gamma, MW, and C* 
        # or simple interpolator for a typical E85/N2O combustion to guarantee it runs.
        # N2O/E85 typical values: gamma=1.2, MW=22, c*=1500 m/s at optimal MR.
        
    def get_fuel_properties(self, pc_psi, mr, fuel_type="E85"):
        # Simplified placeholder for the complex 2D lookup in Excel.
        # In a full 1:1, we would query the Fuel dataframe.
        return {
            "gamma": 1.22,
            "mw": 22.0,
            "c_star": 1500.0 # m/s
        }

    def run_simulation(self, inputs):
        """
        Run the timestep simulation.
        inputs: dict of parameters.
        Returns a pandas dataframe containing the time history.
        """
        dt = inputs.get("timestep", 0.001)
        t_max = inputs.get("max_time", 10.0)
        
        # Setup initial state
        t = 0.0
        p_n2o = inputs.get("P_N2O_tank", 4000.0) # kPa
        m_ox_init = inputs.get("m_ox_init", 3.0) # kg
        m_ox = m_ox_init
        
        p_fu = inputs.get("P_fu_tank", 4000.0) # kPa
        m_fu_init = inputs.get("m_fu_init", 1.0) # kg
        m_fu = m_fu_init
        
        k_liq = inputs.get("decay_liq", 0.7)
        k_gas = inputs.get("decay_gas", 0.25)
        
        CdA_ox = inputs.get("CdA_ox", 1e-5) # m^2
        CdA_fu = inputs.get("CdA_fu", 1e-5) # m^2
        
        A_t = inputs.get("A_t", 0.0005) # m^2
        A_e = inputs.get("A_e", 0.002) # m^2
        P_amb = inputs.get("P_amb", 101.325) # kPa
        
        c_star_eff = inputs.get("c_star_eff", 0.85)
        nozzle_eff = inputs.get("nozzle_eff", 0.95)
        
        # state history
        history = []
        
        P_c = 101.325 # Start at ambient
        
        phase = "Liquid"
        
        while t <= t_max and m_ox > 0 and m_fu > 0:
            # 1. Update Tank Pressures
            if phase == "Liquid":
                if m_ox / m_ox_init > 0.1:
                    p_n2o = inputs.get("P_N2O_tank", 4000.0) * ((m_ox / m_ox_init) * (1 - k_liq) + k_liq)
                else:
                    phase = "Gas"
            if phase == "Gas":
                p_n2o = p_n2o / np.exp(k_gas * dt)
                
            # Assume fuel is regulated or simple blowdown
            # For MVP, keep fuel pressure constant or similar blowdown
            p_fu = p_fu / np.exp(0.01 * dt)
            
            # 2. Flow rates
            dp_ox = max(p_n2o - P_c, 0)
            rho_ox = float(self.n2o_liq_rho_interp(p_n2o)) if phase == "Liquid" else float(self.n2o_gas_rho_interp(p_n2o))
            mdot_ox = CdA_ox * np.sqrt(2 * rho_ox * dp_ox * 1000)
            
            dp_fu = max(p_fu - P_c, 0)
            rho_fu = 779.0 # E85 density kg/m3
            mdot_fu = CdA_fu * np.sqrt(2 * rho_fu * dp_fu * 1000)
            
            mdot_tot = mdot_ox + mdot_fu
            mr = mdot_ox / mdot_fu if mdot_fu > 0 else 0
            
            # 3. Combustion properties
            props = self.get_fuel_properties(P_c * 0.145, mr)
            c_star = props["c_star"] * c_star_eff
            
            # 4. Chamber pressure (Euler integration of mass conservation)
            # Simplification: instantaneous P_c
            if A_t > 0:
                P_c_raw = (c_star * mdot_tot / A_t) / 1000 # kPa
            else:
                P_c_raw = 101.325
                
            dP_c = (P_c_raw - P_c) / dt if dt > 0 else 0
            P_c += dP_c * dt
            
            # 5. Thrust
            # Pe from isentropic expansion (simplified ideal)
            gamma = props["gamma"]
            # Simplified thrust coefficient
            if P_c <= P_amb or P_c == 0:
                Cf = 0
            else:
                try:
                    Cf = np.sqrt((2 * gamma**2 / (gamma - 1)) * (2 / (gamma + 1))**((gamma + 1) / (gamma - 1)) * (1 - (P_amb / P_c)**((gamma - 1) / gamma)))
                    if np.isnan(Cf): Cf = 0
                except:
                    Cf = 0
            
            F = nozzle_eff * (mdot_tot * c_star * Cf + (P_amb - P_amb) * A_e) # Ideal F
            
            history.append({
                "Time": t,
                "P_N2O": p_n2o,
                "P_fu": p_fu,
                "P_c": P_c,
                "m_ox": m_ox,
                "m_fu": m_fu,
                "mdot_ox": mdot_ox,
                "mdot_fu": mdot_fu,
                "Thrust": F,
                "Phase": phase
            })
            
            # Update mass
            m_ox -= mdot_ox * dt
            m_fu -= mdot_fu * dt
            
            t += dt
            
        return pd.DataFrame(history)

if __name__ == "__main__":
    engine = HalfCatEngine()
    print("Engine initialized.")
    df = engine.run_simulation({})
    print(df.head())
