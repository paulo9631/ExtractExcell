from PyQt6.QtCore import Qt, QSize, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

class IconProvider:
    ICONS = {
        "folder": '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M10 4H2v16h20V6H12l-2-2z" fill="currentColor"/></svg>',
        "process": '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 8a4 4 0 100 8 4 4 0 000-8z" fill="currentColor"/><path d="M20.94 11a1 1 0 00-.34-.74l-1.43-1.43a1 1 0 00-.74-.34 7.94 7.94 0 00-1.66-.11 7.94 7.94 0 00-1.66.11 1 1 0 00-.74.34L11.4 10.26a1 1 0 00-.34.74 7.94 7.94 0 00-.11 1.66c.03.55.11 1.09.11 1.66a7.94 7.94 0 00-.11 1.66 1 1 0 00.34.74l1.43 1.43a1 1 0 00.74.34c.55.03 1.09.11 1.66.11.55 0 1.09-.03 1.66-.11a1 1 0 00.74-.34l1.43-1.43a1 1 0 00.34-.74 7.94 7.94 0 00.11-1.66c0-.55-.03-1.09-.11-1.66a7.94 7.94 0 00.11-1.66z" fill="currentColor"/></svg>',
        "excel": '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" fill="currentColor"/><text x="12" y="16" font-size="8" text-anchor="middle" fill="#fff">XLS</text></svg>',
        "chart": '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><rect x="4" y="10" width="4" height="10" fill="currentColor"/><rect x="10" y="6" width="4" height="14" fill="currentColor"/><rect x="16" y="2" width="4" height="18" fill="currentColor"/></svg>',
        "close": '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><line x1="4" y1="4" x2="20" y2="20" stroke="currentColor" stroke-width="2"/><line x1="20" y1="4" x2="4" y2="20" stroke="currentColor" stroke-width="2"/></svg>',
        "file": '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" fill="currentColor"/><polyline points="14 2 14 8 20 8" fill="none" stroke="#fff" stroke-width="2"/></svg>',
        "question": '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="currentColor"/><path d="M12 16v-4" stroke="#fff" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="18" r="1" fill="#fff"/></svg>',
        "info": '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="currentColor"/><line x1="12" y1="16" x2="12" y2="12" stroke="#fff" stroke-width="2"/><circle cx="12" cy="8" r="1" fill="#fff"/></svg>'
    }

    @staticmethod
    def get_icon(name, color="#000000", size=24):
        if name not in IconProvider.ICONS:
            return QIcon()

        svg_content = IconProvider.ICONS[name].replace('currentColor', color)
        svg_data = QByteArray(svg_content.encode("utf-8"))
        renderer = QSvgRenderer(svg_data)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def get_colored_icon(name, color="#000000", size=24):
        return IconProvider.get_icon(name, color, size)