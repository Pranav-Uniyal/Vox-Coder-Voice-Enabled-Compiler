import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import speech_recognition as sr
import pyttsx3
import threading
import subprocess
import re
from lark import Lark, Tree
from lark.tree import pydot__tree_to_png
import tempfile
import os
from PIL import Image, ImageTk

# Initialization
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()
user_code = ""
current_language = "Python"

# Define a simple grammar for parse tree generation
parser = Lark(r"""
    start: assignment | expr

    assignment: NAME "=" expr

    ?expr: expr "+" term   -> add
         | expr "-" term   -> sub
         | term

    ?term: term "*" factor -> mul
         | term "/" factor -> div
         | term "%" factor -> mod
         | factor

    ?factor: "-" factor    -> neg
           | "+" factor    -> pos
           | NUMBER        -> number
           | NAME          -> var
           | "(" expr ")"

    %import common.CNAME -> NAME
    %import common.NUMBER
    %import common.WS
    %ignore WS
""", parser='lalr')


# Tokenization function
def tokenize_code(code):
    token_specification = [
        ('COMMENT',  r'#.*'),                     
        ('NUMBER',   r'\d+(\.\d*)?'),             
        ('ASSIGN',   r'='),                       
        ('OP',       r'[+\-*/%()]'),              
        ('ID',       r'[A-Za-z_]\w*'),            
        ('SKIP',     r'[ \t]+'),                  
        ('NEWLINE',  r'\n'),                     
        ('MISMATCH', r'.'),                       
    ]

    tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
    get_token = re.compile(tok_regex).match

    tokens = []
    pos = 0
    mo = get_token(code, pos)
    while mo is not None:
        kind = mo.lastgroup
        value = mo.group()
        if kind not in ['SKIP', 'NEWLINE', 'COMMENT']:  # Ignore comments, whitespace, and newlines
            tokens.append((kind, value))
        pos = mo.end()
        mo = get_token(code, pos)
    return tokens

# Strip comments and blank lines before parsing
def remove_comments_and_blank_lines(code):
    return '\n'.join(
        line.split('#')[0].strip()
        for line in code.splitlines()
        if line.strip() and not line.strip().startswith('#')
    )

# Display Tokenization in a popup
def show_tokens_window(tokens):
    token_win = tk.Toplevel()
    token_win.title("Tokenization")
    token_win.geometry("300x300")
    tk.Label(token_win, text="Tokens:", font=("Arial", 14, "bold")).pack()
    for kind, val in tokens:
        tk.Label(token_win, text=f"{kind} : {val}", font=("Courier", 10)).pack()


# 1. Text-Based Tree (Simple Indentation)
def show_text_tree(code):
    try:
        tree = parser.parse(code)
        tree_win = tk.Toplevel()
        tree_win.title("Text Parse Tree")
        
        text_widget = scrolledtext.ScrolledText(tree_win, width=60, height=30)
        text_widget.pack()
        
        def print_tree(node, depth=0, output=None):
            if output is None:
                output = []
            indent = "    " * depth
            if isinstance(node, Tree):
                output.append(f"{indent}{node.data}")
                for child in node.children:
                    print_tree(child, depth+1, output)
            else:
                output.append(f"{indent}{node}")
            return "\n".join(output)
        
        text_widget.insert(tk.END, print_tree(tree))
    except Exception as e:
        messagebox.showerror("Error", str(e))


