import sys
import os
import logging
import time
import ctypes
import requests  # Hinzugefügt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QCheckBox, 
                            QFrame, QListWidget, QTabWidget, QProgressBar, QTextEdit, QScrollArea,
                            QSplashScreen, QDialog)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QPainter, QLinearGradient

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from src.start_app import main as start_app_main
except ImportError as e:
    logging.error(f"Failed to import start_app_main: {e}")
    start_app_main = lambda x: logging.error("start_app_main not available")

def minimize_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 6)  # 6 = SW_MINIMIZE
        else:
            logging.warning("No console window found to minimize")
    except Exception as e:
        logging.error(f"Error minimizing console: {e}")

class SplashScreen(QSplashScreen):
    def __init__(self):
        try:
            super().__init__()
            self.setFixedSize(400, 400)
            self.progress = QProgressBar(self)
            self.progress.setGeometry(50, 350, 300, 20)
            self.progress.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #FF6B6B;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #1a1a1a;
                }
                QProgressBar::chunk {
                    background-color: #FF6B6B;
                }
            """)

            # Lade das Bild von der URL
            logo_url = "https://beeimg.com/images/e94478500041.png"
            try:
                response = requests.get(logo_url, timeout=5)
                response.raise_for_status()  # Prüft, ob der Request erfolgreich war
                self.logo = QPixmap()
                self.logo.loadFromData(response.content)
                logging.info(f"Loaded logo from {logo_url}")
            except requests.RequestException as e:
                logging.warning(f"Failed to load logo from {logo_url}: {e}")
                self.logo = QPixmap(100, 100)  # Fallback-Bild
                self.logo.fill(QColor("#1a1a1a"))  # Fülle mit dunkler Farbe als Fallback

        except Exception as e:
            logging.error(f"Error initializing SplashScreen: {e}")
            raise

    def drawContents(self, painter):
        try:
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor("#121212"))
            gradient.setColorAt(1, QColor("#1a1a1a"))
            painter.fillRect(self.rect(), gradient)

            logo_scaled = self.logo.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_x = (self.width() - logo_scaled.width()) // 2
            logo_y = 50
            painter.drawPixmap(logo_x, logo_y, logo_scaled)

            painter.setPen(QColor("#FF6B6B"))
            font = QFont("Arial", 36, QFont.Weight.Bold)
            painter.setFont(font)
            text_y = logo_y + logo_scaled.height() + 20
            painter.drawText(0, text_y, self.width(), 100, Qt.AlignmentFlag.AlignCenter, "ANIMORO")
        except Exception as e:
            logging.error(f"Error in drawContents: {e}")

# Der Rest des Codes bleibt unverändert
class SearchSuggestionThread(QThread):
    suggestions_ready = pyqtSignal(list)
    
    def __init__(self, search_text, search_type):
        super().__init__()
        self.search_text = search_text
        self.search_type = search_type
        self.anime_list = []
        self.series_list = []
        try:
            with open('list/animes.txt', 'r', encoding='utf-8') as f:
                self.anime_list = [line.strip() for line in f.readlines() if line.strip()]
            logging.info("Loaded anime list")
        except Exception as e:
            logging.error(f"Error loading anime list: {e}")
        try:
            with open('list/series.txt', 'r', encoding='utf-8') as f:
                self.series_list = [line.strip() for line in f.readlines() if line.strip()]
            logging.info("Loaded series list")
        except Exception as e:
            logging.error(f"Error loading series list: {e}")
        
    def run(self):
        try:
            suggestions = []
            search_query = self.search_text.lower()
            search_list = self.anime_list if self.search_type.lower() == "anime" else self.series_list
            for title in search_list:
                if search_query in title.lower():
                    suggestions.append({'title': title, 'year': '', 'type': self.search_type})
                    if len(suggestions) >= 10:
                        break
            self.suggestions_ready.emit(suggestions)
        except Exception as e:
            logging.error(f"Error in SearchSuggestionThread: {e}")
            self.suggestions_ready.emit([])

class ScraperThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, args):
        super().__init__()
        self.args = args

    def run(self):
        try:
            start_app_main(self.args)
            self.finished.emit()
        except Exception as e:
            self.progress.emit(f"Error: {str(e)}")
            logging.error(f"Error in ScraperThread: {e}")

class ModernSearchInput(QLineEdit):
    def __init__(self, parent=None, search_type="Anime"):
        super().__init__(parent)
        self.search_type = search_type
        self.suggestion_list = QListWidget()
        self.suggestion_list.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.suggestion_list.setFocusProxy(self)
        self.suggestion_list.setMouseTracking(True)
        self.suggestion_list.itemClicked.connect(self.complete_text)
        self.suggestion_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.suggestion_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                border: 2px solid #FF6B6B;
                border-radius: 8px;
                color: #ffffff;
                selection-background-color: #2d2d2d;
                font-size: 14px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #2d2d2d;
            }
            QListWidget::item:selected {
                background: #FF6B6B;
                color: white;
            }
        """)
        
        self.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                border: 2px solid #FF6B6B;
                border-radius: 8px;
                color: #ffffff;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #FF6B6B;
            }
        """)
        
        self.textChanged.connect(self.get_suggestions)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.trigger_search)
        self.load_lists()
        self.suggestions_visible = False
        
    def load_lists(self):
        try:
            with open('list/animes.txt', 'r', encoding='utf-8') as f:
                self.anime_list = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"Fehler beim Laden der Anime-Liste: {str(e)}")
            self.anime_list = []
            
        try:
            with open('list/series.txt', 'r', encoding='utf-8') as f:
                self.series_list = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"Fehler beim Laden der Serien-Liste: {str(e)}")
            self.series_list = []
    
    def get_suggestions(self, text):
        self.search_timer.stop()
        if len(text) >= 2:
            self.search_timer.start(100)
        else:
            self.suggestion_list.hide()
            self.suggestions_visible = False
            
    def trigger_search(self):
        self.search_thread = SearchSuggestionThread(self.text(), self.search_type)
        self.search_thread.suggestions_ready.connect(self.show_suggestions)
        self.search_thread.start()
        
    def show_suggestions(self, suggestions):
        self.suggestion_list.clear()
        if not suggestions:
            self.suggestion_list.hide()
            self.suggestions_visible = False
            return
            
        for suggestion in suggestions:
            title = suggestion['title']
            year = suggestion['year']
            display_text = f"{title} ({year})" if year else title
            self.suggestion_list.addItem(display_text)
            
        self.suggestion_list.setMinimumWidth(self.width())
        self.suggestion_list.setMaximumWidth(self.width())
        global_pos = self.mapToGlobal(QPoint(0, self.height()))
        self.suggestion_list.move(global_pos)
        self.suggestion_list.show()
        self.suggestions_visible = True
        self.setFocus()
        
    def complete_text(self, item):
        if not item:
            return
        text = item.text()
        if "(" in text:
            text = text.split("(")[0].strip()
        text = text.replace("<em>", "").replace("</em>", "")
        text = " ".join(text.split())
        text = text.lower().replace(" ", "-")
        text = "".join(c for c in text if c.isalnum() or c == "-")
        text = "-".join(filter(None, text.split("-")))
        self.setText(text)
        self.suggestion_list.hide()
        self.suggestions_visible = False
        self.setFocus()

    def keyPressEvent(self, event):
        if self.suggestions_visible:
            if event.key() == Qt.Key.Key_Down:
                if self.suggestion_list.currentRow() < 0:
                    self.suggestion_list.setCurrentRow(0)
                else:
                    next_row = (self.suggestion_list.currentRow() + 1) % self.suggestion_list.count()
                    self.suggestion_list.setCurrentRow(next_row)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Up:
                if self.suggestion_list.currentRow() < 0:
                    self.suggestion_list.setCurrentRow(self.suggestion_list.count() - 1)
                else:
                    prev_row = (self.suggestion_list.currentRow() - 1) % self.suggestion_list.count()
                    self.suggestion_list.setCurrentRow(prev_row)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Return and self.suggestion_list.currentItem():
                self.complete_text(self.suggestion_list.currentItem())
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Escape:
                self.suggestion_list.hide()
                self.suggestions_visible = False
                event.accept()
                return
        super().keyPressEvent(event)
        
    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self.suggestions_visible:
            self.suggestion_list.show()
        
    def focusOutEvent(self, event):
        QTimer.singleShot(200, self.check_focus)
        super().focusOutEvent(event)
        
    def check_focus(self):
        if not self.hasFocus() and not self.suggestion_list.hasFocus():
            self.suggestion_list.hide()
            self.suggestions_visible = False

class ModernSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QSpinBox {
                background-color: #2d2d2d;
                border: 2px solid #FF6B6B;
                border-radius: 5px;
                color: #ffffff;
                padding: 5px;
                min-width: 100px;
            }
            QSpinBox::up-button {
                background-color: #FF6B6B;
                border-top-right-radius: 3px;
                width: 20px;
                height: 12px;
            }
            QSpinBox::down-button {
                background-color: #FF6B6B;
                border-bottom-right-radius: 3px;
                width: 20px;
                height: 12px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #FF5252;
            }
            QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
                background-color: #FF3939;
            }
            QSpinBox::up-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDE2IDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTggMEwxNiA4SDBMOCAwWiIgZmlsbD0id2hpdGUiLz48L3N2Zz4=);
                width: 12px;
                height: 6px;
            }
            QSpinBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDE2IDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTggOEwwIDBIMTZMOCA4WiIgZmlsbD0id2hpdGUiLz48L3N2Zz4=);
                width: 12px;
                height: 6px;
            }
        """)
        self.setKeyboardTracking(True)
        self.setAccelerated(True)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            self.stepUp()
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self.stepDown()
            event.accept()
        else:
            super().keyPressEvent(event)
            
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.stepUp()
        else:
            self.stepDown()
        event.accept()

class ModernAniWorldGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 ANIMORO Downloader")
        self.setMinimumSize(800, 600)
        
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'animoro.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Warnung: Icon nicht gefunden unter {icon_path}")
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel()
        if os.path.exists(icon_path):
            icon_pixmap = QPixmap(icon_path)
            if not icon_pixmap.isNull():
                icon_label.setPixmap(icon_pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                print("Warnung: Icon konnte nicht geladen werden")
        header_layout.addWidget(icon_label)
        
        header = QLabel("🎬 ANIMORO Downloader")
        header.setStyleSheet("""
            QLabel {
                color: #FF6B6B;
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
                background-color: #1a1a1a;
                border-radius: 10px;
            }
        """)
        header_layout.addWidget(header)
        
        main_layout.addLayout(header_layout)
        
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #FF6B6B;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        search_layout = QVBoxLayout(search_frame)
        
        search_input_layout = QHBoxLayout()
        self.search_input = ModernSearchInput()
        self.search_input.setPlaceholderText("🔍 Anime oder Serie suchen...")
        search_input_layout.addWidget(self.search_input)
        search_layout.addLayout(search_input_layout)
        
        filter_layout = QHBoxLayout()
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Anime", "Serie"])
        self.type_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 2px solid #FF6B6B;
                border-radius: 5px;
                color: #ffffff;
                padding: 5px;
                min-width: 120px;
            }
        """)
        self.type_combo.currentIndexChanged.connect(self.update_search_type)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Deutsch", "Ger-Sub", "English", "Eng-Sub"])
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 2px solid #FF6B6B;
                border-radius: 5px;
                color: #ffffff;
                padding: 5px;
                min-width: 120px;
            }
        """)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["VOE", "Streamtape", "Vidoza"])
        self.provider_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 2px solid #FF6B6B;
                border-radius: 5px;
                color: #ffffff;
                padding: 5px;
                min-width: 120px;
            }
        """)
        
        filter_layout.addWidget(self.type_combo)
        filter_layout.addWidget(self.lang_combo)
        filter_layout.addWidget(self.provider_combo)
        search_layout.addLayout(filter_layout)
        
        main_layout.addWidget(search_frame)
        
        options_frame = QFrame()
        options_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #FF6B6B;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        options_layout = QVBoxLayout(options_frame)
        
        episode_layout = QHBoxLayout()
        
        season_layout = QVBoxLayout()
        season_label = QLabel("📺 Staffel:")
        season_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.season_spin = ModernSpinBox()
        self.season_spin.setMinimum(1)
        self.season_spin.setMaximum(999)
        self.season_spin.setValue(1)
        season_layout.addWidget(season_label)
        season_layout.addWidget(self.season_spin)
        
        episode_layout_v = QVBoxLayout()
        episode_label = QLabel("🎯 Episode:")
        episode_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.episode_spin = ModernSpinBox()
        self.episode_spin.setMinimum(1)
        self.episode_spin.setMaximum(999)
        self.episode_spin.setValue(1)
        episode_layout_v.addWidget(episode_label)
        episode_layout_v.addWidget(self.episode_spin)
        
        episode_layout.addLayout(season_layout)
        episode_layout.addLayout(episode_layout_v)
        options_layout.addLayout(episode_layout)
        
        self.all_episodes_check = QCheckBox("📦 Alle Episoden herunterladen")
        self.all_episodes_check.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
            }
        """)
        self.all_episodes_check.stateChanged.connect(self.toggle_episode_spin)
        options_layout.addWidget(self.all_episodes_check)
        
        main_layout.addWidget(options_frame)
        
        button_layout = QHBoxLayout()
        
        self.download_button = QPushButton("⬇️ Download starten")
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                border: none;
                border-radius: 5px;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF5252;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
            }
        """)
        self.download_button.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_button)
        
        self.help_button = QPushButton("❓ Hilfe")
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 2px solid #FF6B6B;
                border-radius: 5px;
                color: #FF6B6B;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF6B6B;
                color: white;
            }
        """)
        self.help_button.clicked.connect(self.show_help)
        button_layout.addWidget(self.help_button)
        
        main_layout.addLayout(button_layout)
        
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #FF6B6B;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        status_layout = QVBoxLayout(status_frame)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #FF6B6B;
                border-radius: 5px;
                text-align: center;
                background-color: #1a1a1a;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #FF6B6B;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                border: 2px solid #FF6B6B;
                border-radius: 5px;
                color: #ffffff;
                padding: 10px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)
        status_layout.addWidget(self.log_output)
        
        main_layout.addWidget(status_frame)
        
        logging.getLogger().setLevel(logging.INFO)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
        """)

    def toggle_episode_spin(self, state):
        self.episode_spin.setEnabled(not state)

    def show_help(self):
        help_text = """
        <h2>🎮 Wie benutze ich ANIMORO?</h2>
        
        <h3>1️⃣ Suche</h3>
        <p>🔍 - Wähle zwischen "Anime" oder "Serie"</p>
        <p>⌨️ - Gib mindestens 2 Buchstaben ein, um Vorschläge zu sehen</p>
        <p>👆 - Wähle einen Vorschlag aus der Liste</p>
        
        <h3>2️⃣ Sprache & Provider</h3>
        <p>🗣️ - Wähle deine bevorzugte Sprache</p>
        <p>🌐 - Wähle einen Provider (VOE, Streamtape oder Vidoza)</p>
        
        <h3>3️⃣ Download-Optionen</h3>
        <p>📺 - Wähle die gewünschte Staffel</p>
        <p>🎯 - Wähle die gewünschte Episode</p>
        <p>📦 - Aktiviere "Alle Episoden herunterladen" für die komplette Staffel</p>
        
        <h3>4️⃣ Download starten</h3>
        <p>⬇️ - Klicke auf "Download starten"</p>
        <p>📊 - Der Fortschritt wird im Log-Bereich angezeigt</p>
        
        <h3>💡 Tipps</h3>
        <p>⚡ - Die Suche funktioniert auch während die Vorschlagsliste angezeigt wird</p>
        <p>⌨️ - Du kannst die Vorschlagsliste mit den Pfeiltasten navigieren</p>
        <p>❌ - Drücke ESC um die Vorschlagsliste zu schließen</p>
        """
        
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("ANIMORO Hilfe")
        help_dialog.setMinimumWidth(500)
        help_dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton {
                background-color: #FF6B6B;
                border: none;
                border-radius: 5px;
                color: white;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #FF5252;
            }
        """)
        
        layout = QVBoxLayout(help_dialog)
        text_label = QLabel(help_text)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        close_button = QPushButton("Schließen")
        close_button.clicked.connect(help_dialog.accept)
        layout.addWidget(close_button)
        help_dialog.exec()

    def start_download(self):
        name = self.search_input.text()
        if not name:
            self.log_output.append("❌ Status: Fehler - Kein Name angegeben")
            return

        args = {
            "TYPE": self.type_combo.currentText().lower(),
            "NAME": name,
            "LANG": self.lang_combo.currentText(),
            "MODE": "Series",
            "PROVIDER": self.provider_combo.currentText().upper(),
            "SEASON": str(self.season_spin.value()),
            "EPISODE": str(self.episode_spin.value())
        }

        if self.all_episodes_check.isChecked():
            args["MODE"] = "All"
            args["EPISODE"] = "0"

        self.download_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.log_output.append("🚀 Status: Download läuft...")
        if self.all_episodes_check.isChecked():
            self.log_output.append(f"📥 Starte Download für: {name} - Komplette Staffel {args['SEASON']}")
        else:
            self.log_output.append(f"📥 Starte Download für: {name} - Staffel {args['SEASON']} Episode {args['EPISODE']}")

        self.scraper_thread = ScraperThread(args)
        self.scraper_thread.progress.connect(self.update_log)
        self.scraper_thread.finished.connect(self.download_finished)
        self.scraper_thread.start()

    def update_log(self, message):
        self.log_output.append(f"📝 {message}")

    def download_finished(self):
        self.download_button.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.log_output.append("✅ Status: Download abgeschlossen")

    def update_search_type(self, index):
        search_type = "Anime" if self.type_combo.currentText() == "Anime" else "Serie"
        self.search_input.search_type = search_type
        self.search_input.clear()
        self.search_input.setPlaceholderText(f"🔍 {search_type} suchen...")

def main():
    minimize_console()
    app = QApplication(sys.argv)
    
    splash = SplashScreen()
    
    # Center the splash screen
    screen = app.primaryScreen()
    screen_geometry = screen.availableGeometry()
    splash.move(
        (screen_geometry.width() - splash.width()) // 2,
        (screen_geometry.height() - splash.height()) // 2
    )
    
    splash.show()
    
    total_duration = 3.0
    steps = 100
    step_duration = total_duration / steps
    
    for i in range(steps + 1):
        splash.progress.setValue(i)
        app.processEvents()
        time.sleep(step_duration)
    
    window = ModernAniWorldGUI()
    window.show()
    splash.finish(window)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()