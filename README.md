# HalfCat-PySim

A modern Python recreation of the HalfCat rocketry simulator, translating the original Excel-based hybrid/liquid rocket simulation into a standalone Python GUI.

## Core Functions & Simulation Engine
This application is driven by a native Python simulation engine (`backend/engine.py`) that handles the complex numerical methods previously done via spreadsheet rows:

*   **Timestep Euler Integration:** The engine simulates the motor firing by stepping forward in time (default `0.001s`). At each timestep, it recalculates fluid properties, flow rates, chamber pressure, and instantaneous thrust, integrating the changes in propellant mass.
*   **$N_2O$ Blowdown Modeling:** Accurately models the decay of Nitrous Oxide tank pressure. It first models the liquid phase volumetric decay (based on mass depletion) and transitions seamlessly to an exponential decay model for the gaseous tail-off.
*   **Dynamic Property Lookups:** Instead of hardcoded approximations, the engine uses `pandas` and `scipy.interpolate` to dynamically read and interpolate the actual thermodynamic fluid properties (density, viscosity, pressure) directly from the original HalfCatSim Excel tables during the firing sequence.
*   **Mass Flow & Thrust (Isentropic Flow):** Uses standard orifice equations ($m_{dot} = C_d A \sqrt{2 \rho \Delta P}$) for both fuel and oxidizer to calculate chamber pressure ($P_c = \eta_{c*} c^* \dot{m} / A_t$) and ideal thrust coefficients ($C_f$) based on theoretical characteristic velocity ($c^*$) and specific heat ratios ($\gamma$).

## GUI Features
*   **Interactive Simulation Dashboard:** Built with `PyQt6` and `pyqtgraph`. Parameter tweaks on the left pane instantly reflect on the Thrust and Pressure visualizations upon running.
*   **Unit Preferences:** A dedicated **Preferences** tab allows you to switch your display units globally. You can choose between `bar`, `kPa`, `MPa`, or `psi` for pressures, and toggle lengths between `mm`, `cm`, `in`, and `m`. The GUI automatically scales and mathematically converts your inputs to standard internal SI units for the physics engine, ensuring the math stays accurate while providing a friendly interface.
*   **Dark/Light Mode:** Toggleable user interface themes using `qdarkstyle`.
*   **Export `.eng` Files:** With a single click, extract your simulated thrust curve into the `.eng` standard format. This allows you to import your simulated motor directly into OpenRocket or Rocksim to simulate flight apogee and stability.

## Setup Instructions

1. **Prerequisites:** Ensure you have Python 3.9+ installed.
2. **Clone the repository:**
   ```bash
   git clone https://github.com/Tomasraketak/HalfCat-PySim-.git
   cd HalfCat-PySim-
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Excel Reference file:** Ensure `HalfCatSim_v1311.xlsx` is present in the root directory. The Python backend reads this file dynamically to build its interpolation tables for the oxidizer and fuel properties.

## Running the Application
```bash
python main.py
```

## How to Use
1. Launch the application.
2. Visit the **Preferences** tab first to set your comfortable working units (e.g., configuring pressure to `psi` and lengths to `in`).
3. On the **Simulation** tab, define your motor geometry:
   - **Setup:** Initial tank pressures, initial propellant masses, integration timestep, and decay constants.
   - **Fluid System:** Define your Oxidizer and Fuel injector flow area ($C_d A$).
   - **Thrust Chamber:** Define your nozzle throat and exit diameters, as well as efficiencies.
4. Click **Run Simulation**. The backend engine will integrate the state variables and plot the thrust and pressures over time.
5. **Analyze Results:** The top right panel will display the calculated Burn Time, Total Impulse, and Peak Thrust.
6. Click **Export .eng** to save the thrust curve to a file.

## Credits
The core mathematical model, equations, and property tables are based on **HalfCatSim**, originally created by **HalfCat Rocketry**. 
Visit their official website at [https://www.halfcatrocketry.com/halfcatsim](https://www.halfcatrocketry.com/halfcatsim) for the original Excel-based simulator, hardware documentation, and more hybrid rocketry resources. This Python project is an independent port designed to provide a native GUI experience.