# 2. Matplotlib Visualization
def show_matplotlib_tree(code):
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        
        tree = parser.parse(code)
        tree_win = tk.Toplevel()
        tree_win.title("Matplotlib Parse Tree")
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        def plot_node(node, x, y, dx=1.0, dy=1.0):
            label = node.data if isinstance(node, Tree) else str(node)
            ax.text(x, y, label, ha='center', va='center',
                   bbox=dict(facecolor='white', edgecolor='black', boxstyle='round'))
            
            if isinstance(node, Tree):
                children = node.children
                if children:
                    x_children = x - (len(children)-1)*dx/2
                    for child in children:
                        ax.plot([x, x_children], [y-dy/4, y-dy], 'k-')
                        plot_node(child, x_children, y-dy, dx/2, dy)
                        x_children += dx
        
        plot_node(tree, 0, 0)
        ax.axis('off')
        
        canvas = FigureCanvasTkAgg(fig, master=tree_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    except ImportError:
        messagebox.showerror("Error", "Please install matplotlib: pip install matplotlib")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# 3. Tkinter Canvas Drawing
def show_canvas_tree(code):
    try:
        tree = parser.parse(code)
        tree_win = tk.Toplevel()
        tree_win.title("Canvas Parse Tree")
        
        canvas = tk.Canvas(tree_win, width=800, height=600, bg='white')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        def draw_node(node, x, y, h_spacing=150, v_spacing=100):
            node_id = canvas.create_oval(x-30, y-15, x+30, y+15, fill='lightblue')
            label = node.data if isinstance(node, Tree) else str(node)
            canvas.create_text(x, y, text=label)
            
            if isinstance(node, Tree):
                children = node.children
                if children:
                    start_x = x - (len(children)-1)*h_spacing/2
                    for child in children:
                        child_x = start_x
                        child_y = y + v_spacing
                        canvas.create_line(x, y+15, child_x, child_y-15)
                        draw_node(child, child_x, child_y, h_spacing*0.7, v_spacing)
                        start_x += h_spacing
            return node_id
        
        draw_node(tree, 400, 50)
    except Exception as e:
        messagebox.showerror("Error", str(e))


# Get indentation
def get_indentation(code):
    lines = code.strip().split("\n")
    if not lines:
        return ""
    last = lines[-1].strip()
    if last.endswith(":") or last.endswith("{"):
        return "    "
    return ""

# Speech to Code Mapping
def map_speech_to_code(text, language="Python", user_code=""):
    text = text.lower().strip()
    indent = get_indentation(user_code)

    # Normalize common phrases
    replacements = {
        "plus": "+",
        "minus": "-",
        "into": "*",
        "multiplied by": "*",
        "multiplies": "*",
        "divided by": "/",
        "greater than or equal to": ">=",
        "less than or equal to": "<=",
        "greater than": ">",
        "less than": "<",
        "equal to": "=",
        "equals to": "=",
        "equals": "=",
        "check is equal to": "==",
        "check is equals to": "==",
        "is not equal to": "!=",
        "not equal to": "!=",
        "not equals": "!=",
        "and": "and",
        "or": "or",
        "not": "not",
        "open parenthesis": "(",
        "close parenthesis": ")",
        "mode": "%",
        "floor division": "//",
        "smaller than": "<",
        "bigger than": ">",
        "dot": "."
    }

    for phrase, symbol in replacements.items():
        text = text.replace(phrase, f" {symbol} ")

    text = ' '.join(text.split())  # remove extra whitespace

    if language == "Python":
        # Handle print
        if text.startswith("print "):
            return indent + f'print("{text.replace("print ", "")}")'

        # Handle input
        if "take input for" in text:
            var = text.split("for")[-1].strip()
            return indent + f'{var} = input("Enter {var}: ")'

        # Handle function call
        if text.startswith("call function"):
            match = re.match(r"call function (\w+)(?: with (.+))?", text)
            if match:
                func = match.group(1)
                args = match.group(2)
                if args:
                    args = ', '.join(arg.strip() for arg in args.split("and"))
                else:
                    args = ''
                return indent + f"{func}({args})"

        # Variable assignment with operator expressions
        match = re.match(r"(?:create |set |define |variable )?([a-zA-Z_]\w*) (?:=|equals|is|:=|==)? (.+)", text)
        if match:
            var_name = match.group(1).strip()
            value_expr = match.group(2).strip()
            return indent + f"{var_name} = {value_expr}"

        # Incomplete expression like "equals b + c"
        if text.startswith("==") or text.startswith("= "):
            value_expr = text.split("=", 1)[-1].strip()
            return indent + f"# Missing variable name = {value_expr}"

        # While loop
        if text.startswith("while "):
            condition = text.replace("while", "").strip()
            return indent + f"while {condition}:"

        # If condition
        if text.startswith("if "):
            condition = text.replace("if", "").strip()
            return indent + f"if {condition}:"

        # Else
        if text.strip() == "else":
            return indent + "else:"

        # For loop
        match = re.search(r"from (\d+) to (\d+)", text)
        if match:
            start, end = match.groups()
            return indent + f"for i in range({start}, {int(end)+1}):"

    return indent + f"# Unrecognized: {text}"

# Voice recognition
def speak(text):
    tts_engine.say(text)
    tts_engine.runAndWait()

def recognize_speech_thread():
    global user_code
    try:
        with sr.Microphone() as source:
            status_label.config(text="🎤 Listening...")
            window.update()
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
            status_label.config(text="🧠 Recognizing...")
            text = recognizer.recognize_google(audio)
            status_label.config(text=f"You said: {text}")

            mapped_code = map_speech_to_code(text, current_language, user_code)
            code_display.insert(tk.END, mapped_code + "\n")
            user_code += mapped_code + "\n"
    except sr.UnknownValueError:
        messagebox.showerror("Speech Error", "Could not understand audio")
    except sr.RequestError:
        messagebox.showerror("Connection Error", "Check your internet connection")

def recognize_speech():
    threading.Thread(target=recognize_speech_thread).start()

def run_code():
    global user_code
    try:
        exec(user_code)
        speak("Code executed successfully")
    except Exception as e:
        messagebox.showerror("Execution Error", str(e))

def clear_code():
    global user_code
    user_code = ""
    code_display.delete(1.0, tk.END)
    status_label.config(text="Editor cleared.")
    speak("Editor cleared")

def on_tokenize():
    tokens = tokenize_code(user_code)
    show_tokens_window(tokens)


def sync_user_code():
    global user_code
    user_code = code_display.get("1.0", tk.END)
    status_label.config(text="Code synced from editor.")


# GUI Setup
window = tk.Tk()
window.title("🧠 VoxCoder - Voice-Based Python Compiler")
window.geometry("900x700")
window.config(bg="#F2F4F4")

tk.Label(window, text="🧠 VoxCoder", font=("Arial", 24, "bold"), fg="#2980B9", bg="#F2F4F4").pack(pady=10)
status_label = tk.Label(window, text="Click '🎤 Speak' to start coding", font=("Arial", 12), bg="#F2F4F4")
status_label.pack()

btn_frame = tk.Frame(window, bg="#F2F4F4")
btn_frame.pack(pady=10)
tk.Button(btn_frame, text="🎤 Speak", font=("Arial", 12, "bold"), bg="#1ABC9C", fg="white", command=recognize_speech).grid(row=0, column=0, padx=10)
tk.Button(btn_frame, text="▶️ Run", font=("Arial", 12, "bold"), bg="#28B463", fg="white", command=run_code).grid(row=0, column=1, padx=10)
tk.Button(btn_frame, text="🧹 Clear", font=("Arial", 12, "bold"), bg="#E74C3C", fg="white", command=clear_code).grid(row=0, column=2, padx=10)
tk.Button(btn_frame, text="💾 Sync Code", font=("Arial", 12, "bold"), bg="#85929E", fg="white", command=sync_user_code).grid(row=0, column=4, padx=10)


tool_frame = tk.Frame(window, bg="#F2F4F4")
tool_frame.pack(pady=5)
tk.Button(tool_frame, text="🧩 Tokenize", font=("Arial", 12), bg="#5DADE2", fg="white", command=on_tokenize).pack(side=tk.LEFT, padx=10)

# All parse tree visualization options
parse_tree_options = [
    ("📝 Text Tree", show_text_tree, "#F39C12"),
    ("📊 Matplotlib", show_matplotlib_tree, "#3498DB"),
    ("🎨 Canvas", show_canvas_tree, "#16A085")
]

for text, command, color in parse_tree_options:
    try:
        tk.Button(tool_frame, text=text, font=("Arial", 12), bg=color, fg="white", 
                 command=lambda cmd=command: cmd(user_code)).pack(side=tk.LEFT, padx=5)
    except:
        pass  # Skip if dependencies aren't available

code_display = scrolledtext.ScrolledText(window, height=25, width=100, font=("Courier New", 12), bg="#FBFCFC")
code_display.pack(padx=15, pady=10)

tk.Label(window, text="Team Machinist | Let your voice be the keyboard", font=("Arial", 10, "italic"), bg="#F2F4F4").pack()
window.mainloop()