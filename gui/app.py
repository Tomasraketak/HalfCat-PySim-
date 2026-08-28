import sys
import os
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QFormLayout, QLineEdit, QPushButton, QLabel, QGroupBox, QScrollArea, QComboBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import qdarkstyle

# Add parent directory to path so we can import backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.engine import HalfCatEngine

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HalfCat-PySim")
        self.resize(1200, 800)
        
        self.engine = HalfCatEngine()
        
        self.is_dark_mode = True
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QHBoxLayout(main_widget)
        
        # Left Panel: Inputs
        left_panel = QScrollArea()
        left_panel.setWidgetResizable(True)
        left_panel.setMinimumWidth(400)
        
        input_widget = QWidget()
        self.input_layout = QVBoxLayout(input_widget)
        
        self.inputs = {}
        
        self._create_input_group("Setup", {
            "P_N2O_tank_bar": ("40.0", "N2O Pressure (bar)"),
            "m_ox_init": ("3.0", "Initial N2O Mass (kg)"),
            "P_fu_tank_bar": ("40.0", "Fuel Pressure (bar)"),
            "m_fu_init": ("1.0", "Initial Fuel Mass (kg)"),
            "decay_liq": ("0.7", "Liquid Decay Constant"),
            "decay_gas": ("0.25", "Gas Decay Constant"),
            "timestep": ("0.001", "Timestep (s)"),
            "max_time": ("10.0", "Max Time (s)")
        })
        
        self._create_input_group("Fluid System", {
            "CdA_ox_mm2": ("10.0", "Oxidizer CdA (mm²)"),
            "CdA_fu_mm2": ("10.0", "Fuel CdA (mm²)")
        })
        
        self._create_input_group("Thrust Chamber", {
            "d_t_mm": ("25.4", "Throat Diameter (mm)"),
            "d_e_mm": ("50.8", "Exit Diameter (mm)"),
            "P_amb_bar": ("1.013", "Ambient Pressure (bar)"),
            "c_star_eff": ("0.85", "C* Efficiency"),
            "nozzle_eff": ("0.95", "Nozzle Efficiency")
        })
        
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
        
        # Results label
        self.lbl_results = QLabel("Results will appear here.")
        self.lbl_results.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.lbl_results)
        
        # Thrust Plot
        self.plot_thrust = pg.PlotWidget(title="Thrust vs Time")
        self.plot_thrust.setLabel('left', 'Thrust', units='N')
        self.plot_thrust.setLabel('bottom', 'Time', units='s')
        self.plot_thrust.showGrid(x=True, y=True)
        right_layout.addWidget(self.plot_thrust)
        
        # Pressure Plot
        self.plot_pressure = pg.PlotWidget(title="Pressures vs Time")
        self.plot_pressure.setLabel('left', 'Pressure', units='kPa')
        self.plot_pressure.setLabel('bottom', 'Time', units='s')
        self.plot_pressure.showGrid(x=True, y=True)
        self.plot_pressure.addLegend()
        right_layout.addWidget(self.plot_pressure)
        
        layout.addWidget(right_panel, stretch=1)
        
        self.last_results = None

    def _create_input_group(self, title, fields):
        group = QGroupBox(title)
        form = QFormLayout()
        
        for key, (default_val, label) in fields.items():
            line_edit = QLineEdit(default_val)
            form.addRow(label, line_edit)
            self.inputs[key] = line_edit
            
        group.setLayout(form)
        self.input_layout.addWidget(group)
        
    def toggle_theme(self):
        if self.is_dark_mode:
            self.setStyleSheet("")
            self.is_dark_mode = False
        else:
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
            self.is_dark_mode = True

    def run_simulation(self):
        try:
            params = {k: float(v.text()) for k, v in self.inputs.items()}
            
            df = self.engine.run_simulation(params)
            self.last_results = df
            
            # Update Thrust plot
            self.plot_thrust.clear()
            self.plot_thrust.plot(df['Time'], df['Thrust'], pen=pg.mkPen('y', width=2))
            
            # Update Pressure plot
            self.plot_pressure.clear()
            self.plot_pressure.plot(df['Time'], df['P_N2O'], pen=pg.mkPen('b', width=2), name="N2O Tank")
            self.plot_pressure.plot(df['Time'], df['P_fu'], pen=pg.mkPen('g', width=2), name="Fuel Tank")
            self.plot_pressure.plot(df['Time'], df['P_c'], pen=pg.mkPen('r', width=2), name="Chamber")
            
            # Update Results label
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
        
        # Calculate motor stats
        total_impulse = np.trapz(df['Thrust'], df['Time'])
        max_thrust = df['Thrust'].max()
        burn_time = df['Time'].iloc[-1]
        init_mass = self.inputs['m_ox_init'].text() # simplify
        
        try:
            with open(file_path, 'w') as f:
                f.write("; Generated by HalfCat-PySim\n")
                # NAME DIAMETER LENGTH DELAYS PROPELLANT_WEIGHT TOTAL_WEIGHT MANUFACTURER
                # Approximate values
                f.write(f"M_Custom 98 1000 0 {float(init_mass)} {float(init_mass)+2.0} HalfCat\n")
                
                # Thrust data points
                for _, row in df.iterrows():
                    # Format: time thrust
                    f.write(f"{row['Time']:.3f} {row['Thrust']:.2f}\n")
                    
            QMessageBox.information(self, "Export Success", f"Successfully exported to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.path)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
