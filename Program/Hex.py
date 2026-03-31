import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk
import os
import re
import threading
from datetime import datetime

try:
    from pynput import keyboard as pynkb
except ImportError:
    print("Kniznica 'pynput' nie je nainstalovana.")
    print("V Thonny: Tools -> Manage packages -> zadaj 'pynput' -> Install")
    exit()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KB_DIR     = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'Keyboards'))
DB_PATH    = os.path.join(SCRIPT_DIR, 'Database.txt')
IMG_EXTS   = {'.jpg', '.jpeg', '.png', '.bmp'}

VK_LABELS = {
    '1B':'ESC',
    '70':'F1','71':'F2','72':'F3','73':'F4',
    '74':'F5','75':'F6','76':'F7','77':'F8',
    '78':'F9','79':'F10','7A':'F11','7B':'F12',
    'C0':'^','31':'1','32':'2','33':'3','34':'4','35':'5',
    '36':'6','37':'7','38':'8','39':'9','30':'0',
    'BD':'-','BB':'+','08':'Backspace',
    '09':'Tab',
    '51':'Q','57':'W','45':'E','52':'R','54':'T',
    '5A':'Z','55':'U','49':'I','4F':'O','50':'P',
    'DB':'U','DC':'#','0D':'Enter',
    '14':'Caps Lock',
    '41':'A','53':'S','44':'D','46':'F','47':'G',
    '48':'H','4A':'J','4B':'K','4C':'L',
    'BA':'O','DE':'A',
    'A0':'Shift L','E2':'<',
    '59':'Y','58':'X','43':'C','56':'V','42':'B',
    '4E':'N','4D':'M','BC':',','BE':'.','BF':'-',
    'A1':'Shift R',
    'A2':'Strg L','5B':'Win L','A4':'Alt',
    '20':'Medzernik',
    'A5':'AltGr','5C':'Win R','5D':'Menu','A3':'Strg R',
    '26':'Hor','25':'Vlavo','28':'Dol','27':'Vpravo',
    '2C':'PrintScr','91':'ScrollLock','13':'Pause',
    '2D':'Insert','2E':'Delete','24':'Home','23':'End',
    '21':'PgUp','22':'PgDn',
    '90':'NumLock',
    '60':'Num0','61':'Num1','62':'Num2','63':'Num3',
    '64':'Num4','65':'Num5','66':'Num6','67':'Num7',
    '68':'Num8','69':'Num9',
    '6A':'Num*','6B':'Num+','6D':'Num-','6E':'Num.','6F':'Num/',
}

BG     = '#1c1c1c'
BG2    = '#242424'
BG3    = '#2e2e2e'
BORDER = '#353535'
TPRI   = '#e0e0e0'
TSEC   = '#777777'
TDIM   = '#404040'
GREEN  = '#4caf50'
GDARK  = '#1a3d1a'
GBRI   = '#88ee88'
RED    = '#e53935'
BLUE   = '#42a5f5'
AMBER  = '#ffa726'
ACC_G  = '#1e5c28'
ACC_B  = '#1a3f5c'

DD_BG = '#3a3f46'
DD_ACTIVE = '#4f6f8f'

WINDOW_BOTTOM_MARGIN = 70

def scan_keyboards():
    result = {}
    if not os.path.isdir(KB_DIR):
        os.makedirs(KB_DIR, exist_ok=True)
        return result
    by_name = {}
    for f in os.listdir(KB_DIR):
        base, ext = os.path.splitext(f)
        if ext.lower() in IMG_EXTS:
            by_name.setdefault(base, {})['img'] = os.path.join(KB_DIR, f)
        elif ext.lower() == '.txt':
            by_name.setdefault(base, {})['txt'] = os.path.join(KB_DIR, f)
    for name, paths in by_name.items():
        if 'img' in paths and 'txt' in paths:
            result[name] = paths
    return result

def load_sequence(path):
    if not os.path.isfile(path):
        return []
    result = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.search(r'0x([0-9A-Fa-f]+)', line)
            if m:
                result.append(m.group(1).upper())
                continue
            val = line.upper()
            if val.startswith('0X'):
                val = val[2:]
            if re.match(r'^[0-9A-F]+$', val):
                result.append(val)
    return result

