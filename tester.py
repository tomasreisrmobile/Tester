import re
import sys
import time
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    import serial  # pyserial
except Exception:
    serial = None


def normalize_hex(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return value.upper()


def parse_mapping_line(line: str):
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    # Supports:
    # 0x1B    [ Escape ]   1   1
    # 0x70    F1           1   2
    m = re.match(r"^\s*(0x[0-9a-fA-F]+|[0-9a-fA-F]+)\s+(.+?)\s+(\d+)\s+(\d+)\s*$", raw)
    if not m:
        return None

    hex_code = normalize_hex(m.group(1))
    key_name = m.group(2).strip()
    card = int(m.group(3))
    valve = int(m.group(4))
    return hex_code, key_name, card, valve


def load_mapping(path: Path):
    mapping = {}
    bad_lines = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        parsed = parse_mapping_line(line)
        if parsed is None:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                bad_lines.append(idx)
            continue
        hex_code, key_name, card, valve = parsed
        mapping[hex_code] = (key_name, card, valve)
    return mapping, bad_lines


def discover_profiles(profiles_dir: Path):
    return sorted([p.stem for p in profiles_dir.glob("*.txt") if p.is_file()])


class TesterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keyboard -> Arduino Tester")
        self.setMinimumSize(760, 520)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.project_root = Path(__file__).resolve().parent
        self.profiles_dir = self.project_root / "Keyboards"
        self.state_file = self.project_root / ".selected_keyboard"

        self.mapping = {}
        self.serial_port = None
        self.running = False
        self.last_fire_at = 0.0

        self.profile_combo = QComboBox()
        self.port_edit = QLineEdit("/dev/ttyACM0")
        self.baud_edit = QLineEdit("115200")
        self.on_spin = QSpinBox()
        self.on_spin.setRange(1, 20000)
        self.on_spin.setValue(200)
        self.off_spin = QSpinBox()
        self.off_spin.setRange(1, 20000)
        self.off_spin.setValue(200)
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.status_label = QLabel("Status: Ready")
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self._build_ui()
        self._load_profiles()
        self._wire()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        form = QFormLayout()
        form.addRow("Keyboard profile:", self.profile_combo)
        form.addRow("Arduino USB port:", self.port_edit)
        form.addRow("Baud:", self.baud_edit)
        form.addRow("Valve ON (ms):", self.on_spin)
        form.addRow("Pause OFF (ms):", self.off_spin)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.stop_btn)

        layout = QVBoxLayout(central)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log)

    def _wire(self):
        self.start_btn.clicked.connect(self.start_test)
        self.stop_btn.clicked.connect(self.stop_test)
        self.profile_combo.currentTextChanged.connect(self._store_selected_profile)

    def _load_profiles(self):
        self.profile_combo.clear()
        profiles = discover_profiles(self.profiles_dir)
        if not profiles:
            self.log_line(f"No profiles found in: {self.profiles_dir}")
            return

        self.profile_combo.addItems(profiles)

        last = None
        if self.state_file.exists():
            last = self.state_file.read_text(encoding="utf-8").strip()
        if last and last in profiles:
            self.profile_combo.setCurrentText(last)
        else:
            self._store_selected_profile(self.profile_combo.currentText())

    def _store_selected_profile(self, name: str):
        if not name:
            return
        self.state_file.write_text(name + "\n", encoding="utf-8")

    def log_line(self, text: str):
        self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def set_status(self, text: str):
        self.status_label.setText(f"Status: {text}")

    def _open_serial(self, port: str, baud: int):
        if serial is None:
            raise RuntimeError("Missing dependency: pyserial (pip install pyserial)")
        ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2.0)  # Arduino reset after USB open.
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        return ser

    def start_test(self):
        if self.running:
            return

        profile_name = self.profile_combo.currentText().strip()
        if not profile_name:
            QMessageBox.warning(self, "Missing profile", "Vyber klavesnicu zo zoznamu.")
            return

        map_path = self.profiles_dir / f"{profile_name}.txt"
        if not map_path.exists():
            QMessageBox.critical(self, "Missing mapping", f"Subor neexistuje:\n{map_path}")
            return

        mapping, bad_lines = load_mapping(map_path)
        if not mapping:
            QMessageBox.critical(self, "Invalid mapping", "V TXT neboli najdene validne riadky.")
            return

        try:
            port = self.port_edit.text().strip()
            baud = int(self.baud_edit.text().strip())
            ser = self._open_serial(port, baud)
            ser.write(b"PING\n")
            ser.flush()
            pong = ser.readline().decode("utf-8", errors="replace").strip()
        except Exception as exc:
            QMessageBox.critical(self, "Arduino connection error", str(exc))
            return

        self.mapping = mapping
        self.serial_port = ser
        self.running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.set_status(f"Running ({profile_name})")

        self.log_line(f"Selected profile: {profile_name}")
        self.log_line(f"Loaded mappings: {len(mapping)}")
        if bad_lines:
            self.log_line(f"Skipped malformed lines: {bad_lines}")
        self.log_line(f"Arduino handshake: {pong if pong else '(no response)'}")
        self.log_line("Test started. Press keys now.")
        self.activateWindow()
        self.setFocus()

    def stop_test(self):
        if not self.running:
            return
        try:
            self.serial_port.write(b"RESET\n")
            self.serial_port.flush()
            _ = self.serial_port.readline()
        except Exception:
            pass
        try:
            self.serial_port.close()
        except Exception:
            pass
        self.serial_port = None
        self.mapping = {}
        self.running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.set_status("Stopped")
        self.log_line("Test stopped.")

    def keyPressEvent(self, event: QKeyEvent):
        super().keyPressEvent(event)

        if not self.running or self.serial_port is None:
            return

        now = time.time()
        if now - self.last_fire_at < 0.05:
            return

        vk = event.nativeVirtualKey()
        if not isinstance(vk, int) or vk <= 0:
            return

        vk_hex = normalize_hex(f"{vk:X}")
        mapping = self.mapping.get(vk_hex)
        if mapping is None:
            self.log_line(f"No mapping for 0x{vk_hex}")
            return

        key_name, card, valve = mapping
        on_ms = self.on_spin.value()
        off_ms = self.off_spin.value()

        cmd = f"FIRE {card} {valve} {on_ms} {off_ms}\n"
        try:
            self.serial_port.write(cmd.encode("ascii"))
            self.serial_port.flush()
            response = self.serial_port.readline().decode("utf-8", errors="replace").strip()
        except Exception as exc:
            self.log_line(f"Serial error: {exc}")
            self.stop_test()
            return

        self.log_line(f"0x{vk_hex} {key_name} -> card {card}, valve {valve} | {response}")
        self.last_fire_at = now

    def closeEvent(self, event):
        self.stop_test()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    win = TesterWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
