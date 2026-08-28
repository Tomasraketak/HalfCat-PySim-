# HalfCat-PySim

A modern Python recreation of the HalfCat rocketry simulator, translating the original Excel-based hybrid/liquid rocket simulation into a standalone Python GUI.

## Features
- **Accurate Mathematics:** Re-implements the original timestep Euler integration for N2O blowdown, mass flow, and chamber pressure.
- **Modern UI:** Built with PyQt6 and PyQtGraph for real-time visualization.
- **Dark/Light Mode:** Toggleable user interface themes.
- **Export:** Easily export generated thrust curves to `.eng` format for use in OpenRocket or Rocksim.

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
4. **Excel Reference file:** Ensure `HalfCatSim_v1311.xlsx` is present in the root directory, as the simulation uses the N2O property tables from it.

## Running the Application
```bash
python main.py
```

## Tutorial
1. Launch the application.
2. On the **left panel**, you'll see parameters organized by:
   - **Setup:** Define initial tank pressures, propellant masses, timestep, and blowdown decay constants.
   - **Fluid System:** Define your Oxidizer and Fuel injector CdA.
   - **Thrust Chamber:** Define your throat and exit area, as well as efficiencies.
3. Click **Run Simulation**. The backend engine will integrate the state variables and plot the thrust and pressures over time.
4. **Analyze Results:** The top right panel will display the calculated Burn Time, Total Impulse, and Peak Thrust.
5. Click **Export .eng** to save the thrust curve for your flight simulations.

## Credits
The core mathematical model, equations, and property tables are based on **HalfCatSim**, originally created by **HalfCat Rocketry**. 
Visit their official website at [https://www.halfcatrocketry.com/halfcatsim](https://www.halfcatrocketry.com/halfcatsim) for the original Excel-based simulator, hardware documentation, and more hybrid rocketry resources. This Python project is an independent port designed to provide a native GUI experience.
