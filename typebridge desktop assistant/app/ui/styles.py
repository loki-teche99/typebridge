"""
TypeBridge Desktop - Modern Premium UI Stylesheet
High-polish dark interface with restrained indigo/cyan accents & seamless card integration.
"""

def get_stylesheet(theme: str = 'dark') -> str:
    if theme == 'light':
        return """
            QMainWindow, QDialog {
                background-color: #f8fafc;
            }
            QWidget {
                color: #0f172a;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel {
                background: transparent;
                color: #0f172a;
            }
            QFrame#card {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 14px;
            }
            QLabel#appTitle {
                font-size: 22px;
                font-weight: 800;
                color: #0f172a;
                background: transparent;
            }
            QLabel#statusBadge {
                font-size: 12px;
                font-weight: 700;
                padding: 5px 14px;
                border-radius: 14px;
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                color: #475569;
            }
            QLabel#dimLabel {
                color: #64748b;
                font-size: 13px;
                background: transparent;
            }
            QPushButton#primaryBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #0284c7);
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                border: none;
                border-radius: 8px;
                padding: 9px 18px;
            }
            QPushButton#primaryBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #0369a1);
            }
            QPushButton#secondaryBtn {
                background-color: #ffffff;
                color: #334155;
                font-size: 13px;
                font-weight: 600;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #f8fafc;
                border: 1px solid #38bdf8;
                color: #0284c7;
            }
            QPushButton#dangerBtn {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 700;
            }
            QPushButton#dangerBtn:hover {
                background-color: #dc2626;
            }
            QProgressBar {
                background-color: #e2e8f0;
                border: none;
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #06b6d4);
                border-radius: 4px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #e2e8f0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4f46e5;
                border: 2px solid #ffffff;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #4338ca;
            }
            QScrollBar:vertical {
                background: #f1f5f9;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 4px;
                min-height: 24px;
            }
        """

    # Dark Theme (Default) — Premium Dark with Restrained Indigo/Cyan
    return """
        QMainWindow, QDialog {
            background-color: #0b0f19;
        }
        QWidget {
            color: #f1f5f9;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        }
        QLabel {
            background: transparent;
            color: #f1f5f9;
        }
        QFrame#card {
            background-color: #111827;
            border: 1px solid rgba(56, 189, 248, 0.18);
            border-radius: 12px;
            padding: 16px;
        }
        QLabel#appTitle {
            font-size: 26px;
            font-weight: 900;
            color: #ffffff;
            letter-spacing: 0.5px;
            background: transparent;
        }
        QLabel#statusBadge {
            font-size: 12px;
            font-weight: 700;
            padding: 5px 14px;
            border-radius: 14px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #f87171;
        }
        QLabel#statusBadge[connected="true"] {
            background: rgba(16, 185, 129, 0.18);
            border: 1px solid rgba(16, 185, 129, 0.5);
            color: #34d399;
            font-weight: 800;
        }
        QLabel#dimLabel {
            color: #94a3b8;
            font-size: 13px;
            background: transparent;
        }
        QPushButton#primaryBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:0.5 #3b82f6, stop:1 #06b6d4);
            color: #ffffff;
            font-size: 13px;
            font-weight: 700;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
        }
        QPushButton#primaryBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:0.5 #60a5fa, stop:1 #22d3ee);
        }
        QPushButton#primaryBtn:pressed {
            background: #4338ca;
        }
        QPushButton#secondaryBtn {
            background-color: #1e293b;
            color: #e2e8f0;
            font-size: 13px;
            font-weight: 600;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 8px 16px;
        }
        QPushButton#secondaryBtn:hover {
            background-color: #24344d;
            border: 1px solid #38bdf8;
            color: #38bdf8;
        }
        QPushButton#dangerBtn {
            background-color: rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            border: 1px solid rgba(239, 68, 68, 0.4);
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 700;
        }
        QPushButton#dangerBtn:hover {
            background-color: #ef4444;
            color: #ffffff;
        }
        QProgressBar {
            background-color: #1e293b;
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #10b981);
            border-radius: 4px;
        }
        QSlider::groove:horizontal {
            height: 6px;
            background: #1e293b;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #38bdf8;
            border: 2px solid #0f172a;
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        QSlider::handle:horizontal:hover {
            background: #7dd3fc;
        }
        QTextEdit, QLineEdit {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 8px;
            color: #f1f5f9;
        }
        QTextEdit:focus, QLineEdit:focus {
            border: 1px solid #38bdf8;
        }
        QScrollBar:vertical {
            background: #0b0f19;
            width: 8px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #1e293b;
            border-radius: 4px;
            min-height: 24px;
        }
        QScrollBar::handle:vertical:hover {
            background: #334155;
        }
    """