def load_order_kb_map(path):
    mapping = {}
    if not os.path.isfile(path):
        return mapping
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = re.split(r'[\t;]+', line)
            if len(parts) < 2:
                parts = line.split()
            if len(parts) < 2:
                continue
            tester_type = parts[0].strip()
            order_type = parts[1].strip().upper()
            if tester_type and order_type:
                mapping[order_type] = tester_type
    return mapping

keyboards        = scan_keyboards()
order_kb_map     = load_order_kb_map(DB_PATH)
sequence         = []
idx              = [0]
running          = [False]
last_ok          = [None]
photo_ref        = [None]
led_state        = {'NUM': False, 'CAPS': False, 'SCROLL': False, 'PAD': False}
led_values       = {'NUM': '', 'CAPS': '', 'SCROLL': '', 'PAD': ''}
pyn_listener     = [None]
resize_job       = [None]

root = tk.Tk()
root.title('Keyboard Tester')
root.configure(bg=BG)
root.minsize(720, 540)

sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()
root.geometry(f"{sw}x{sh-WINDOW_BOTTOM_MARGIN}+0+0")
# root.overrideredirect(True)

F_HEX = tkfont.Font(family='Courier New', size=30, weight='bold')
F_BIG = tkfont.Font(family='Courier New', size=11)
F_MED = tkfont.Font(family='Courier New', size=9)
F_SML = tkfont.Font(family='Courier New', size=8)
F_RES = tkfont.Font(family='Courier New', size=9, weight='bold')

kb_var            = tk.StringVar(value='')
kb_names          = sorted(keyboards.keys())
order_kb_type_var = tk.StringVar(value='')
order_var         = tk.StringVar(value='')
date_var          = tk.StringVar(value=datetime.now().strftime('%d.%m.%Y'))

root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=0)
root.rowconfigure(0, weight=1)

left = tk.Frame(root, bg=BG)
left.grid(row=0, column=0, sticky='nsew')
left.columnconfigure(0, weight=1)
left.rowconfigure(1, weight=1)

led_bar = tk.Frame(left, bg=BG2, pady=8, padx=16)
led_bar.grid(row=0, column=0, sticky='ew')

led_cvs      = {}
led_lbls     = {}
led_val_lbls = {}

