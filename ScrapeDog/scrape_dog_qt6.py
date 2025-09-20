"""
Universal Web Scraper with Qt6 Interface

This script provides a flexible web scraping tool with a graphical user interface,
allowing users to specify target URLs and control the number of results to extract.

Features:
- Qt6-based graphical user interface
- Configurable target URL
- Adjustable result limit (stops scraping when reached)
- Cancellable scraping operations
- Asynchronous web crawling
- Progress tracking and status updates

Usage:
1. Ensure required dependencies are installed:
   pip install crawl4ai pydantic beautifulsoup4 PyQt6

2. Run the script:
   python scrape_dog_qt6.py

Dependencies:
- crawl4ai: Asynchronous web crawling
- pydantic: Data validation
- beautifulsoup4: HTML parsing
- PyQt6: Graphical user interface
"""

import asyncio
import sys
import json
from typing import List, Optional
from pathlib import Path
from urllib.parse import urljoin
import logging
import re
import configparser

from PyQt6.QtWidgets import (
	QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
	QLabel, QLineEdit, QSpinBox, QPushButton, QTextEdit, QProgressBar,
	QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
	QStyle, QComboBox  # Add this import
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap
from crawl4ai import AsyncWebCrawler
from pydantic import BaseModel
from bs4 import BeautifulSoup

# Configure simple logging for debugging/test runs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VexFunction(BaseModel):
	"""Data model for scraped function information."""
	name: str
	description: str
	category: str
	url: str
	usage: List[str]

class NodeEntry(BaseModel):
	"""Data model for scraped node information (nodes don't have usage)."""
	name: str
	description: str
	category: str
	url: str

# New testable scraper class which contains all parsing and fetching logic.
class Scraper:
	"""A testable, GUI-agnostic scraper.

	Supports two modes: 'vex' (functions + usage) and 'nodes' (node index, no usage).
	"""
	def __init__(self, target_url: str, max_results: int = 0, concurrency: int = 10, progress_callback=None, cancel_check=None, mode: str = 'vex'):
		self.target_url = target_url
		self.max_results = max_results
		self.concurrency = max(1, int(concurrency))
		self.progress_callback = progress_callback or (lambda msg, val=None: None)
		# cancel_check should be a callable returning True if cancelled
		self.cancel_check = cancel_check or (lambda: False)
		self._is_cancelled = False
		self.mode = mode or 'vex'

	def cancel(self):
		self._is_cancelled = True

	def _report(self, message: str, value: Optional[int] = None):
		try:
			self.progress_callback(message, value)
		except Exception:
			logger.debug("Progress callback failed", exc_info=True)

	async def scrape(self) -> List[BaseModel]:
		"""Run the full scraping pipeline and return parsed items.
		For 'vex' mode returns List[VexFunction]; for 'nodes' returns List[NodeEntry]
		"""
		# If cancellation already requested, return empty list (don't raise)
		if self.cancel_check() or self._is_cancelled:
			return []

		async with AsyncWebCrawler(verbose=False) as crawler:
			self._report(f"Fetching: {self.target_url}")
			result = await crawler.arun(url=self.target_url, session_id="universal_scrape")

			# If cancelled after fetch, return empty list
			if self.cancel_check() or self._is_cancelled:
				return []

			if not result.success:
				raise RuntimeError(getattr(result, 'error_message', 'Failed to fetch index page'))

			items = await self.parse_functions(result.html, crawler)
			if not items:
				self._report("No items found to scrape", 100)
				return []

			# Apply max_results if requested
			if self.max_results > 0:
				items = items[: self.max_results]
			self._report(f"Will process {len(items)} items")

			# For VEX mode we fetch usages. For nodes we skip extra fetches.
			if self.mode == 'vex':
				# Limit concurrency with a semaphore
				sem = asyncio.Semaphore(self.concurrency)

				async def fetch_one(func: VexFunction):
					if self.cancel_check() or self._is_cancelled:
						return func
					async with sem:
						try:
							usages = await self.fetch_function_usage(crawler, func)
							func.usage = usages
						except Exception:
							func.usage = []
					return func

				# create real tasks so we can cancel pending ones if needed
				tasks = [asyncio.create_task(fetch_one(f)) for f in items]
				processed: List[VexFunction] = []
				total = len(tasks)

				try:
					for coro in asyncio.as_completed(tasks):
						# if cancellation requested, break and clean up pending tasks
						if self.cancel_check() or self._is_cancelled:
							break
						func = await coro
						processed.append(func)
						pct = int((len(processed) / total) * 100)
						self._report(f"Processed {len(processed)}/{total}", pct)
				except Exception:
					# continue to cleanup below
					pass

				# Cancel any pending tasks if we stopped early
				for t in tasks:
					if not t.done():
						t.cancel()
				# Wait for cancellation to settle
				await asyncio.gather(*tasks, return_exceptions=True)

				return processed
			else:
				# nodes mode: return parsed NodeEntry list as-is
				return items

	async def parse_functions(self, html: str, crawler=None) -> List[BaseModel]:
		"""Parse HTML content to extract function or node information.
		If a node entry has no description, try fetching its linked page (using provided crawler)
		and extract a short description from meta tags or the first paragraph.
		"""
		soup = BeautifulSoup(html, 'html.parser')
		results: List[BaseModel] = []

		# For node mode try to detect a top-level category (page title) so we don't produce
		# multiple files for subsections (e.g. 'Object network' vs 'Object types').
		top_category = None
		if self.mode == 'nodes':
			h1 = soup.find('h1')
			if h1:
				top_category = h1.get_text().strip().split('\n')[0].strip()
			else:
				first_h2 = soup.find('h2')
				if first_h2:
					top_category = first_h2.get_text().strip().split('\n')[0].strip()

		# Find all h2 tags for categories
		categories = soup.find_all('h2')
		for h2 in categories:
			if self.cancel_check() or self._is_cancelled:
				break

			category = h2.get_text().strip().split('\n')[0].strip()
			if category in ['Functions', 'Language', 'Next steps', 'Reference']:
				continue
			self._report(f"Processing category: {category}")

			ul = h2.find_next('ul')
			if not ul:
				continue
			lis = ul.find_all('li', class_='item')
			for li in lis:
				if self.max_results > 0 and len(results) >= self.max_results:
					self._report(f"Reached maximum limit of {self.max_results} items")
					return results

				label_p = li.find('p', class_='label')
				summary_p = li.find('p', class_='summary')
				# Accept missing summary for nodes and attempt to fetch later
				if not label_p:
					continue
				a_tag = label_p.find('a')
				if not a_tag or 'href' not in a_tag.attrs:
					continue
				name = a_tag.get_text().strip()
				href = a_tag['href']
				# Build robust URL using urljoin
				url = urljoin(self.target_url, href)
				# description preference: index summary, else try to fetch from detail page (nodes mode)
				description = ''
				if summary_p:
					description = summary_p.get_text().strip()
				elif self.mode == 'nodes' and crawler is not None:
					# try fetching the linked page to extract a short description
					try:
						self._report(f"Fetching detail page for: {name}")
						detail = await crawler.arun(url=url)
						if detail.success:
							soup2 = BeautifulSoup(detail.html, 'html.parser')
							# try meta description
							meta = soup2.find('meta', attrs={'name': 'description'})
							if meta and meta.get('content'):
								description = meta.get('content').strip()
							else:
								# fallback to first meaningful paragraph
								p = soup2.find('p')
								if p and p.get_text().strip():
									description = p.get_text().strip()
					except Exception as e:
						logger.debug(f"Failed to fetch detail description for {url}: {e}", exc_info=True)

				if self.mode == 'vex':
					results.append(VexFunction(name=name, description=description, category=category, url=url, usage=[]))
				else:
					# For nodes use the detected top-level category when available to avoid
					# creating multiple category files for the same page.
					node_cat = top_category or category
					results.append(NodeEntry(name=name, description=description, category=node_cat, url=url))

		return results

	async def fetch_function_usage(self, crawler, func: VexFunction) -> List[str]:
		"""Fetch usage examples for a specific function, returning a list of code snippets."""
		if self.cancel_check() or self._is_cancelled:
			return []
		try:
			result = await crawler.arun(url=func.url)
			if not result.success:
				return []
			soup = BeautifulSoup(result.html, 'html.parser')
			codes = soup.find_all('code')
			usages: List[str] = []
			# Match function invocation like name(...)
			pattern = re.compile(rf"\b{re.escape(func.name)}\s*\(")
			for code in codes:
				text = code.get_text().strip()
				if pattern.search(text):
					cleaned = text.replace('\u00a0', ' ')
					usages.append(cleaned)
			return usages
		except Exception as e:
			logger.debug(f"Failed fetching usage for {func.url}: {e}", exc_info=True)
			return []


class ScraperThread(QThread):
	"""Background thread for web scraping operations."""
	progress_update = pyqtSignal(str)
	progress_value = pyqtSignal(int)
	scraping_complete = pyqtSignal(list)
	scraping_failed = pyqtSignal(str)
	
	def __init__(self, target_url: str, max_results: int = 0, concurrency: int = 10, mode: str = 'vex', houdini_version: str = ''):
		super().__init__()
		self.target_url = target_url
		self.max_results = max_results
		self._is_cancelled = False
		self.mode = mode
		self.houdini_version = houdini_version
		# Create a Scraper instance and pass callbacks for progress and cancellation checks
		self.scraper = Scraper(target_url, max_results, concurrency, progress_callback=self._progress_callback, cancel_check=lambda: self._is_cancelled, mode=self.mode)
		
	def _progress_callback(self, message: str, value: Optional[int] = None):
		self.progress_update.emit(message)
		if value is not None:
			try:
				self.progress_value.emit(int(value))
			except Exception:
				pass
	
	def cancel(self):
		"""Set the cancellation flag and notify the scraper."""
		self._is_cancelled = True
		self.scraper.cancel()
		self.progress_update.emit("Cancellation requested...")
		
	def run(self):
		"""Execute the scraping operation in a separate thread using the testable Scraper."""
		try:
			results = asyncio.run(self.scraper.scrape())
			self.scraping_complete.emit(results)
		except asyncio.CancelledError:
			self.scraping_failed.emit("Scraping cancelled by user")
		except Exception as e:
			logger.exception("Scraping failed")
			self.scraping_failed.emit(f"Error: {str(e)}")


class ScraperMainWindow(QMainWindow):
	"""Main application window with Qt6 interface."""
	
	def __init__(self):
		super().__init__()
		self.scraper_thread = None
		self.scraped_data = []
		self.settings = self.load_settings()
		self.init_ui()
		
	def load_settings(self):
		"""Load scrape_settings.ini from the same directory as this script."""
		cfg_path = Path(__file__).parent / 'scrape_settings.ini'
		config = configparser.ConfigParser()
		if cfg_path.exists():
			config.read(cfg_path)
		else:
			# Provide sane defaults
			config['vex'] = {
				'url': 'https://www.sidefx.com/docs/houdini20.5/vex/functions/index.html',
				'houdini_version': '20.5'
			}
			config['nodes'] = {
				'url': 'https://www.sidefx.com/docs/houdini20.5/nodes/obj/index.html',
				'houdini_version': '20.5'
			}
			# Save defaults so the user can edit later
			with open(cfg_path, 'w') as f:
				config.write(f)
		# remember last selected mode if present
		self._settings_path = cfg_path
		return config

	def _write_settings(self):
		"""Write current settings back to scrape_settings.ini next to the script."""
		try:
			if not hasattr(self, '_settings_path'):
				self._settings_path = Path(__file__).parent / 'scrape_settings.ini'
			with open(self._settings_path, 'w') as f:
				self.settings.write(f)
		except Exception as e:
			logger.debug(f"Failed to write settings file: {e}", exc_info=True)

	def init_ui(self):
		"""Initialize the user interface components."""
		self.setWindowTitle("Universal Web Scraper")
		self.setGeometry(100, 100, 1000, 800)
		
		# Try multiple methods to set an icon on macOS
		try:
			# First, try system theme icons
			app_icon = QIcon.fromTheme("network-server", 
				QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon))
			)
		except Exception:
			# Fallback to standard icon
			app_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon)
		
		# Set application-wide icon
		QApplication.setWindowIcon(app_icon)
		self.setWindowIcon(app_icon)
		
		# Create central widget and main layout
		central_widget = QWidget()
		self.setCentralWidget(central_widget)
		main_layout = QVBoxLayout(central_widget)
		
		config_layout = QHBoxLayout()
		config_label = QLabel("Setup:")
		self.config_combo = QComboBox()
		# Only list actual scrape presets; skip internal 'meta' section
		preset_sections = [s for s in self.settings.sections() if s.lower() != 'meta']
		self.config_combo.addItems(preset_sections)
		# If a meta section contains last_mode, preselect it (only if it's a real preset)
		last_mode = None
		if self.settings.has_section('meta'):
			last_mode = self.settings.get('meta', 'last_mode', fallback=None)
		if last_mode and last_mode in preset_sections:
			self.config_combo.setCurrentText(last_mode)
		self.config_combo.currentTextChanged.connect(self.on_config_changed)
		config_layout.addWidget(config_label)
		config_layout.addWidget(self.config_combo)
		main_layout.addLayout(config_layout)

		# URL and Version input section
		url_layout = QHBoxLayout()
		url_label = QLabel("Target URL:")
		self.url_input = QLineEdit()
		default_setup = self.config_combo.currentText() or 'vex'
		self.url_input.setText(self.settings.get(default_setup, 'url'))
		self.url_input.setPlaceholderText("Enter the URL to scrape...")
		# Version input (user can override the version from the URL)
		version_label = QLabel("Version:")
		self.version_input = QLineEdit()
		self.version_input.setMaximumWidth(120)
		self.version_input.setText(self.settings.get(default_setup, 'houdini_version', fallback=''))
		self.version_input.setPlaceholderText("e.g. 20.5")
		url_layout.addWidget(url_label)
		url_layout.addWidget(self.url_input)
		url_layout.addWidget(version_label)
		url_layout.addWidget(self.version_input)
		main_layout.addLayout(url_layout)
		
		# Results limit section
		limit_layout = QHBoxLayout()
		limit_label = QLabel("Max Results (0 = unlimited):")
		self.limit_spinbox = QSpinBox()
		self.limit_spinbox.setMinimum(0)
		self.limit_spinbox.setMaximum(10000)
		self.limit_spinbox.setValue(0)
		self.limit_spinbox.setToolTip("Set to 0 for unlimited results, or specify a number to stop scraping after reaching that limit")
		limit_layout.addWidget(limit_label)
		limit_layout.addWidget(self.limit_spinbox)
		limit_layout.addStretch()
		main_layout.addLayout(limit_layout)
		
		# Control buttons
		button_layout = QHBoxLayout()
		self.scrape_button = QPushButton("Start Scraping")
		self.scrape_button.clicked.connect(self.start_scraping)
		self.cancel_button = QPushButton("Cancel")
		self.cancel_button.clicked.connect(self.cancel_scraping)
		self.cancel_button.setEnabled(False)
		self.cancel_button.setStyleSheet("QPushButton:enabled { background-color: #ff6b6b; }")
		self.save_button = QPushButton("Save Results As")
		self.save_button.clicked.connect(self.save_results)
		self.save_button.setEnabled(False)
		button_layout.addWidget(self.scrape_button)
		button_layout.addWidget(self.cancel_button)
		button_layout.addWidget(self.save_button)
		button_layout.addStretch()
		main_layout.addLayout(button_layout)
		
		# Progress bar
		self.progress_bar = QProgressBar()
		self.progress_bar.setVisible(False)
		main_layout.addWidget(self.progress_bar)
		
		# Results table
		self.results_table = QTableWidget()
		self.results_table.setColumnCount(4)
		self.results_table.setHorizontalHeaderLabels(["Name", "Description", "Category", "URL"])
		self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
		self.results_table.setVisible(False)
		main_layout.addWidget(self.results_table)
		
		# Output text area
		self.output_text = QTextEdit()
		self.output_text.setReadOnly(True)
		main_layout.addWidget(self.output_text)
		
	def on_config_changed(self, name: str):
		"""Update UI fields when the selected setup changes."""
		if not name:
			return
		url = self.settings.get(name, 'url', fallback='')
		self.url_input.setText(url)
		# update version field when switching presets
		version = self.settings.get(name, 'houdini_version', fallback='')
		self.version_input.setText(version)
		# persist selected mode
		try:
			if not self.settings.has_section('meta'):
				self.settings.add_section('meta')
			self.settings.set('meta', 'last_mode', name)
			self._write_settings()
		except Exception:
			pass

	def start_scraping(self):
		"""Initiate the scraping process with user-specified parameters."""
		target_url = self.url_input.text().strip()
		mode = self.config_combo.currentText() or 'vex'
		# Prefer explicit version input, fallback to settings
		input_version = self.version_input.text().strip() if hasattr(self, 'version_input') else ''
		houdini_version = input_version or self.settings.get(mode, 'houdini_version', fallback='')
		
		if not target_url:
			QMessageBox.warning(self, "Warning", "Please enter a target URL")
			return
		# persist url and version back to the selected preset
		try:
			if not self.settings.has_section(mode):
				self.settings.add_section(mode)
			self.settings.set(mode, 'url', target_url)
			self.settings.set(mode, 'houdini_version', houdini_version)
			# also persist selected mode
			if not self.settings.has_section('meta'):
				self.settings.add_section('meta')
			self.settings.set('meta', 'last_mode', mode)
			self._write_settings()
		except Exception:
			logger.debug('Failed to persist settings', exc_info=True)
		
		# Disable/enable controls during scraping
		self.scrape_button.setEnabled(False)
		self.cancel_button.setEnabled(True)
		self.save_button.setEnabled(False)
		self.progress_bar.setVisible(True)
		self.progress_bar.setValue(0)
		self.output_text.clear()
		self.results_table.setVisible(False)
		
		# Get max results setting
		max_results = self.limit_spinbox.value()
		
		# Create and start scraper thread
		self.scraper_thread = ScraperThread(target_url, max_results, mode=mode, houdini_version=houdini_version)
		self.scraper_thread.progress_update.connect(self.update_output)
		self.scraper_thread.progress_value.connect(self.update_progress)
		self.scraper_thread.scraping_complete.connect(self.on_scraping_complete)
		self.scraper_thread.scraping_failed.connect(self.on_scraping_failed)
		self.scraper_thread.start()

		self.output_text.append(f"Starting scrape of: {target_url} (setup: {mode}, version: {houdini_version})")
		if max_results > 0:
			self.output_text.append(f"Will stop after scraping {max_results} items")
		else:
			self.output_text.append("No limit set - will scrape all available items")
			
	def cancel_scraping(self):
		"""Cancel the ongoing scraping operation."""
		if self.scraper_thread and self.scraper_thread.isRunning():
			self.output_text.append("\n⚠ Cancelling scraping operation...")
			self.scraper_thread.cancel()
			self.cancel_button.setEnabled(False)
		
	def update_output(self, message: str):
		"""Update the output text area with progress messages."""
		self.output_text.append(message)
		
	def update_progress(self, value: int):
		"""Update the progress bar value."""
		self.progress_bar.setValue(value)
		
	def on_scraping_complete(self, functions: List[BaseModel]):
		"""Handle successful completion of scraping."""
		self.scraped_data = functions
		mode = getattr(self.scraper_thread, 'mode', 'vex')
		# prefer thread-provided houdini_version, otherwise use the UI input
		hv = getattr(self.scraper_thread, 'houdini_version', '') or (self.version_input.text().strip() if hasattr(self, 'version_input') else '')
		self.output_text.append(f"\n✓ Successfully scraped {len(functions)} items (mode: {mode})")

		# Display results in the table (only first 10)
		self.results_table.setRowCount(min(len(functions), 10))
		self.results_table.setVisible(True)

		for row, func in enumerate(functions[:10]):
			# Support both VexFunction and NodeEntry
			name = getattr(func, 'name', '')
			desc = getattr(func, 'description', '')
			cat = getattr(func, 'category', '')
			url = getattr(func, 'url', '')
			self.results_table.setItem(row, 0, QTableWidgetItem(name))
			self.results_table.setItem(row, 1, QTableWidgetItem(desc))
			self.results_table.setItem(row, 2, QTableWidgetItem(cat))
			self.results_table.setItem(row, 3, QTableWidgetItem(url))

		# Display detailed results in the text area for first 10
		self.output_text.append("\nDetailed results (first 10):")
		for func in functions[:10]:
			name = getattr(func, 'name', '')
			desc = getattr(func, 'description', '')
			cat = getattr(func, 'category', '')
			self.output_text.append(f"  • {name} ({cat}): {desc}")
			# Only show usage for vex mode
			if mode == 'vex' and getattr(func, 'usage', None):
				self.output_text.append("    Usage examples:")
				for usage in func.usage[:2]:  # Show up to 2 usage examples
					self.output_text.append(f"      - {usage}")
			self.output_text.append("")

		# Auto-save results into the script folder
		try:
			script_dir = Path(__file__).parent
			if mode == 'vex':
				out = {
					"houdini_version": hv,
					"functions": [f.model_dump() for f in functions]
				}
				out_path = script_dir / f"Houdini_Vex_functions_{hv}.json"
				with open(out_path, 'w') as f:
					json.dump(out, f, indent=2)
				self.output_text.append(f"\n✓ Auto-saved VEX functions to: {out_path}")
			else:
				# Group by category and write one file per category (omit usage)
				by_cat = {}
				for n in functions:
					cat = getattr(n, 'category', 'Uncategorized')
					by_cat.setdefault(cat, []).append({
						'name': n.name,
						'description': n.description,
						'url': n.url
					})
				for cat, items in by_cat.items():
					safe_cat = re.sub(r"[^A-Za-z0-9_]+", "_", cat).strip('_')
					out = {
						"houdini_version": hv,
						"category": cat,
						"nodes": items
					}
					out_path = script_dir / f"Houdini_Nodes_{safe_cat}_{hv}.json"
					with open(out_path, 'w') as f:
						json.dump(out, f, indent=2)
					self.output_text.append(f"\n✓ Auto-saved nodes to: {out_path}")
		except Exception as e:
			self.output_text.append(f"\n✗ Auto-save failed: {e}")

		# Re-enable controls
		self.scrape_button.setEnabled(True)
		self.cancel_button.setEnabled(False)
		self.save_button.setEnabled(True if functions else False)
		self.progress_bar.setVisible(False)

	def on_scraping_failed(self, error_message: str):
		"""Handle scraping failure or cancellation."""
		if "cancelled" in error_message.lower():
			self.output_text.append(f"\n⚠ {error_message}")
		else:
			self.output_text.append(f"\n✗ Scraping failed: {error_message}")
			QMessageBox.critical(self, "Scraping Failed", error_message)
			
		self.scrape_button.setEnabled(True)
		self.cancel_button.setEnabled(False)
		self.progress_bar.setVisible(False)
		
	def save_results(self):
		"""Save scraped results to a JSON file (manual save)."""
		if not self.scraped_data:
			QMessageBox.warning(self, "Warning", "No data to save")
			return
		mode = getattr(self.scraper_thread, 'mode', 'vex') if self.scraper_thread else 'vex'
		# prefer thread-provided houdini_version, otherwise use UI input
		hv = getattr(self.scraper_thread, 'houdini_version', '') if self.scraper_thread else ''
		if not hv and hasattr(self, 'version_input'):
			hv = self.version_input.text().strip()
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			"Save Results",
			"scraped_results.json",
			"JSON Files (*.json);;All Files (*)"
		)
		if file_path:
			try:
				script_dir = Path(__file__).parent
				if mode == 'vex':
					out = {"houdini_version": hv, "functions": [f.model_dump() for f in self.scraped_data]}
				else:
					# group into one file
					by_cat = {}
					for n in self.scraped_data:
						cat = getattr(n, 'category', 'Uncategorized')
						by_cat.setdefault(cat, []).append({'name': n.name, 'description': n.description, 'url': n.url})
					out = {"houdini_version": hv, "categories": by_cat}
				with open(file_path, 'w') as f:
					json.dump(out, f, indent=2)
				self.output_text.append(f"\n✓ Results saved to: {file_path}")
				QMessageBox.information(self, "Success", f"Results saved to {file_path}")
			except Exception as e:
				QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")


def main():
	"""Main entry point for the application."""
	app = QApplication(sys.argv)
	window = ScraperMainWindow()
	window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()