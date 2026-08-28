import sys
import os
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QFormLayout, QLineEdit, QPushButton, QLabel, QGroupBox, QScrollArea, 
    QComboBox, QMessageBox, QFileDialog, QTabWidget
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import qdarkstyle

# Add parent directory to path so we can import backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.engine import HalfCatEngine

UNIT_CONV = {
    "Pressure": {
        "kPa": 1.0,
        "MPa": 1000.0,
        "bar": 100.0,
        "psi": 6.89475729
    },
    "Mass": {
        "kg": 1.0,
        "g": 0.001,
        "lbs": 0.45359237
    },
    "Length": {
        "m": 1.0,
        "cm": 0.01,
        "mm": 0.001,
        "in": 0.0254
    },
    "Area": {
        "m²": 1.0,
        "cm²": 1e-4,
        "mm²": 1e-6,
        "in²": 0.00064516
    }
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HalfCat-PySim")
        self.resize(1200, 800)
        
        self.engine = HalfCatEngine()
        
        self.is_dark_mode = True
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
        
        # Unit settings
        self.current_units = {
            "Pressure": "bar",
            "Mass": "kg",
            "Length": "mm",
            "Area": "mm²"
        }
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Build tabs
        self.sim_tab = QWidget()
        self.pref_tab = QWidget()
        
        self.tabs.addTab(self.sim_tab, "Simulation")
        self.tabs.addTab(self.pref_tab, "Preferences")
        
        self._build_sim_tab()
        self._build_pref_tab()
        
        self.last_results = None

    def _build_sim_tab(self):
        layout = QHBoxLayout(self.sim_tab)
        
        # Left Panel: Inputs
        left_panel = QScrollArea()
        left_panel.setWidgetResizable(True)
        left_panel.setMinimumWidth(400)
        
        input_widget = QWidget()
        self.input_layout = QVBoxLayout(input_widget)
        
        self.inputs = {}
        self.input_labels = {}
        
        # Store input metadata for unit conversions
        # Format: key: (default_val_in_internal_units, label_base, unit_category)
        self.input_metadata = {
            "P_N2O_tank_kPa": (4000.0, "N2O Pressure", "Pressure"),
            "m_ox_init_kg": (3.0, "Initial N2O Mass", "Mass"),
            "P_fu_tank_kPa": (4000.0, "Fuel Pressure", "Pressure"),
            "m_fu_init_kg": (1.0, "Initial Fuel Mass", "Mass"),
            "decay_liq": (0.7, "Liquid Decay Constant", None),
            "decay_gas": (0.25, "Gas Decay Constant", None),
            "timestep": (0.001, "Timestep (s)", None),
            "max_time": (10.0, "Max Time (s)", None),
            
            "CdA_ox_m2": (1e-5, "Oxidizer CdA", "Area"),
            "CdA_fu_m2": (1e-5, "Fuel CdA", "Area"),
            
            "d_t_m": (0.0254, "Throat Diameter", "Length"),
            "d_e_m": (0.0508, "Exit Diameter", "Length"),
            "P_amb_kPa": (101.325, "Ambient Pressure", "Pressure"),
            "c_star_eff": (0.85, "C* Efficiency", None),
            "nozzle_eff": (0.95, "Nozzle Efficiency", None)
        }
        
        self._create_input_group("Setup", ["P_N2O_tank_kPa", "m_ox_init_kg", "P_fu_tank_kPa", "m_fu_init_kg", "decay_liq", "decay_gas", "timestep", "max_time"])
        self._create_input_group("Fluid System", ["CdA_ox_m2", "CdA_fu_m2"])
        self._create_input_group("Thrust Chamber", ["d_t_m", "d_e_m", "P_amb_kPa", "c_star_eff", "nozzle_eff"])
        
        # Initialize UI values based on default units
        self.update_ui_values_to_current_units()
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Run Simulation")
        self.btn_run.clicked.connect(self.run_simulation)
        self.btn_theme = QPushButton("Toggle Theme")
        self.btn_theme.clicked.connect(self.toggle_theme)
        self.btn_export = QPushButton("Export .eng")
        self.btn_export.clicked.connect(self.export_eng)
        
        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_theme)
        btn_layout.addWidget(self.btn_export)
        
        self.input_layout.addLayout(btn_layout)
        self.input_layout.addStretch()
        
        left_panel.setWidget(input_widget)
        layout.addWidget(left_panel)
        
        # Right Panel: Plots
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.lbl_results = QLabel("Results will appear here.")
        self.lbl_results.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.lbl_results)
        
        self.plot_thrust = pg.PlotWidget(title="Thrust vs Time")
        self.plot_thrust.setLabel('left', 'Thrust', units='N')
        self.plot_thrust.setLabel('bottom', 'Time', units='s')
        self.plot_thrust.showGrid(x=True, y=True)
        right_layout.addWidget(self.plot_thrust)
        
        self.plot_pressure = pg.PlotWidget(title="Pressures vs Time")
        # Initialize label for pressure plot to match default pressure unit (we'll just use kPa for plot anyway to keep it simple, or maybe standard internal)
        # Actually it's easier to keep plots in standard SI (N, kPa, s)
        self.plot_pressure.setLabel('left', 'Pressure', units='kPa')
        self.plot_pressure.setLabel('bottom', 'Time', units='s')
        self.plot_pressure.showGrid(x=True, y=True)
        self.plot_pressure.addLegend()
        right_layout.addWidget(self.plot_pressure)
        
        layout.addWidget(right_panel, stretch=1)
        
    def _create_input_group(self, title, keys):
        group = QGroupBox(title)
        form = QFormLayout()
        
        for key in keys:
            line_edit = QLineEdit()
            label = QLabel()
            form.addRow(label, line_edit)
            self.inputs[key] = line_edit
            self.input_labels[key] = label
            
        group.setLayout(form)
        self.input_layout.addWidget(group)

    def _build_pref_tab(self):
        layout = QVBoxLayout(self.pref_tab)
        
        group = QGroupBox("Unit Preferences")
        form = QFormLayout()
        
        self.pref_combos = {}
        for category, units_dict in UNIT_CONV.items():
            combo = QComboBox()
            combo.addItems(list(units_dict.keys()))
            combo.setCurrentText(self.current_units[category])
            
            # Use a lambda with default arg to capture the category correctly
            combo.currentTextChanged.connect(lambda text, cat=category: self._on_unit_changed(cat, text))
            
            form.addRow(f"{category} Unit:", combo)
            self.pref_combos[category] = combo
            
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

    def _on_unit_changed(self, category, new_unit):
        old_unit = self.current_units[category]
        if old_unit == new_unit:
            return
            
        # Convert existing values in line edits
        for key, (_, _, cat) in self.input_metadata.items():
            if cat == category:
                try:
                    val_ui = float(self.inputs[key].text())
                    # convert ui value to internal base unit
                    internal_val = val_ui * UNIT_CONV[category][old_unit]
                    # convert internal base unit to new ui unit
                    new_val_ui = internal_val / UNIT_CONV[category][new_unit]
                    # formatting nicely
                    if new_val_ui == 0:
                        s_val = "0"
                    elif new_val_ui < 0.001 or new_val_ui > 1e6:
                        s_val = f"{new_val_ui:.6e}"
                    else:
                        s_val = f"{new_val_ui:.6g}".rstrip('0').rstrip('.') if '.' in f"{new_val_ui:.6g}" else f"{new_val_ui:.6g}"
                    self.inputs[key].setText(s_val)
                except ValueError:
                    pass # Keep as is if invalid
                    
        self.current_units[category] = new_unit
        self.update_ui_values_to_current_units(update_values=False)

    def update_ui_values_to_current_units(self, update_values=True):
        for key, (internal_val, label_base, cat) in self.input_metadata.items():
            if cat is not None:
                unit_str = self.current_units[cat]
                self.input_labels[key].setText(f"{label_base} ({unit_str})")
                
                if update_values:
                    factor = UNIT_CONV[cat][unit_str]
                    ui_val = internal_val / factor
                    self.inputs[key].setText(f"{ui_val:g}")
            else:
                self.input_labels[key].setText(label_base)
                if update_values:
                    self.inputs[key].setText(f"{internal_val:g}")

    def toggle_theme(self):
        if self.is_dark_mode:
            self.setStyleSheet("")
            self.is_dark_mode = False
        else:
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
            self.is_dark_mode = True

    def run_simulation(self):
        try:
            params = {}
            for key, (internal_val, label_base, cat) in self.input_metadata.items():
                ui_val = float(self.inputs[key].text())
                if cat is not None:
                    # convert to internal unit
                    factor = UNIT_CONV[cat][self.current_units[cat]]
                    params[key] = ui_val * factor
                else:
                    params[key] = ui_val
            
            df = self.engine.run_simulation(params)
            self.last_results = df
            
            self.plot_thrust.clear()
            self.plot_thrust.plot(df['Time'], df['Thrust'], pen=pg.mkPen('y', width=2))
            
            self.plot_pressure.clear()
            self.plot_pressure.plot(df['Time'], df['P_N2O'], pen=pg.mkPen('b', width=2), name="N2O Tank")
            self.plot_pressure.plot(df['Time'], df['P_fu'], pen=pg.mkPen('g', width=2), name="Fuel Tank")
            self.plot_pressure.plot(df['Time'], df['P_c'], pen=pg.mkPen('r', width=2), name="Chamber")
            
            total_impulse = np.trapz(df['Thrust'], df['Time'])
            burn_time = df['Time'].iloc[-1]
            max_thrust = df['Thrust'].max()
            
            self.lbl_results.setText(
                f"Burn Time: {burn_time:.2f} s | "
                f"Total Impulse: {total_impulse:.0f} Ns | "
                f"Peak Thrust: {max_thrust:.0f} N"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Simulation Error", str(e))

    def export_eng(self):
        if self.last_results is None or self.last_results.empty:
            QMessageBox.warning(self, "Export Error", "Run a simulation first!")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save .eng File", "", "OpenRocket Engine (*.eng)")
        if not file_path:
            return
            
        df = self.last_results
        
        # Simplify initial mass for the header
        m_ox_init = float(self.inputs['m_ox_init_kg'].text())
        m_fu_init = float(self.inputs['m_fu_init_kg'].text())
        if self.current_units["Mass"] != "kg":
            # Just approximate or leave it since it's just header
            # Let's use internal val
            factor = UNIT_CONV["Mass"][self.current_units["Mass"]]
            m_ox_init *= factor
            m_fu_init *= factor
            
        prop_mass = m_ox_init + m_fu_init
        
        try:
            with open(file_path, 'w') as f:
                f.write("; Generated by HalfCat-PySim\n")
                f.write(f"M_Custom 98 1000 0 {prop_mass:.3f} {prop_mass+2.0:.3f} HalfCat\n")
                
                for _, row in df.iterrows():
                    f.write(f"{row['Time']:.3f} {row['Thrust']:.2f}\n")
                    
            QMessageBox.information(self, "Export Success", f"Successfully exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.path)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
