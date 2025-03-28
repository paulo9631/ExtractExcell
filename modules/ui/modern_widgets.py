from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QRect, QTimer, pyqtProperty
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen, QFont
from PyQt6.QtWidgets import (
    QPushButton, QProgressBar, QFrame, QHBoxLayout, QVBoxLayout,
    QLabel, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect, QWidget
)

from .icon_provider import IconProvider

class ModernButton(QPushButton):
    """Botão moderno com efeitos de hover e estilo profissional."""
    def __init__(self, text, icon=None, primary=True, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        
        if isinstance(icon, QIcon):
            self.setIcon(icon)
            self.setIconSize(QSize(20, 20))
        elif isinstance(icon, str):
            color = "#ffffff" if primary else "#4a90e2"
            self.setIcon(IconProvider.get_icon(icon, color))
            self.setIconSize(QSize(20, 20))
        
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.update_style()

    def update_style(self):
        """
        Ajusta o estilo do botão. Caso seja primário, usamos o gradiente verde (#10b981).
        Caso seja secundário, usamos o estilo cinza-azul.
        """
        if self.primary:
            self.setStyleSheet("""
                QPushButton {
                    /* Gradiente principal: #10b981 → #059669 */
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #10b981, stop:1 #059669);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    /* Gradiente hover: #059669 → #047857 */
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #059669, stop:1 #047857);
                }
                QPushButton:pressed {
                    background: #047857;
                }
                QPushButton:disabled {
                    background: #94a3b8;
                    color: #e2e8f0;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9;
                    color: #4a90e2;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e2e8f0;
                }
                QPushButton:pressed {
                    background-color: #cbd5e1;
                }
                QPushButton:disabled {
                    background-color: #f8fafc;
                    color: #94a3b8;
                }
            """)


class ModernProgressBar(QProgressBar):
    """Barra de progresso moderna com animação de gradiente."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(True)
        self.setMinimumHeight(12)
        self.setMaximumHeight(12)
        self.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #e2e8f0;
                text-align: center;
                color: transparent;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                /* Gradiente verde do chunk */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #10b981, stop:1 #059669);
            }
        """)
        
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_offset = 0
        
    def update_animation(self):
        """Animação de gradiente quando o valor está entre 1% e 99%."""
        if self.value() > 0 and self.value() < 100:
            self.animation_offset = (self.animation_offset + 1) % 100
            gradient = f"""
                QProgressBar::chunk {{
                    border-radius: 6px;
                    background: qlineargradient(
                        x1:{self.animation_offset/100}, y1:0, 
                        x2:{(self.animation_offset+100)/100}, y2:0,
                        stop:0 #10b981, stop:0.5 #059669, stop:1 #10b981
                    );
                }}
            """
            self.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 6px;
                    background-color: #e2e8f0;
                    text-align: center;
                    color: transparent;
                }
            """ + gradient)
        else:
            self.animation_timer.stop()
            self.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 6px;
                    background-color: #e2e8f0;
                    text-align: center;
                    color: transparent;
                }
                QProgressBar::chunk {
                    border-radius: 6px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #10b981, stop:1 #059669);
                }
            """)

    def setValue(self, value):
        super().setValue(value)
        if 0 < value < 100 and not self.animation_timer.isActive():
            self.animation_timer.start(50)
        elif (value == 0 or value == 100) and self.animation_timer.isActive():
            self.animation_timer.stop()
            self.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 6px;
                    background-color: #e2e8f0;
                    text-align: center;
                    color: transparent;
                    height: 12px;
                }
                QProgressBar::chunk {
                    border-radius: 6px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #10b981, stop:1 #059669);
                }
            """)


class InfoCard(QFrame):
    """
    Card de informação com efeito glass e ícone.
    Possui métodos set_title e set_value para alterar texto/título de forma segura.
    """
    def __init__(self, title, value, icon_name=None, color="#4a90e2", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        self.setStyleSheet(f"""
            InfoCard {{
                background-color: rgba(255, 255, 255, 0.75);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.8);
                padding: 5px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        if icon_name:
            icon = IconProvider.get_colored_icon(icon_name, color, 32)
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(QSize(32, 32)))
            layout.addWidget(icon_label)
        else:
            icon_widget = QWidget()
            icon_widget.setFixedSize(32, 32)
            icon_widget.setStyleSheet(f"""
                background-color: {color};
                border-radius: 8px;
            """)
            layout.addWidget(icon_widget)

        text_layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 14px; color: #666;")
        
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet("font-size: 20px; color: #333; font-weight: bold;")
        
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.value_label)
        layout.addLayout(text_layout)

        layout.addItem(QSpacerItem(
            0, 0,
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        ))

    def set_title(self, new_title: str):
        """Atualiza o texto do título."""
        self.title_label.setText(new_title)

    def set_value(self, new_value):
        """Atualiza o texto do valor."""
        self.value_label.setText(str(new_value))


