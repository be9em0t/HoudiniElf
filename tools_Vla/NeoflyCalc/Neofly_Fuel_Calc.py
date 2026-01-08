import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QSettings

class FuelCalc(QWidget):
    def __init__(self):
        super().__init__()
        ini_path = os.path.join(os.path.dirname(__file__), 'neoflycalc.ini')
        self.settings = QSettings(ini_path, QSettings.Format.IniFormat)
        self.aircrafts = {}
        aircraft_list_str = self.settings.value('aircraft_list', '')
        if not aircraft_list_str:
            # Set defaults
            default_aircrafts = {
                "Asobo C208B Cargo": {"max_fuel": 2034, "range": 964, "speed": 195},
                "Microsoft Piper PA28-236 Dacota": {"max_fuel": 432, "range": 740, "speed": 123},
                "Asobo C172SP G1000 Passengers": {"max_fuel": 342, "range": 640, "speed": 124}
            }
            aircraft_list = list(default_aircrafts.keys())
            self.settings.setValue('aircraft_list', ','.join(aircraft_list))
            for name, data in default_aircrafts.items():
                group_name = name.replace(' ', '_')
                self.settings.beginGroup(group_name)
                for key, value in data.items():
                    self.settings.setValue(key, value)
                self.settings.endGroup()
        else:
            aircraft_list = aircraft_list_str.split(',')
        
        for name in aircraft_list:
            group_name = name.replace(' ', '_')
            self.settings.beginGroup(group_name)
            data = {
                'max_fuel': int(self.settings.value('max_fuel', 0)),
                'range': int(self.settings.value('range', 0)),
                'speed': int(self.settings.value('speed', 0))
            }
            self.settings.endGroup()
            self.aircrafts[name] = data
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

        self.aircraft_combo = QComboBox()
        for name in self.aircrafts:
            self.aircraft_combo.addItem(name)
        selected = self.settings.value('selected_aircraft', 'Asobo C208B Cargo')
        self.aircraft_combo.setCurrentText(selected)
        self.aircraft_combo.setToolTip("Select aircraft model")
        layout.addWidget(self.aircraft_combo)
        self.aircraft_combo.currentTextChanged.connect(self.load_aircraft)

        max_fuel_layout = QHBoxLayout()
        max_fuel_layout.addWidget(QLabel("Max. fuel (lbs):"))
        self.max_fuel_label = QLabel()
        max_fuel_layout.addWidget(self.max_fuel_label)
        layout.addLayout(max_fuel_layout)

        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Range (n.m.):"))
        self.range_label = QLabel()
        range_layout.addWidget(self.range_label)
        layout.addLayout(range_layout)

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Cruise speed (ktas):"))
        self.speed_label = QLabel()
        speed_layout.addWidget(self.speed_label)
        layout.addLayout(speed_layout)

        # Flight settings
        self.flight_label = QLabel("Flight Settings")
        self.flight_label.setStyleSheet("color: #fdb200;")
        font = self.flight_label.font()
        font.setPointSize(font.pointSize() + 3)
        font.setCapitalization(QFont.Capitalization.SmallCaps)
        self.flight_label.setFont(font)
        layout.addWidget(self.flight_label)

        self.weight_edit = QLineEdit()
        self.weight_edit.setText(self.settings.value('weight_factor', '0.90'))
        weight_label = QLabel("Weight factor:")
        weight_label.setToolTip("1 is empty plane, 0 is maximum load")
        layout.addWidget(weight_label)
        layout.addWidget(self.weight_edit)

        self.wind_edit = QLineEdit()
        self.wind_edit.setText(self.settings.value('wind_factor', '0.90'))
        wind_label = QLabel("Wind factor:")
        wind_label.setToolTip("1 is no wind penalty, <1 for headwind")
        layout.addWidget(wind_label)
        layout.addWidget(self.wind_edit)

        self.climb_edit = QLineEdit()
        self.climb_edit.setText(self.settings.value('climb_fraction', '0.08'))
        climb_label = QLabel("Climb fraction:")
        climb_label.setToolTip("Fraction of max fuel reserved for climb")
        layout.addWidget(climb_label)
        layout.addWidget(self.climb_edit)

        self.reserve_frac_edit = QLineEdit()
        self.reserve_frac_edit.setText(self.settings.value('reserve_fraction', '0.12'))
        reserve_label = QLabel("Reserve fraction:")
        reserve_label.setToolTip("Fraction of max fuel reserved as final reserve")
        layout.addWidget(reserve_label)
        layout.addWidget(self.reserve_frac_edit)

        self.distance_edit = QLineEdit()
        self.distance_edit.setText(self.settings.value('flight_distance', '336'))
        distance_label = QLabel("Flight distance (n.m.):")
        distance_label.setToolTip("Planned distance in nautical miles")
        layout.addWidget(distance_label)
        layout.addWidget(self.distance_edit)

        self.weight_edit.textChanged.connect(self.save_settings)
        self.weight_edit.textChanged.connect(self.calculate)
        self.wind_edit.textChanged.connect(self.save_settings)
        self.wind_edit.textChanged.connect(self.calculate)
        self.climb_edit.textChanged.connect(self.save_settings)
        self.climb_edit.textChanged.connect(self.calculate)
        self.reserve_frac_edit.textChanged.connect(self.save_settings)
        self.reserve_frac_edit.textChanged.connect(self.calculate)
        self.distance_edit.textChanged.connect(self.save_settings)
        self.distance_edit.textChanged.connect(self.calculate)

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
        layout.addWidget(QLabel("Effective range:"))
        self.consumption_edit = QLineEdit()
        self.consumption_edit.setReadOnly(True)
        layout.addWidget(self.consumption_edit)

        layout.addWidget(QLabel("Cruise fuel:"))
        self.needed_edit = QLineEdit()
        self.needed_edit.setReadOnly(True)
        layout.addWidget(self.needed_edit)

        layout.addWidget(QLabel("Total fuel:"))
        self.load_edit = QLineEdit()
        self.load_edit.setReadOnly(True)
        layout.addWidget(self.load_edit)

        layout.addWidget(QLabel("Expected fuel flow:"))
        self.flow_edit = QLineEdit()
        self.flow_edit.setReadOnly(True)
        layout.addWidget(self.flow_edit)

        self.setLayout(layout)
        self.setWindowTitle("Neofly Fuel Calculator")
        self.load_aircraft()
        self.show()

    def calculate(self):
        try:
            max_fuel = float(self.max_fuel_label.text().split()[0])
            range_ = float(self.range_label.text().split()[0])
            speed = float(self.speed_label.text().split()[0])
            weight_factor = float(self.weight_edit.text())
            wind_factor = float(self.wind_edit.text())
            climb_fraction = float(self.climb_edit.text())
            reserve_fraction = float(self.reserve_frac_edit.text())
            distance = float(self.distance_edit.text())

            effective_range = range_ * weight_factor * wind_factor
            fixed_fraction = climb_fraction + reserve_fraction
            available_cruise_fuel = (1 - fixed_fraction) * max_fuel
            cruise_fuel = available_cruise_fuel * (distance / effective_range)
            total_fuel = cruise_fuel + fixed_fraction * max_fuel
            flow = (cruise_fuel / distance) * speed # if distance > 0 else 0

            self.consumption_edit.setText(f"{effective_range:.2f} n.m.")
            self.needed_edit.setText(f"{cruise_fuel:.2f} lbs")
            self.load_edit.setText(f"{total_fuel:.2f} lbs")
            if total_fuel >= max_fuel:
                self.load_edit.setStyleSheet("color: red;")
            else:
                self.load_edit.setStyleSheet("color: #fdb200;")
            self.flow_edit.setText(f"{flow:.2f} lbs/hour")
        except ValueError:
            # Handle invalid input - perhaps show a message
            pass

    def load_aircraft(self):
        name = self.aircraft_combo.currentText()
        data = self.aircrafts[name]
        self.max_fuel_label.setText(f"{data['max_fuel']} lbs")
        self.range_label.setText(f"{data['range']} n.m.")
        self.speed_label.setText(f"{data['speed']} ktas")
        self.settings.setValue('selected_aircraft', name)
        self.calculate()

    def save_settings(self):
        self.settings.setValue('weight_factor', self.weight_edit.text())
        self.settings.setValue('wind_factor', self.wind_edit.text())
        self.settings.setValue('climb_fraction', self.climb_edit.text())
        self.settings.setValue('reserve_fraction', self.reserve_frac_edit.text())
        self.settings.setValue('flight_distance', self.distance_edit.text())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    calc = FuelCalc()
    sys.exit(app.exec())
