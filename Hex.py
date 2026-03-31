try:
    from pynput import keyboard
except ImportError:
    print("Kniznica 'pynput' nie je nainstalovana.")
    print("V Thonny: Tools -> Manage packages -> zadaj 'pynput' -> Install")
    exit()

# ============================================================
#  KEY HEX LOGGER  -  cez pynput (nevyzaduje Admin)
#  Spusti: F5 v Thonny
#  Ukonci: Stop tlacidlo v Thonny
# ============================================================

VK_NAMES = {
    keyboard.Key.backspace:  "Backspace",
    keyboard.Key.tab:        "Tab",
    keyboard.Key.enter:      "Enter",
    keyboard.Key.shift:      "Shift",
    keyboard.Key.shift_r:    "Shift_R",
    keyboard.Key.ctrl:       "Ctrl_L",
    keyboard.Key.ctrl_r:     "Ctrl_R",
    keyboard.Key.alt:        "Alt_L",
    keyboard.Key.alt_r:      "Alt_R",
    keyboard.Key.cmd:        "Win_L",
    keyboard.Key.cmd_r:      "Win_R",
    keyboard.Key.esc:        "Escape",
    keyboard.Key.space:      "Space",
    keyboard.Key.caps_lock:  "CapsLock",
    keyboard.Key.delete:     "Delete",
    keyboard.Key.insert:     "Insert",
    keyboard.Key.home:       "Home",
    keyboard.Key.end:        "End",
    keyboard.Key.page_up:    "PgUp",
    keyboard.Key.page_down:  "PgDn",
    keyboard.Key.left:       "←",
    keyboard.Key.right:      "→",
    keyboard.Key.up:         "↑",
    keyboard.Key.down:       "↓",
    keyboard.Key.print_screen: "PrintScr",
    keyboard.Key.scroll_lock:  "ScrollLock",
    keyboard.Key.pause:        "Pause",
    keyboard.Key.num_lock:     "NumLock",
    keyboard.Key.f1:  "F1",  keyboard.Key.f2:  "F2",
    keyboard.Key.f3:  "F3",  keyboard.Key.f4:  "F4",
    keyboard.Key.f5:  "F5",  keyboard.Key.f6:  "F6",
    keyboard.Key.f7:  "F7",  keyboard.Key.f8:  "F8",
    keyboard.Key.f9:  "F9",  keyboard.Key.f10: "F10",
    keyboard.Key.f11: "F11", keyboard.Key.f12: "F12",
}

def on_press(key):
    try:
        # Normalna klaves (pismeno, cislo, symbol)
        vk = key.vk
        name = key.char if key.char else "?"
        print(f"VK: 0x{vk:02X}   [ {name} ]", flush=True)
    except AttributeError:
        # Specialna klaves (Win, F1, Ctrl...)
        vk = key.value.vk if hasattr(key, 'value') else 0
        name = VK_NAMES.get(key, str(key).replace("Key.", ""))
        print(f"VK: 0x{vk:02X}   [ {name} ]", flush=True)

print("=" * 40)
print("  KEY HEX LOGGER  (pynput, bez Admin)")
print("  Ukonci: Stop v Thonny")
print("=" * 40)

with keyboard.Listener(on_press=on_press, suppress=True) as listener:
    listener.join()