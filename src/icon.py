from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath, QFont, QIcon, QPixmap
from PyQt6.QtCore import Qt, QSize

def create_icon():
    # Erstelle verschiedene Icon-Größen
    sizes = [16, 32, 48, 64, 128, 256]
    icon = QIcon()
    
    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Hintergrund mit Gradient
        path = QPainterPath()
        path.addRoundedRect(0, 0, size, size, size/8, size/8)
        
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, QColor("#2d2a44"))
        gradient.setColorAt(1, QColor("#1d1b34"))
        painter.fillPath(path, gradient)
        
        # "A" mit Gradient
        text_gradient = QLinearGradient(0, 0, size, size)
        text_gradient.setColorAt(0, QColor("#89a5df"))
        text_gradient.setColorAt(0.5, QColor("#e46e7f"))
        text_gradient.setColorAt(1, QColor("#e8e191"))
        
        font = QFont("Segoe UI")
        font.setPointSize(int(size/2))
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        
        text_path = QPainterPath()
        text_path.addText(
            size/2 - painter.fontMetrics().horizontalAdvance("A") / 2,
            size/2 + painter.fontMetrics().height() / 3,
            font, "A"
        )
        
        # Schatten
        painter.setPen(Qt.PenStyle.NoPen)
        shadow_path = QPainterPath(text_path)
        shadow_path.translate(size/32, size/32)
        painter.fillPath(shadow_path, QColor(0, 0, 0, 40))
        
        # Text
        painter.fillPath(text_path, text_gradient)
        painter.end()
        
        icon.addPixmap(pixmap)
    
    return icon

if __name__ == "__main__":
    # Speichere das Icon als ICO-Datei
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    icon = create_icon()
    
    # Speichere alle Größen
    pixmaps = []
    for size in [16, 32, 48, 64, 128, 256]:
        pixmap = icon.pixmap(QSize(size, size))
        pixmaps.append(pixmap)
        # Speichere auch einzelne PNG-Dateien für Debug-Zwecke
        pixmap.save(f"icon_{size}.png")
    
    # Speichere die ICO-Datei mit allen Größen
    pixmaps[5].save("animoro.ico")  # Die größte Version als ICO 