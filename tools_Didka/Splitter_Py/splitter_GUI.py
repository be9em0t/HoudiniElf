#!/usr/bin/env python3
"""
CSV Splitter/Combiner GUI
Qt6-based graphical interface for splitting and combining CSV files.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QFileDialog, 
    QTextEdit, QFrame, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


class WorkerThread(QThread):
    """Worker thread for processing files without blocking the GUI."""
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, mode, file_path=None, lines=3000, directory=None):
        super().__init__()
        self.mode = mode
        self.file_path = file_path
        self.lines = lines
        self.directory = directory
    
    def run(self):
        try:
            if self.mode == 'split':
                self.split_csv(self.file_path, self.lines)
            elif self.mode == 'combine':
                self.combine_csv(self.directory)
        except Exception as e:
            self.finished.emit(f"Error: {str(e)}")
    
    def split_csv(self, file_path, lines_per_file):
        """Split a CSV file into multiple files."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.finished.emit(f"Error: File '{file_path}' not found.")
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            header = f.readline()
            
            if not header:
                self.finished.emit("Error: File is empty.")
                return
            
            file_count = 1
            line_count = 0
            output_file = None
            
            for line in f:
                if line_count == 0:
                    base_name = file_path.stem
                    extension = file_path.suffix
                    output_path = file_path.parent / f"{base_name}_part_{file_count:04d}{extension}"
                    output_file = open(output_path, 'w', encoding='utf-8')
                    output_file.write(header)
                    self.progress.emit(f"Creating: {output_path.name}")
                
                output_file.write(line)
                line_count += 1
                
                if line_count >= lines_per_file:
                    output_file.close()
                    line_count = 0
                    file_count += 1
            
            if output_file and not output_file.closed:
                output_file.close()
            
            self.finished.emit(f"Split complete: Created {file_count} file(s)")
    
    def combine_csv(self, directory):
        """Combine all CSV files in a directory."""
        dir_path = Path(directory)
        
        if not dir_path.exists() or not dir_path.is_dir():
            self.finished.emit(f"Error: Directory '{directory}' not found.")
            return
        
        csv_files = sorted(dir_path.glob('*.csv'))
        
        if not csv_files:
            self.finished.emit(f"No CSV files found in '{directory}'")
            return
        
        output_path = dir_path / "combined_output.csv"
        header_written = False
        total_lines = 0
        
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for csv_file in csv_files:
                self.progress.emit(f"Processing: {csv_file.name}")
                with open(csv_file, 'r', encoding='utf-8') as infile:
                    header = infile.readline()
                    
                    if not header_written:
                        outfile.write(header)
                        header_written = True
                    
                    for line in infile:
                        outfile.write(line)
                        total_lines += 1
        
        self.finished.emit(f"Combine complete: {len(csv_files)} file(s) merged into '{output_path.name}'\nTotal lines: {total_lines}")


class SplitterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("CSV Splitter/Combiner")
        self.setGeometry(100, 100, 600, 500)
        
        # Main widget and layout
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #263543; color: white;")
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        main_widget.setLayout(layout)
        
        # Title
        title = QLabel("File Splitter")
        title_font = QFont()
        title_font.setPointSize(42)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # Mode selection
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("font-size: 14pt;")
        mode_layout.addWidget(mode_label)
        
        self.mode_group = QButtonGroup()
        self.split_radio = QRadioButton("Split")
        self.combine_radio = QRadioButton("Combine")
        self.split_radio.setChecked(True)
        self.split_radio.setStyleSheet("font-size: 14pt; outline: none;")
        self.combine_radio.setStyleSheet("font-size: 14pt; outline: none;")
        self.split_radio.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combine_radio.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.mode_group.addButton(self.split_radio)
        self.mode_group.addButton(self.combine_radio)
        
        mode_layout.addWidget(self.split_radio)
        mode_layout.addWidget(self.combine_radio)
        mode_layout.addStretch()
        
        layout.addLayout(mode_layout)
        
        layout.addSpacing(15)
        
        # Split controls
        split_label = QLabel("File to split:")
        split_label.setStyleSheet("font-size: 14pt;")
        layout.addWidget(split_label)
        
        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setStyleSheet("background-color: white; color: black; padding: 5px; font-size: 11pt;")
        self.file_input.setPlaceholderText("Select a CSV file...")
        file_layout.addWidget(self.file_input)
        
        self.browse_file_btn = QPushButton("Browse...")
        self.browse_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a5f7a; 
                color: white; 
                padding: 7.5px 15px; 
                font-size: 11pt;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a7090;
            }
        """)
        self.browse_file_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_file_btn)
        
        layout.addLayout(file_layout)
        
        # Lines per file
        lines_label = QLabel("Lines per file:")
        lines_label.setStyleSheet("padding-left: 0px; font-size: 14pt;")
        layout.addWidget(lines_label)
        
        self.lines_input = QSpinBox()
        self.lines_input.setMinimum(1)
        self.lines_input.setMaximum(1000000)
        self.lines_input.setValue(3000)
        self.lines_input.setStyleSheet("background-color: white; color: black; font-size: 11pt;")
        self.lines_input.lineEdit().setStyleSheet("padding-left: 5px;")
        self.lines_input.setFixedHeight(self.file_input.sizeHint().height())
        self.lines_input.setFixedWidth(100)
        layout.addWidget(self.lines_input, alignment=Qt.AlignmentFlag.AlignLeft)
        
        layout.addSpacing(10)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #FDB200; min-height: 4px; max-height: 4px;")
        layout.addWidget(separator)
        
        layout.addSpacing(10)
        
        # Combine controls
        dir_label = QLabel("Directory of files to combine:")
        dir_label.setStyleSheet("font-size: 14pt;")
        layout.addWidget(dir_label)
        
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setStyleSheet("background-color: white; color: black; padding: 5px; font-size: 11pt;")
        self.dir_input.setPlaceholderText("Select a directory...")
        dir_layout.addWidget(self.dir_input)
        
        self.browse_dir_btn = QPushButton("Browse...")
        self.browse_dir_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a5f7a; 
                color: white; 
                padding: 7.5px 15px; 
                font-size: 11pt;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a7090;
            }
        """)
        self.browse_dir_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.browse_dir_btn)
        
        layout.addLayout(dir_layout)
        
        layout.addSpacing(20)
        
        # Execute button
        self.execute_btn = QPushButton("Execute")
        self.execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #FDB200; 
                color: #263543; 
                padding: 10px; 
                font-size: 14pt;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #fdc520;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
            }
        """)
        self.execute_btn.clicked.connect(self.execute)
        layout.addWidget(self.execute_btn)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: #1a2530; color: #aaa; padding: 10px; font-size: 10pt; font-family: monospace;")
        self.output_text.setMaximumHeight(150)
        layout.addWidget(self.output_text)
        
        layout.addStretch()
    
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.file_input.setText(file_path)
    
    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory"
        )
        if dir_path:
            self.dir_input.setText(dir_path)
    
    def execute(self):
        mode = 'split' if self.split_radio.isChecked() else 'combine'
        
        self.output_text.clear()
        self.execute_btn.setEnabled(False)
        
        if mode == 'split':
            file_path = self.file_input.text()
            if not file_path:
                self.output_text.append("Error: Please select a file to split.")
                self.execute_btn.setEnabled(True)
                return
            
            lines = self.lines_input.value()
            self.worker = WorkerThread('split', file_path=file_path, lines=lines)
        else:
            directory = self.dir_input.text()
            if not directory:
                self.output_text.append("Error: Please select a directory to combine.")
                self.execute_btn.setEnabled(True)
                return
            
            self.worker = WorkerThread('combine', directory=directory)
        
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.operation_finished)
        self.worker.start()
    
    def update_progress(self, message):
        self.output_text.append(message)
    
    def operation_finished(self, message):
        self.output_text.append(message)
        self.execute_btn.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    gui = SplitterGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()