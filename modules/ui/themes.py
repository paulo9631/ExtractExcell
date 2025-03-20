# modules/themes.py

from PyQt6.QtWidgets import QStyleFactory
from PyQt6.QtGui import QPalette, QColor

class Temas:
    @staticmethod
    def tema_claro(app):
        app.setStyle(QStyleFactory.create("Fusion"))
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(248, 250, 252))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(15, 23, 42))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(241, 245, 249))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(15, 23, 42))
        palette.setColor(QPalette.ColorRole.Text, QColor(15, 23, 42))
        palette.setColor(QPalette.ColorRole.Button, QColor(241, 245, 249))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(15, 23, 42))
        palette.setColor(QPalette.ColorRole.Link, QColor(37, 99, 235))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(37, 99, 235))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)

        style = """
            QMainWindow { background-color: #f8fafc; }
            QLabel { font-size: 14px; color: #0f172a; }
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #334155;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 15px;
                padding: 15px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                background-color: #ffffff;
            }
            QComboBox {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 15px;
                background-color: #f8fafc;
                color: #334155;
                min-height: 40px;
                font-size: 14px;
            }
            QComboBox:hover {
                border-color: #94a3b8;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background-color: #ffffff;
                selection-background-color: #e2e8f0;
                selection-color: #334155;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            QPushButton:disabled {
                background-color: #94a3b8;
                color: #e2e8f0;
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                text-align: center;
                background-color: #e2e8f0;
                color: transparent;
                height: 12px;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                 stop:0 #3b82f6, stop:1 #2563eb);
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f1f5f9;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #94a3b8;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #64748b;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QStatusBar {
                background-color: #f8fafc;
                color: #64748b;
                border-top: 1px solid #e2e8f0;
                padding: 4px;
                font-size: 13px;
            }
            QToolBar {
                background-color: #f8fafc;
                border-bottom: 1px solid #e2e8f0;
                spacing: 10px;
                padding: 5px 10px;
            }
            QToolButton {
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QToolButton:hover {
                background-color: #e2e8f0;
            }
            QToolButton:pressed {
                background-color: #cbd5e1;
            }
            QMenuBar {
                background-color: #f8fafc;
                color: #334155;
                border-bottom: 1px solid #e2e8f0;
            }
            QMenuBar::item {
                padding: 6px 10px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background-color: #e2e8f0;
                border-radius: 4px;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 25px 6px 20px;
                border-radius: 4px;
                margin: 2px 5px;
            }
            QMenu::item:selected {
                background-color: #e2e8f0;
            }
            QSlider {
                height: 30px;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background-color: #e2e8f0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background-color: #3b82f6;
                border: none;
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #2563eb;
            }
            QSlider::sub-page:horizontal {
                background-color: #93c5fd;
                border-radius: 4px;
            }
            QSplitter::handle {
                background-color: #e2e8f0;
                border-radius: 4px;
            }
            QSplitter::handle:hover {
                background-color: #cbd5e1;
            }
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f1f5f9;
                color: #64748b;
                border: 1px solid #e2e8f0;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #2563eb;
                border-bottom: 2px solid #2563eb;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e2e8f0;
            }
            QMessageBox {
                background-color: #ffffff;
            }
            QMessageBox QLabel {
                color: #334155;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                min-width: 100px;
            }
            QMessageBox QPushButton:hover {
                background-color: #1d4ed8;
            }
        """
        return style

    @staticmethod
    def tema_escuro(app):
        app.setStyle(QStyleFactory.create("Fusion"))
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(15, 23, 42))         # Slate 900
        palette.setColor(QPalette.ColorRole.WindowText, QColor(241, 245, 249))  # Slate 100
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 41, 59))           # Slate 800
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(51, 65, 85))  # Slate 700
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(15, 23, 42))    # Slate 900
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(241, 245, 249)) # Slate 100
        palette.setColor(QPalette.ColorRole.Text, QColor(241, 245, 249))        # Slate 100
        palette.setColor(QPalette.ColorRole.Button, QColor(30, 41, 59))         # Slate 800
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(241, 245, 249))  # Slate 100
        palette.setColor(QPalette.ColorRole.Link, QColor(96, 165, 250))         # Blue 400
        palette.setColor(QPalette.ColorRole.Highlight, QColor(59, 130, 246))    # Blue 500
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(241, 245, 249)) # Slate 100
        app.setPalette(palette)

        style = """
            QMainWindow { 
                background-color: #0f172a; 
            }
            QLabel { 
                font-size: 14px; 
                color: #f1f5f9; 
            }
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 12px;
                margin-top: 15px;
                padding: 15px;
                background-color: #1e293b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                background-color: #1e293b;
            }
            QComboBox {
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 8px 15px;
                background-color: #334155;
                color: #f1f5f9;
                min-height: 40px;
                font-size: 14px;
            }
            QComboBox:hover {
                border-color: #60a5fa;
                background-color: #3b4a63;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #475569;
                border-radius: 8px;
                background-color: #1e293b;
                selection-background-color: #334155;
                selection-color: #f1f5f9;
            }
            QPushButton {
                background-color: #3b82f6;
                color: #f1f5f9;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #475569;
                color: #94a3b8;
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                text-align: center;
                background-color: #334155;
                color: transparent;
                height: 12px;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                 stop:0 #3b82f6, stop:1 #60a5fa);
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #1e293b;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #475569;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #60a5fa;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QStatusBar {
                background-color: #0f172a;
                color: #94a3b8;
                border-top: 1px solid #1e293b;
                padding: 4px;
                font-size: 13px;
            }
            QToolBar {
                background-color: #1e293b;
                border-bottom: 1px solid #334155;
                spacing: 10px;
                padding: 5px 10px;
            }
            QToolButton {
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QToolButton:hover {
                background-color: #334155;
            }
            QToolButton:pressed {
                background-color: #475569;
            }
            QMenuBar {
                background-color: #1e293b;
                color: #e2e8f0;
                border-bottom: 1px solid #334155;
            }
            QMenuBar::item {
                padding: 6px 10px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background-color: #334155;
                border-radius: 4px;
            }
            QMenu {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 25px 6px 20px;
                border-radius: 4px;
                margin: 2px 5px;
                color: #e2e8f0;
            }
            QMenu::item:selected {
                background-color: #334155;
            }
            QSlider {
                height: 30px;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background-color: #334155;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background-color: #3b82f6;
                border: none;
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #60a5fa;
            }
            QSlider::sub-page:horizontal {
                background-color: #2563eb;
                border-radius: 4px;
            }
            QSplitter::handle {
                background-color: #334155;
                border-radius: 4px;
            }
            QSplitter::handle:hover {
                background-color: #475569;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 8px;
                background-color: #1e293b;
            }
            QTabBar::tab {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #334155;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 16px;
                margin-right: 2px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background-color: #1e293b;
                color: #60a5fa;
                border-bottom: 2px solid #3b82f6;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #1e293b;
                color: #e2e8f0;
            }
            QMessageBox {
                background-color: #1e293b;
            }
            QMessageBox QLabel {
                color: #f1f5f9;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                background-color: #3b82f6;
                color: #f1f5f9;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                min-width: 100px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2563eb;
            }
        """
        return style