# Raspberry Pi -> Arduino Mega bridge

## 1) Upload Arduino sketch

Upload:

- `arduino/mega_valve_controller.ino`

Default serial settings:

- baud: `115200`
- commands: `PING`, `RESET`, `FIRE <card> <valve> [on_ms] [off_ms]`

Card select assumption in sketch:

- binary select pins `32,33,34,35` (LSB..MSB) for cards `1..16`

If your hardware is different, edit constants at the top of the sketch.

## 2) Install Python deps on Raspberry Pi

```bash
python3 -m pip install pyserial pynput
```

## 3) Prepare mapping file

Use your keyboard mapping TXT in `Keyboards/*.txt` format:

```text
0x1B    Escape    1    1
0x70    F1        1    2
```

Columns:

1. hex
2. keyboard label
3. card number (1-16)
4. valve number (1-8)

## 4) Keyboard profiles from list

Put all keyboard mappings into `Keyboards/*.txt`.

Profile name = file name without `.txt`, for example:

- `Keyboards/9100dw.txt` -> profile `9100dw`
- `Keyboards/compact.txt` -> profile `compact`

List profiles:

```bash
python3 raspi/keyboard_to_arduino.py --port /dev/ttyACM0 --list
```

Interactive selection from list:

```bash
python3 raspi/keyboard_to_arduino.py --port /dev/ttyACM0 --choose
```

Select profile directly:

```bash
python3 raspi/keyboard_to_arduino.py --port /dev/ttyACM0 --keyboard 9100dw
```

The app stores selected keyboard and uses it on next start until you change it.

## 5) Run bridge

```bash
python3 raspi/keyboard_to_arduino.py \
  --port /dev/ttyACM0 \
  --keyboard 9100dw \
  --on-ms 200 \
  --off-ms 200
```

When you press a key, script finds hex in mapping and sends `FIRE` to Arduino.

## 6) GUI app with Start button (no bridge command typing)

You can also run the GUI app and use `Start` / `Stop` directly:

```bash
python3 tester.py
```

Flow:

1. Select keyboard profile from dropdown.
2. Set Arduino USB port (for example `/dev/ttyACM0`).
3. Click `Start`.
4. Press keys and app sends mapped `FIRE` commands automatically.
5. Click `Stop` to end test.
