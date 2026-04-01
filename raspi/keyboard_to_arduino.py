#!/usr/bin/env python3
"""
Read keyboard mapping from TXT and send valve commands to Arduino Mega over USB.

TXT format (one key per line):
  <hex> <tab> <key_name> <tab> <card_number> <tab> <valve_number>

Example:
  0x1B    Escape    1    1
  0x70    F1        1    2
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

try:
    import serial  # pyserial
except Exception as exc:
    print(f"Missing dependency: pyserial ({exc})")
    print("Install with: pip install pyserial")
    raise SystemExit(1)

try:
    from pynput import keyboard
except Exception as exc:
    print(f"Missing dependency: pynput ({exc})")
    print("Install with: pip install pynput")
    raise SystemExit(1)


def normalize_hex(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    return value.upper()


def parse_mapping_line(line: str):
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    # Accept mixed tabs/spaces and labels like "[ Escape ]".
    # Format: <hex> <label...> <card> <valve>
    m = re.match(r"^\s*(0x[0-9a-fA-F]+|[0-9a-fA-F]+)\s+(.+?)\s+(\d+)\s+(\d+)\s*$", raw)
    if not m:
        return None

    hex_code = normalize_hex(m.group(1))
    key_name = m.group(2).strip()
    try:
        card = int(m.group(3))
        valve = int(m.group(4))
    except ValueError:
        return None

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
    profiles = []
    if not profiles_dir.exists():
        return profiles
    for txt_file in sorted(profiles_dir.glob("*.txt")):
        profiles.append(txt_file.stem)
    return profiles


def choose_profile_interactive(profiles: list[str]) -> str:
    print("Available keyboard profiles:")
    for idx, name in enumerate(profiles, start=1):
        print(f"  {idx}. {name}")
    while True:
        value = input("Select profile number: ").strip()
        if not value.isdigit():
            print("Enter a number.")
            continue
        choice = int(value)
        if 1 <= choice <= len(profiles):
            return profiles[choice - 1]
        print("Out of range.")


def load_last_profile(state_file: Path) -> str | None:
    if not state_file.exists():
        return None
    content = state_file.read_text(encoding="utf-8").strip()
    return content or None


def save_last_profile(state_file: Path, profile_name: str):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(profile_name + "\n", encoding="utf-8")


def get_vk_hex(key) -> str | None:
    # Normal key
    vk = getattr(key, "vk", None)
    if isinstance(vk, int):
        return f"{vk:X}"

    # Special key
    value = getattr(key, "value", None)
    vk = getattr(value, "vk", None)
    if isinstance(vk, int):
        return f"{vk:X}"

    return None


class Bridge:
    def __init__(self, ser: serial.Serial, mapping: dict, on_ms: int, off_ms: int):
        self.ser = ser
        self.mapping = mapping
        self.on_ms = on_ms
        self.off_ms = off_ms
        self.last_fire_at = 0.0

    def send_fire(self, card: int, valve: int):
        cmd = f"FIRE {card} {valve} {self.on_ms} {self.off_ms}\n"
        self.ser.write(cmd.encode("ascii"))
        self.ser.flush()
        response = self.ser.readline().decode("utf-8", errors="replace").strip()
        if response:
            print(f"Arduino: {response}")

    def on_press(self, key):
        # Basic debounce in software so repeated key events do not spam valves.
        now = time.time()
        if now - self.last_fire_at < 0.05:
            return

        vk_hex = get_vk_hex(key)
        if not vk_hex:
            return

        vk_hex = normalize_hex(vk_hex)
        if vk_hex not in self.mapping:
            print(f"No mapping for hex 0x{vk_hex}")
            return

        key_name, card, valve = self.mapping[vk_hex]
        print(f"Key 0x{vk_hex} ({key_name}) -> card {card}, valve {valve}")
        self.send_fire(card, valve)
        self.last_fire_at = now


def main():
    parser = argparse.ArgumentParser(description="Keyboard to Arduino valve bridge")
    parser.add_argument("--port", required=True, help="Serial port, e.g. /dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--on-ms", type=int, default=200, help="Valve ON time in ms")
    parser.add_argument("--off-ms", type=int, default=200, help="Pause after reset in ms")
    parser.add_argument(
        "--profiles-dir",
        default="Keyboards",
        help="Directory with keyboard TXT profiles",
    )
    parser.add_argument(
        "--keyboard",
        help="Keyboard profile name (TXT file stem, e.g. 9100dw for 9100dw.txt)",
    )
    parser.add_argument(
        "--choose",
        action="store_true",
        help="Force interactive keyboard selection from profile list",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print available keyboard profiles and exit",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    profiles_dir = Path(args.profiles_dir)
    if not profiles_dir.is_absolute():
        profiles_dir = (base_dir / profiles_dir).resolve()

    profiles = discover_profiles(profiles_dir)
    if not profiles:
        print(f"No keyboard profiles found in: {profiles_dir}")
        raise SystemExit(1)

    if args.list:
        for name in profiles:
            print(name)
        raise SystemExit(0)

    state_file = Path(__file__).resolve().parent / ".selected_keyboard"
    selected_profile = None

    if args.keyboard:
        selected_profile = args.keyboard
    elif args.choose:
        selected_profile = choose_profile_interactive(profiles)
    else:
        last = load_last_profile(state_file)
        if last in profiles:
            selected_profile = last
        else:
            selected_profile = choose_profile_interactive(profiles)

    if selected_profile not in profiles:
        print(f"Unknown profile '{selected_profile}'. Use --list to see profiles.")
        raise SystemExit(1)

    save_last_profile(state_file, selected_profile)

    map_path = profiles_dir / f"{selected_profile}.txt"
    if not map_path.exists():
        print(f"Mapping file not found: {map_path}")
        raise SystemExit(1)

    mapping, bad_lines = load_mapping(map_path)
    if not mapping:
        print(f"No valid mappings found in: {map_path}")
        raise SystemExit(1)

    print(f"Selected keyboard profile: {selected_profile}")
    print(f"Mapping file: {map_path}")
    print(f"Loaded mappings: {len(mapping)}")
    if bad_lines:
        print(f"Skipped malformed lines: {bad_lines}")

    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        time.sleep(2.0)  # Allow Arduino reset after opening USB serial
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Handshake
        ser.write(b"PING\n")
        ser.flush()
        pong = ser.readline().decode("utf-8", errors="replace").strip()
        print(f"Arduino handshake: {pong or '(no response)'}")

        bridge = Bridge(ser, mapping, args.on_ms, args.off_ms)
        print("Listening for key presses. Stop with Ctrl+C.")
        with keyboard.Listener(on_press=bridge.on_press, suppress=False) as listener:
            listener.join()


if __name__ == "__main__":
    main()
