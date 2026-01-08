import sys
import os
import math
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QSettings

class DescentCalc(QWidget):
    def __init__(self):
        super().__init__()
        ini_path = os.path.join(os.path.dirname(__file__), 'msfs_descent.ini')
        self.settings = QSettings(ini_path, QSettings.Format.IniFormat)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Inputs
        self.inputs_label = QLabel("Inputs")
        self.inputs_label.setStyleSheet("color: #fdb200;")
        font = self.inputs_label.font()
        font.setPointSize(font.pointSize() + 3)
        font.setCapitalization(QFont.Capitalization.SmallCaps)
        self.inputs_label.setFont(font)
        layout.addWidget(self.inputs_label)

        # ALTcurrent
        alt_current_layout = QHBoxLayout()
        alt_current_layout.addWidget(QLabel("Current Altitude (ft):"))
        self.alt_current_edit = QLineEdit()
        self.alt_current_edit.setText(self.settings.value('alt_current', '30000'))
        self.alt_current_edit.setToolTip("Current altitude in feet")
        alt_current_layout.addWidget(self.alt_current_edit)
        layout.addLayout(alt_current_layout)

        # ALTtarget
        alt_target_layout = QHBoxLayout()
        alt_target_layout.addWidget(QLabel("Target Altitude (ft):"))
        self.alt_target_edit = QLineEdit()
        self.alt_target_edit.setText(self.settings.value('alt_target', '5000'))
        self.alt_target_edit.setToolTip("Target altitude in feet")
        alt_target_layout.addWidget(self.alt_target_edit)
        layout.addLayout(alt_target_layout)

        # GS
        gs_layout = QHBoxLayout()
        gs_layout.addWidget(QLabel("Groundspeed (kt):"))
        self.gs_edit = QLineEdit()
        self.gs_edit.setText(self.settings.value('gs', '250'))
        self.gs_edit.setToolTip("Groundspeed in knots")
        gs_layout.addWidget(self.gs_edit)
        layout.addLayout(gs_layout)

        # θ
        theta_layout = QHBoxLayout()
        theta_layout.addWidget(QLabel("Descent Angle (deg):"))
        self.theta_edit = QLineEdit()
        self.theta_edit.setText(self.settings.value('theta', '3'))
        self.theta_edit.setToolTip("Descent angle in degrees")
        theta_layout.addWidget(self.theta_edit)
        layout.addLayout(theta_layout)

        # ktail
        ktail_layout = QHBoxLayout()
        ktail_layout.addWidget(QLabel("Tailwind Coefficient:"))
        self.ktail_edit = QLineEdit()
        self.ktail_edit.setText(self.settings.value('ktail', '0.0'))
        self.ktail_edit.setToolTip("Tailwind coefficient (0-1)")
        ktail_layout.addWidget(self.ktail_edit)
        layout.addLayout(ktail_layout)

        # khead
        khead_layout = QHBoxLayout()
        khead_layout.addWidget(QLabel("Headwind Coefficient:"))
        self.khead_edit = QLineEdit()
        self.khead_edit.setText(self.settings.value('khead', '0.0'))
        self.khead_edit.setToolTip("Headwind coefficient (0-1)")
        khead_layout.addWidget(self.khead_edit)
        layout.addLayout(khead_layout)

        # Connect inputs to save and calculate
        self.alt_current_edit.textChanged.connect(self.save_settings)
        self.alt_current_edit.textChanged.connect(self.calculate)
        self.alt_target_edit.textChanged.connect(self.save_settings)
        self.alt_target_edit.textChanged.connect(self.calculate)
        self.gs_edit.textChanged.connect(self.save_settings)
        self.gs_edit.textChanged.connect(self.calculate)
        self.theta_edit.textChanged.connect(self.save_settings)
        self.theta_edit.textChanged.connect(self.calculate)
        self.ktail_edit.textChanged.connect(self.save_settings)
        self.ktail_edit.textChanged.connect(self.calculate)
        self.khead_edit.textChanged.connect(self.save_settings)
        self.khead_edit.textChanged.connect(self.calculate)

        # Button
        self.calc_button = QPushButton("Calculate")
        self.calc_button.clicked.connect(self.calculate)
        layout.addWidget(self.calc_button)

        # Results
        self.results_label = QLabel("Results")
        self.results_label.setStyleSheet("color: #fdb200;")
        font = self.results_label.font()
        font.setPointSize(font.pointSize() + 3)
        font.setCapitalization(QFont.Capitalization.SmallCaps)
        self.results_label.setFont(font)
        layout.addWidget(self.results_label)

        layout.addWidget(QLabel("Altitude to lose (ft):"))
        self.dh_edit = QLineEdit()
        self.dh_edit.setReadOnly(True)
        layout.addWidget(self.dh_edit)

        layout.addWidget(QLabel("Base TOD distance (NM):"))
        self.tod_edit = QLineEdit()
        self.tod_edit.setReadOnly(True)
        layout.addWidget(self.tod_edit)

        layout.addWidget(QLabel("Wind-adjusted TOD distance (NM):"))
        self.tod_wind_edit = QLineEdit()
        self.tod_wind_edit.setReadOnly(True)
        layout.addWidget(self.tod_wind_edit)

        layout.addWidget(QLabel("Vertical speed (fpm):"))
        self.vs_edit = QLineEdit()
        self.vs_edit.setReadOnly(True)
        layout.addWidget(self.vs_edit)

        self.setLayout(layout)
        self.setWindowTitle("MSFS Descent Calculator")
        self.calculate()
        self.show()

    def calculate(self):
        try:
            alt_current = float(self.alt_current_edit.text())
            alt_target = float(self.alt_target_edit.text())
            gs = float(self.gs_edit.text())
            theta_deg = float(self.theta_edit.text())
            ktail = float(self.ktail_edit.text())
            khead = float(self.khead_edit.text())

            # Altitude to lose
            dh_ft = alt_current - alt_target

            # Base TOD distance
            theta_rad = math.radians(theta_deg)
            tod_nm = dh_ft / (6076 * math.tan(theta_rad))

            # Wind-adjusted TOD
            tod_nm_wind = tod_nm * (1 + ktail - khead)

            # Vertical speed
            vs_fpm = (6076 * math.tan(theta_rad)) * (gs / 60)

            self.dh_edit.setText(f"{dh_ft:.2f} ft")
            self.tod_edit.setText(f"{tod_nm:.2f} NM")
            self.tod_wind_edit.setText(f"{tod_nm_wind:.2f} NM")
            self.vs_edit.setText(f"{vs_fpm:.2f} fpm")

            # Reset colors
            self.dh_edit.setStyleSheet("")
            self.tod_edit.setStyleSheet("")
            self.tod_wind_edit.setStyleSheet("color: #fdb200;")
            self.vs_edit.setStyleSheet("")

        except ValueError:
            # Handle invalid input
            self.dh_edit.setText("Invalid input")
            self.tod_edit.setText("Invalid input")
            self.tod_wind_edit.setText("Invalid input")
            self.vs_edit.setText("Invalid input")

    def save_settings(self):
        self.settings.setValue('alt_current', self.alt_current_edit.text())
        self.settings.setValue('alt_target', self.alt_target_edit.text())
        self.settings.setValue('gs', self.gs_edit.text())
        self.settings.setValue('theta', self.theta_edit.text())
        self.settings.setValue('ktail', self.ktail_edit.text())
        self.settings.setValue('khead', self.khead_edit.text())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    calc = DescentCalc()
    sys.exit(app.exec())