class AnimatedToggle(QWidget):
    """Toggle switch animado para alternar entre estados."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setFixedSize(60, 30)
        self._enabled = False
        self._track_color = QColor("#e2e8f0")
        self._thumb_color = QColor("#94a3b8")
        self._track_color_enabled = QColor("#93c5fd")
        self._thumb_color_enabled = QColor("#3b82f6")
        
        self._thumb_position = 4
        self._animation = QPropertyAnimation(self, b"thumb_position")
        self._animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        self._animation.setDuration(350)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    @pyqtProperty(int)
    def thumb_position(self):
        return self._thumb_position
    
    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        track_color = self._track_color_enabled if self._enabled else self._track_color
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        
        thumb_color = self._thumb_color_enabled if self._enabled else self._thumb_color
        painter.setBrush(thumb_color)
        painter.drawEllipse(
            self._thumb_position,
            4,
            self.height() - 8,
            self.height() - 8
        )
    
    def mousePressEvent(self, event):
        self._enabled = not self._enabled
        target_position = self.width() - self.height() + 4 if self._enabled else 4
        
        self._animation.setStartValue(self._thumb_position)
        self._animation.setEndValue(target_position)
        self._animation.start()
        
        self.clicked.emit()
    
    def is_enabled(self):
        return self._enabled
    
    def set_enabled(self, enabled):
        if self._enabled != enabled:
            self._enabled = enabled
            target_position = self.width() - self.height() + 4 if self._enabled else 4
            
            self._animation.setStartValue(self._thumb_position)
            self._animation.setEndValue(target_position)
            self._animation.start()
    
    clicked = pyqtProperty(bool, is_enabled, set_enabled)


class GlassCard(QFrame):
    """Card com efeito de vidro (glassmorphism)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
        
        self.setStyleSheet("""
            GlassCard {
                background-color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.8);
                border-radius: 16px;
            }
        """)


class CircularProgressBar(QWidget):
    """Barra de progresso circular animada."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(100, 100)
        self._value = 0
        self._max_value = 100
        self._color = QColor("#10b981")
        self._bg_color = QColor("#e2e8f0")

    def set_value(self, value):
        self._value = value
        self.update()
        
    def paintEvent(self, event):
        width = self.width()
        height = self.height()
        size = min(width, height)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bg_color)
        painter.drawEllipse(
            (width - size) // 2,
            (height - size) // 2,
            size,
            size
        )
        
        painter.setPen(QPen(self._color, 10, Qt.PenStyle.SolidLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        rect = QRect(
            (width - size + 10) // 2,
            (height - size + 10) // 2,
            size - 10,
            size - 10
        )
        
        angle = self._value * 360 / self._max_value
        painter.drawArc(rect, 90 * 16, -angle * 16)
        
        painter.setPen(self._color)
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self._value}%")


class PulseEffect(QWidget):
    """Widget com efeito de pulso para chamar atenção."""
    def __init__(self, widget, parent=None):
        super().__init__(parent)
        self.widget = widget
        self.animation = QPropertyAnimation(self, b"pulse_scale")
        self.animation.setDuration(1000)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(1.1)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.setLoopCount(-1)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(widget)
        
        self._pulse_scale = 1.0
        
    @pyqtProperty(float)
    def pulse_scale(self):
        return self._pulse_scale
    
    @pulse_scale.setter
    def pulse_scale(self, scale):
        self._pulse_scale = scale
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(16, 185, 129, 50)) 
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) / 2 * self._pulse_scale
        
        painter.drawEllipse(
            center_x - radius,
            center_y - radius,
            radius * 2,
            radius * 2
        )
    
    def start_animation(self):
        self.animation.start()
    
    def stop_animation(self):
        self.animation.stop()
