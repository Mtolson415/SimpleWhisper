"""Owned synthetic input fields for opt-in desktop routing acceptance."""
import json
import os
import queue
import sys
import threading
import tkinter as tk

root = tk.Tk()
root.title('Dictation synthetic destination')
root.geometry('650x260+80+180')
second = tk.Toplevel(root)
second.title('Dictation synthetic second destination')
second.geometry('650x200+80+480')
second.withdraw()
fields = [tk.Text(root, height=3, width=65), tk.Text(second, height=3, width=65)]
for field in fields:
    field.pack(padx=12, pady=10)
fields[0].insert('1.0', 'Synthetic prefix: ')
fields[0].mark_set('insert', 'end-1c')
root.update()
fields[0].focus_force()
commands = queue.Queue()


def read_commands():
    for line in sys.stdin:
        commands.put(line.strip())


def poll():
    while not commands.empty():
        command = commands.get_nowait()
        if command == 'read':
            print(json.dumps([field.get('1.0', 'end-1c') for field in fields]), flush=True)
        elif command == 'close':
            root.destroy()
            return
        elif command == 'second':
            second.deiconify()
            second.lift()
            fields[1].focus_force()
            root.update()
            print('ready', flush=True)
    root.after(20, poll)


threading.Thread(target=read_commands, daemon=True).start()
print(json.dumps({'pid': os.getpid()}), flush=True)
root.after(20, poll)
root.mainloop()