for nm in ['NUM', 'CAPS', 'SCROLL', 'PAD']:
    cell = tk.Frame(led_bar, bg=BG2)
    cell.pack(side='left', padx=10)
    c = tk.Canvas(cell, width=22, height=22, bg=BG2, highlightthickness=0)
    c.pack()
    c.create_oval(2, 2, 20, 20, fill=GDARK, outline='#2a5a2a', width=1, tags='led')
    led_cvs[nm] = c
    lbl = tk.Label(cell, text=nm, bg=BG2, fg=TSEC, font=F_SML)
    lbl.pack(pady=2)
    led_lbls[nm] = lbl
    val_frame = tk.Frame(cell, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
    val_frame.pack(fill='x', pady=2)
    val_lbl = tk.Label(val_frame, text='—', bg=BG3, fg=TDIM, font=F_SML, width=6, anchor='center', pady=2)
    val_lbl.pack()
    led_val_lbls[nm] = val_lbl

def set_led(name, on, value=None):
    led_state[name] = on
    if value is not None:
        led_values[name] = value
    c = led_cvs[name]
    if on:
        c.itemconfig('led', fill=GBRI, outline='#aaffaa')
        led_lbls[name].config(fg=GBRI)
        v = led_values[name] if led_values[name] else 'ON'
        led_val_lbls[name].config(text=str(v), fg=GBRI)
    else:
        c.itemconfig('led', fill=GDARK, outline='#2a5a2a')
        led_lbls[name].config(fg=TSEC)
        led_val_lbls[name].config(text='—', fg=TDIM)

img_canvas = tk.Canvas(left, bg=BG, highlightthickness=0)
img_canvas.grid(row=1, column=0, sticky='nsew')

no_img = tk.Label(img_canvas, text='Vyber typ klavesnice\nz menu vpravo',
                  bg=BG, fg=TDIM, font=F_BIG, justify='center')
no_img.place(relx=0.5, rely=0.5, anchor='center')

def render_image(path=None):
    img_canvas.delete('all')
    no_img.place_forget()
    if not path or not os.path.isfile(path):
        no_img.place(relx=0.5, rely=0.5, anchor='center')
        return
    try:
        cw = img_canvas.winfo_width()
        ch = img_canvas.winfo_height()
        if cw < 10:
            cw = 500
        if ch < 10:
            ch = 300
        img = Image.open(path)
        ratio = min(cw / img.width, ch / img.height)
        nw = max(1, int(img.width * ratio))
        nh = max(1, int(img.height * ratio))
        img = img.resize((nw, nh), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        photo_ref[0] = photo
        img_canvas.create_image(cw // 2, ch // 2, anchor='center', image=photo)
        img_canvas.create_text(cw - 6, ch - 4, anchor='se',
                               text=os.path.basename(path), fill='#8a8a8a', font=F_SML)
    except Exception as e:
        img_canvas.create_text(10, 10, anchor='nw', text=str(e), fill=RED, font=F_SML)

def on_img_resize(event=None):
    if resize_job[0] is not None:
        root.after_cancel(resize_job[0])
    resize_job[0] = root.after(120, lambda: render_image(keyboards.get(kb_var.get(), {}).get('img')))

img_canvas.bind('<Configure>', on_img_resize)

bot = tk.Frame(left, bg=BG)
bot.grid(row=2, column=0, sticky='ew')
bot.columnconfigure(0, weight=1)
bot.columnconfigure(1, weight=1)

def make_hex_panel(parent, col, title, accent):
    f = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
    f.grid(row=0, column=col, sticky='nsew', padx=(0,4) if col==0 else (4,0), pady=8)
    f.columnconfigure(0, weight=1)
    tk.Frame(f, bg=accent, height=3).pack(fill='x')
    hdr = tk.Frame(f, bg=BG2)
    hdr.pack(fill='x', padx=10, pady=6)
    hdr.columnconfigure(0, weight=1)
    tk.Label(hdr, text=title, bg=BG2, fg=TSEC, font=F_SML, anchor='w').grid(row=0, column=0, sticky='w')
    ord_l = tk.Label(hdr, text='', bg=BG2, fg=TDIM, font=F_SML, anchor='e')
    ord_l.grid(row=0, column=1, sticky='e')
    hex_l = tk.Label(f, text='—', bg=BG2, fg=TDIM, font=F_MED, anchor='center', pady=4)
    hex_l.pack(fill='x', padx=10)
    name_l = tk.Label(f, text='', bg=BG2, fg=TDIM, font=F_HEX, anchor='center', pady=6)
    name_l.pack(fill='x', padx=10)
    return ord_l, hex_l, name_l

ordA, hexA, nameA = make_hex_panel(bot, 0, 'STLACENE', ACC_G)
ordB, hexB, nameB = make_hex_panel(bot, 1, 'NASLEDUJUCE', ACC_B)

result_lbl = tk.Label(left, text='', bg=BG, fg=TSEC, font=F_RES, anchor='center', pady=4)
result_lbl.grid(row=3, column=0, sticky='ew')

sidebar = tk.Frame(root, bg=BG2, width=230)
sidebar.grid(row=0, column=1, sticky='nsew')
sidebar.columnconfigure(0, weight=1)
sidebar.rowconfigure(11, weight=1)
sidebar.propagate(False)

tk.Label(sidebar, text='Typ klavesnice', bg=BG2, fg=TSEC, font=F_SML, anchor='w',
         padx=14, pady=10).grid(row=0, column=0, sticky='ew')

dd_wrap = tk.Frame(sidebar, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
dd_wrap.grid(row=1, column=0, sticky='ew', padx=14, pady=(0, 8))
dd_wrap.columnconfigure(0, weight=1)

dropdown = tk.OptionMenu(dd_wrap, kb_var, *(kb_names if kb_names else ['']))
dropdown.config(
    bg=BG3,
    fg=TPRI,
    relief='flat',
    font=F_BIG,
    activebackground='#333',
    activeforeground=TPRI,
    highlightthickness=0,
    bd=0,
    anchor='w',
    indicatoron=1
)
dropdown['menu'].config(
    bg=DD_BG,
    fg=TPRI,
    font=F_MED,
    activebackground=DD_ACTIVE,
    activeforeground=TPRI,
    bd=1,
    relief='solid'
)
dropdown.grid(row=0, column=0, sticky='ew', padx=2, pady=2)

tk.Label(sidebar, text='Typ klavesnice podla zakazky', bg=BG2, fg=TSEC, font=F_SML, anchor='w',
         padx=14, pady=10).grid(row=2, column=0, sticky='ew')

order_kb_type_wrap = tk.Frame(sidebar, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
order_kb_type_wrap.grid(row=3, column=0, sticky='ew', padx=14)

order_kb_type_entry = tk.Entry(order_kb_type_wrap, textvariable=order_kb_type_var,
                               bg=BG3, fg=TPRI, relief='flat', font=F_BIG,
                               insertbackground=TPRI, bd=0)
order_kb_type_entry.pack(fill='x', padx=8, pady=6)

tk.Label(sidebar, text='Cislo zakazky', bg=BG2, fg=TSEC, font=F_SML, anchor='w',
         padx=14, pady=10).grid(row=4, column=0, sticky='ew')

order_wrap = tk.Frame(sidebar, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
order_wrap.grid(row=5, column=0, sticky='ew', padx=14)

order_entry = tk.Entry(order_wrap, textvariable=order_var,
                       bg=BG3, fg=TPRI, relief='flat', font=F_BIG,
                       insertbackground=TPRI, bd=0)
order_entry.pack(fill='x', padx=8, pady=6)

tk.Label(sidebar, text='Datum', bg=BG2, fg=TSEC, font=F_SML, anchor='w',
         padx=14, pady=10).grid(row=6, column=0, sticky='ew')

date_wrap = tk.Frame(sidebar, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
date_wrap.grid(row=7, column=0, sticky='ew', padx=14)

date_entry = tk.Entry(date_wrap, textvariable=date_var,
                      bg=BG3, fg=TPRI, relief='flat', font=F_BIG,
                      insertbackground=TPRI, bd=0)
date_entry.pack(fill='x', padx=8, pady=6)

def do_print_label():
    status_lbl.config(text='Tlac stitka zatial nie je nastavena', fg=AMBER)

print_label_btn = tk.Button(sidebar, text='Tlac stitka', command=do_print_label,
                            bg=ACC_B, fg=TPRI, relief='flat', font=F_MED,
                            cursor='hand2', bd=0, pady=8,
                            activebackground=ACC_B, activeforeground=TPRI)
print_label_btn.grid(row=8, column=0, sticky='ew', padx=14, pady=(8, 4))

seq_info = tk.Label(sidebar, text='', bg=BG2, fg=TSEC, font=F_SML, anchor='w', padx=14, pady=8)
seq_info.grid(row=9, column=0, sticky='ew')

tk.Frame(sidebar, bg=BORDER, height=1).grid(row=10, column=0, sticky='new')
tk.Frame(sidebar, bg=BG2).grid(row=11, column=0, sticky='nsew')

tk.Frame(sidebar, bg=BORDER, height=1).grid(row=12, column=0, sticky='ew')

led_sec = tk.Frame(sidebar, bg=BG2, padx=14, pady=10)
led_sec.grid(row=13, column=0, sticky='ew')
led_sec.columnconfigure(0, weight=1)
led_sec.columnconfigure(1, weight=1)

tk.Label(led_sec, text='LED', bg=BG2, fg=TSEC, font=F_SML).grid(row=0, column=0, sticky='w', pady=4)
tk.Label(led_sec, text='Hodnota', bg=BG2, fg=TDIM, font=F_SML).grid(row=0, column=1, sticky='w', pady=4)

sidebar_val_lbls = {}
for i, nm in enumerate(['NUM', 'CAPS', 'SCROLL', 'PAD']):
    def toggle(n=nm):
        new_state = not led_state[n]
        set_led(n, new_state)
        sidebar_val_lbls[n].config(text='ON' if new_state else '—',
                                   fg=GBRI if new_state else TDIM)
    tk.Button(led_sec, text=nm, command=toggle,
              bg=BG3, fg=TSEC, relief='flat', font=F_SML,
              padx=6, pady=3, cursor='hand2', bd=0,
              activebackground='#333', activeforeground=TPRI).grid(row=i+1, column=0, sticky='ew', pady=2, padx=(0,4))
    val_f = tk.Frame(led_sec, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
    val_f.grid(row=i+1, column=1, sticky='ew', pady=2)
    vl = tk.Label(val_f, text='—', bg=BG3, fg=TDIM, font=F_SML, anchor='center', pady=3)
    vl.pack(fill='x')
    sidebar_val_lbls[nm] = vl

tk.Frame(sidebar, bg=BORDER, height=1).grid(row=14, column=0, sticky='ew')
btn_bar = tk.Frame(sidebar, bg=BG2, padx=14, pady=12)
btn_bar.grid(row=15, column=0, sticky='ew')
btn_bar.columnconfigure(0, weight=1)
btn_bar.columnconfigure(1, weight=1)

def bst(bg, fg=TPRI):
    return dict(bg=bg, fg=fg, relief='flat', font=F_MED,
                pady=8, cursor='hand2', bd=0,
                activebackground=bg, activeforeground=fg)

tk.Button(btn_bar, text='START', command=lambda: do_start(), **bst(ACC_G)).grid(row=0, column=0, sticky='ew', padx=(0,4))
tk.Button(btn_bar, text='Reset', command=lambda: do_reset(), **bst(BG3, TSEC)).grid(row=0, column=1, sticky='ew')

prog_lbl = tk.Label(sidebar, text='', bg=BG2, fg=TDIM, font=F_SML, pady=4)
prog_lbl.grid(row=16, column=0)

tk.Frame(sidebar, bg=BORDER, height=1).grid(row=17, column=0, sticky='ew')
btn_reload = tk.Button(sidebar, text='Obnovit zoznam',
                       bg=BG2, fg=TDIM, relief='flat', font=F_SML,
                       cursor='hand2', bd=0, pady=6,
                       activebackground=BG3, activeforeground=TPRI)
btn_reload.grid(row=18, column=0, sticky='ew', padx=14, pady=4)

status_lbl = tk.Label(sidebar, text='Vyber klavesnicu',
                      bg=BG2, fg=TDIM, font=F_SML,
                      padx=14, pady=6, anchor='w', wraplength=190)
status_lbl.grid(row=19, column=0, sticky='ew')

def force_redraw():
    root.update_idletasks()
    render_image(keyboards.get(kb_var.get(), {}).get('img'))
    left.update_idletasks()
    sidebar.update_idletasks()
    img_canvas.update_idletasks()

def apply_window_geometry():
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{sw}x{sh-WINDOW_BOTTOM_MARGIN}+0+0")

def toggle_kiosk(event=None):
    current = bool(root.overrideredirect())
    root.overrideredirect(not current)
    apply_window_geometry()
    root.after(100, force_redraw)
    root.after(300, force_redraw)

def end_kiosk(event=None):
    root.overrideredirect(False)
    apply_window_geometry()
    root.after(100, force_redraw)

root.bind('<F11>', toggle_kiosk)
root.bind('<Escape>', end_kiosk)

def on_kb_select(*_):
    name = kb_var.get()
    kb = keyboards.get(name)
    if not kb:
        return
    do_reset()
    global sequence
    sequence = load_sequence(kb['txt'])
    n = len(sequence)
    seq_info.config(text=f'{n} klavesov', fg=BLUE if n else RED)
    status_lbl.config(text=f'Nacitane: {n} kl.' if n else 'TXT je prazdny!',
                      fg=AMBER if n else RED)
    root.after(50, lambda: render_image(kb.get('img')))
    root.after(150, force_redraw)

kb_var.trace_add('write', on_kb_select)

def apply_order_kb_type(*_):
    order_type = order_kb_type_var.get().strip().upper()
    if not order_type:
        return
    tester_type = order_kb_map.get(order_type)
    if not tester_type:
        status_lbl.config(text=f'Typ zo zakazky nenajdeny: {order_type}', fg=RED)
        return
    if tester_type not in keyboards:
        status_lbl.config(text=f'V testeri chyba typ: {tester_type}', fg=RED)
        return
    kb_var.set(tester_type)
    status_lbl.config(text=f'Priradene zo zakazky: {tester_type}', fg=GREEN)

order_kb_type_entry.bind('<Return>', apply_order_kb_type)
order_kb_type_entry.bind('<FocusOut>', apply_order_kb_type)

def reload_kb():
    global keyboards, order_kb_map, kb_names
    keyboards = scan_keyboards()
    order_kb_map = load_order_kb_map(DB_PATH)
    kb_names = sorted(keyboards.keys())
    menu = dropdown['menu']
    menu.delete(0, 'end')
    for name in kb_names:
        menu.add_command(label=name, command=tk._setit(kb_var, name))
    if not keyboards:
        menu.add_command(label='(prazdna)', command=lambda: None)
    status_lbl.config(text=f'{len(keyboards)} klavesnic', fg=GREEN)
    root.after(100, force_redraw)

btn_reload.config(command=reload_kb)

def update_panels(clear=False):
    total = len(sequence)
    cur = idx[0]
    if clear or total == 0:
        ordA.config(text=''); hexA.config(text='—', fg=TDIM); nameA.config(text='', fg=TDIM)
        ordB.config(text=''); hexB.config(text='—', fg=TDIM); nameB.config(text='', fg=TDIM)
        prog_lbl.config(text='')
        return
    if cur == 0:
        ordA.config(text=''); hexA.config(text='—', fg=TDIM); nameA.config(text='', fg=TDIM)
    else:
        ph = sequence[cur-1]
        pn = VK_LABELS.get(ph, '')
        clr = GREEN if last_ok[0] else RED if last_ok[0] is False else TPRI
        ordA.config(text=f'#{cur}/{total}', fg=TSEC)
        hexA.config(text=ph, fg=clr)
        nameA.config(text=pn, fg=clr)
    if cur < total:
        nh = sequence[cur]
        nn = VK_LABELS.get(nh, '')
        ordB.config(text=f'#{cur+1}/{total}', fg=TSEC)
        hexB.config(text=nh, fg=BLUE)
        nameB.config(text=nn, fg=BLUE)
    else:
        ordB.config(text=''); hexB.config(text='OK', fg=GREEN); nameB.config(text='hotovo', fg=GREEN)
    prog_lbl.config(text=f'{cur} / {total}')

def process_vk(vk_hex):
    if not running[0]:
        return
    cur = idx[0]
    if cur >= len(sequence):
        return
    expected = sequence[cur]
    ok = vk_hex.upper() == expected.upper()
    last_ok[0] = ok
    if ok:
        result_lbl.config(text='OK', fg=GREEN)
    else:
        gl = VK_LABELS.get(vk_hex.upper(), vk_hex)
        el = VK_LABELS.get(expected, expected)
        result_lbl.config(text=f'CHYBA  stlacene: {vk_hex.upper()} ({gl})   ocakavane: {expected} ({el})', fg=RED)
    idx[0] += 1
    update_panels()
    if idx[0] >= len(sequence):
        running[0] = False
        status_lbl.config(text='Test dokonceny!', fg=GREEN)

def on_press(key):
    if not running[0]:
        return
    try:
        vk = key.vk
    except AttributeError:
        vk = key.value.vk if hasattr(key, 'value') else None
    if vk is None:
        return
    vk_hex = f'{vk:02X}'
    root.after(0, lambda h=vk_hex: process_vk(h))

def start_listener():
    l = pynkb.Listener(on_press=on_press, suppress=False)
    l.start()
    pyn_listener[0] = l

def do_start():
    if not kb_var.get():
        status_lbl.config(text='Vyber typ klavesnice!', fg=RED)
        return
    if not date_var.get().strip():
        status_lbl.config(text='Zadaj datum!', fg=RED)
        return
    if not sequence:
        status_lbl.config(text='Najprv vyber klavesnicu!', fg=RED)
        return
    idx[0] = 0
    running[0] = True
    last_ok[0] = None
    result_lbl.config(text='')
    order_txt = order_var.get().strip()
    order_part = f'zakazka {order_txt}' if order_txt else 'bez zakazky'
    status_lbl.config(text=f'Test bezi...  {kb_var.get()}  /  {order_part}', fg=AMBER)
    update_panels()

def do_reset():
    idx[0] = 0
    running[0] = False
    last_ok[0] = None
    result_lbl.config(text='')
    status_lbl.config(text='Reset', fg=TDIM)
    update_panels(clear=True)
    for nm in led_state:
        set_led(nm, False)
        sidebar_val_lbls[nm].config(text='—', fg=TDIM)

def on_close():
    if pyn_listener[0]:
        pyn_listener[0].stop()
    root.destroy()

root.protocol('WM_DELETE_WINDOW', on_close)
update_panels(clear=True)

if not keyboards:
    status_lbl.config(text=f'Keyboards nenajdena:\n{KB_DIR}', fg=RED)

t = threading.Thread(target=start_listener, daemon=True)
t.start()

root.after(200, force_redraw)
root.after(600, force_redraw)

root.mainloop()
