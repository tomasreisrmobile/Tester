import sys
from PyQt6.QtWidgets import QApplication, QWidget, QFileDialog
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt


KEYS = [
    ("ESC", 36, 28, 60, 60),
    ("F1", 120, 28, 60, 60),
    ("F2", 205, 28, 60, 60),
    ("F3", 290, 28, 60, 60),
    ("F4", 375, 28, 60, 60),
    ("F5", 458, 28, 60, 60),
    ("F6", 540, 30, 60, 60),
    ("F7", 622, 30, 60, 60),
    ("F8", 707, 31, 60, 60),
    ("F9", 787, 31, 60, 60),
    ("F10", 870, 31, 60, 60),
    ("F11", 950, 32, 60, 60),
    ("F12", 1035, 32, 60, 60),

    ("1", 77, 104, 60, 60),
    ("2", 162, 104, 60, 60),
    ("3", 247, 104, 60, 60),
    ("4", 332, 105, 60, 60),
    ("5", 416, 105, 60, 60),
    ("6", 497, 106, 60, 60),
    ("7", 580, 106, 60, 60),
    ("8", 661, 106, 60, 60),
    ("9", 742, 107, 60, 60),
    ("0", 827, 107, 60, 60),
]


class Tester(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Keyboard Tester")
        self.setFixedSize(1200, 500)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        file, _ = QFileDialog.getOpenFileName(self, "Vyber obrázok klávesnice")

        if not file:
            sys.exit()

        self.pixmap = QPixmap(file)

        self.index = 0
        self.results = []  # (index očakávaného klávesu, True/False)
        self.test_finished = False

    def keyPressEvent(self, event):
        if self.test_finished:
            return

        key_map = {
            Qt.Key.Key_Escape: "ESC",
            Qt.Key.Key_F1: "F1",
            Qt.Key.Key_F2: "F2",
            Qt.Key.Key_F3: "F3",
            Qt.Key.Key_F4: "F4",
            Qt.Key.Key_F5: "F5",
            Qt.Key.Key_F6: "F6",
            Qt.Key.Key_F7: "F7",
            Qt.Key.Key_F8: "F8",
            Qt.Key.Key_F9: "F9",
            Qt.Key.Key_F10: "F10",
            Qt.Key.Key_F11: "F11",
            Qt.Key.Key_F12: "F12",
        }

        pressed = event.text().upper()

        if pressed == "":
            pressed = key_map.get(event.key(), None)

        if not pressed:
            return

        expected = KEYS[self.index][0]

        if pressed == expected:
            self.results.append((self.index, True))
            self.index += 1
        else:
            self.results.append((self.index, False))

        if self.index == len(KEYS):
            self.test_finished = True

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.drawPixmap(self.rect(), self.pixmap)

        for i, (key, x, y, w, h) in enumerate(KEYS):

            # default
            color = QColor(0, 0, 255, 40)

            # aktuálny očakávaný kláves
            if i == self.index and not self.test_finished:
                color = QColor(255, 255, 0, 80)

            # výsledky
            for idx, ok in self.results:
                if idx == i:
                    if ok:
                        color = QColor(0, 255, 0, 120)
                    else:
                        color = QColor(255, 0, 0, 120)

            painter.setBrush(color)
            painter.drawRect(x, y, w, h)

        painter.setFont(QFont("Arial", 20))

        if not self.test_finished:
            painter.setBrush(QColor(0, 0, 255, 120))
            painter.drawRect(0, 450, 1200, 50)
            painter.drawText(20, 485, f"TESTUJEM... ({self.index}/{len(KEYS)})")

        else:
            ok_count = sum(1 for r in self.results if r[1])
            fail_count = len(self.results) - ok_count

            if fail_count == 0:
                painter.setBrush(QColor(0, 255, 0, 150))
            else:
                painter.setBrush(QColor(255, 0, 0, 150))

            painter.drawRect(0, 450, 1200, 50)
            painter.drawText(20, 485, f"OK: {ok_count}   FAIL: {fail_count}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Tester()
    win.show()
    sys.exit(app.exec())