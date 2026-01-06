import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtGui import QFont

class FuelCalc(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Aircraft settings
        self.aircraft_label = QLabel("Aircraft Settings")
        self.aircraft_label.setStyleSheet("color: #fdb200;")
        font = self.aircraft_label.font()
        font.setPointSize(font.pointSize() + 3)
        font.setCapitalization(QFont.Capitalization.SmallCaps)
        self.aircraft_label.setFont(font)
        layout.addWidget(self.aircraft_label)
        self.max_fuel_edit = QLineEdit("2034")
        layout.addWidget(QLabel("Max. fuel (lbs):"))
        layout.addWidget(self.max_fuel_edit)

        self.range_edit = QLineEdit("964")
        layout.addWidget(QLabel("Range (n.m.):"))
        layout.addWidget(self.range_edit)

        self.speed_edit = QLineEdit("195")
        layout.addWidget(QLabel("Cruise speed (ktas):"))
        layout.addWidget(self.speed_edit)

        # Flight settings
        self.flight_label = QLabel("Flight Settings")
        self.flight_label.setStyleSheet("color: #fdb200;")
        font = self.flight_label.font()
        font.setPointSize(font.pointSize() + 3)
        font.setCapitalization(QFont.Capitalization.SmallCaps)
        self.flight_label.setFont(font)
        layout.addWidget(self.flight_label)
        self.reserve_edit = QLineEdit("10")
        layout.addWidget(QLabel("Fuel reserve (%):"))
        layout.addWidget(self.reserve_edit)

        self.distance_edit = QLineEdit("336")
        layout.addWidget(QLabel("Flight distance (n.m.):"))
        layout.addWidget(self.distance_edit)

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
        layout.addWidget(QLabel("Fuel consumption rate:"))
        self.consumption_edit = QLineEdit()
        self.consumption_edit.setReadOnly(True)
        layout.addWidget(self.consumption_edit)

        layout.addWidget(QLabel("Fuel needed for flight:"))
        self.needed_edit = QLineEdit()
        self.needed_edit.setReadOnly(True)
        layout.addWidget(self.needed_edit)

        layout.addWidget(QLabel("Fuel to load:"))
        self.load_edit = QLineEdit()
        self.load_edit.setReadOnly(True)
        layout.addWidget(self.load_edit)

        layout.addWidget(QLabel("Expected fuel flow:"))
        self.flow_edit = QLineEdit()
        self.flow_edit.setReadOnly(True)
        layout.addWidget(self.flow_edit)

        self.setLayout(layout)
        self.setWindowTitle("Neofly Fuel Calculator")
        self.show()

    def calculate(self):
        try:
            max_fuel = float(self.max_fuel_edit.text())
            range_ = float(self.range_edit.text())
            speed = float(self.speed_edit.text())
            reserve = float(self.reserve_edit.text()) / 100
            distance = float(self.distance_edit.text())

            consumption = max_fuel / range_
            needed = consumption * distance
            load = needed * (1 + reserve)
            flow = consumption * speed

            self.consumption_edit.setText(f"{consumption:.2f} lbs/n.m.")
            self.needed_edit.setText(f"{needed:.2f} lbs")
            self.load_edit.setText(f"{load:.2f} lbs")
            self.flow_edit.setText(f"{flow:.2f} lbs/hour")
        except ValueError:
            # Handle invalid input - perhaps show a message
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    calc = FuelCalc()
    sys.exit(app.exec())
