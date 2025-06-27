import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import speech_recognition as sr
import pyttsx3
import threading
import re
from lark import Lark, Tree
import tempfile
import os

# Initialization
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()
user_code = ""
current_language = "Python"

# Define a simple grammar for parse tree generation
parser = Lark(r"""
    start: statement+

    statement: assignment
             | expr

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
    %import common.NEWLINE
    %import common.WS
    %ignore WS
    %ignore NEWLINE
""", parser='lalr')


import re

def tokenize_code(code):
    keywords = {
        'if', 'else', 'elif', 'for', 'while', 'def', 'return', 'in',
        'and', 'or', 'not', 'True', 'False', 'None', 'class', 'break',
        'continue', 'pass', 'import', 'from', 'as', 'with', 'is', 'lambda'
    }
#Tokenization Function
    token_specification = [
        ('COMMENT',  r'#.*'),                            # Comments
        ('STRING',   r'(\".*?\"|\'.*?\')'),              # Strings
        ('NUMBER',   r'\d+(\.\d*)?'),                    # Integer or decimal numbers
        ('ASSIGN',   r'='),                              # Assignment
        ('OP',       r'[+\-*/%]'),                       # Operators
        ('LIST',     r'[\[\]]'),                         # List brackets
        ('DICT',     r'[\{\}]'),                         # Dictionary braces
        ('COLON',    r':'),                              # Colon
        ('COMMA',    r','),                              # Comma
        ('PAREN',    r'[()]'),                           # Parentheses
        ('ID',       r'[A-Za-z_]\w*'),                   # Identifiers or keywords
        ('NEWLINE',  r'\n'),                             # Line breaks
        ('SKIP',     r'[ \t]+'),                         # Whitespace
        ('MISMATCH', r'.'),                              # Any other character
    ]

    tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)
    get_token = re.compile(tok_regex).match

    tokens = []
    pos = 0
    mo = get_token(code, pos)
    while mo is not None:
        kind = mo.lastgroup
        value = mo.group()

        if kind in ['SKIP', 'NEWLINE', 'COMMENT']:
            pass  # skip whitespace, newlines, comments
        elif kind == 'ID':
            if value in keywords:
                kind = 'KEYWORD' if value not in {'True', 'False', 'None'} else \
                       'BOOL' if value in {'True', 'False'} else 'NONE'
            tokens.append((kind, value))
        elif kind == 'MISMATCH':
            tokens.append(('ERROR', value))
        else:
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



# 1. Matplotlib Visualization Tree
def show_matplotlib_tree(code):
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        def layout(node, depth=0, x_offset=0, positions=None, widths=None):
            if positions is None:
                positions = {}
            if widths is None:
                widths = {}

            if isinstance(node, Tree):
                widths[node] = 0
                child_x = x_offset
                for child in node.children:
                    layout(child, depth + 1, child_x, positions, widths)
                    child_x += widths[child] + 1
                    widths[node] += widths[child] + 1
                widths[node] = max(1, widths[node] - 1)
                mid_x = x_offset + widths[node] / 2
            else:
                widths[node] = 1
                mid_x = x_offset + 0.5

            positions[node] = (mid_x, -depth)
            return positions, widths

        def draw_tree(node, ax, positions):
            x, y = positions[node]
            label = node.data if isinstance(node, Tree) else str(node)

            ax.text(x, y, label, ha='center', va='center',
                    bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.4'))

            if isinstance(node, Tree):
                for child in node.children:
                    cx, cy = positions[child]
                    ax.plot([x, cx], [y, cy], 'k-', lw=1)
                    draw_tree(child, ax, positions)

        # Split by lines and draw each tree
        for line in code.strip().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            try:
                tree = parser.parse(stripped)
                fig, ax = plt.subplots(figsize=(8, 6))
                positions, _ = layout(tree)
                draw_tree(tree, ax, positions)
                ax.axis('off')

                tree_win = tk.Toplevel()
                tree_win.title(f"Parse Tree: {stripped}")

                canvas = FigureCanvasTkAgg(fig, master=tree_win)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            except Exception as e:
                messagebox.showerror("Parse Error", f"Failed to parse line:\n{stripped}\n\n{e}")

    except ImportError:
        messagebox.showerror("Error", "Please install matplotlib: pip install matplotlib")


#2.   Annotated Parse tree 
def show_annotated_matplotlib_tree(code):
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        tree = parser.parse(remove_comments_and_blank_lines(code))

        fig, ax = plt.subplots(figsize=(12, 8))

        # Annotate Tree (Semantic Phase)
        def annotate_tree(node, symbol_table=None):
            if symbol_table is None:
                symbol_table = {}

            annotations = {}

            if isinstance(node, Tree):
                if node.data == "assignment":
                    var_name = node.children[0].value
                    value_node = node.children[1]
                    value, _ = annotate_tree(value_node, symbol_table)
                    symbol_table[var_name] = value
                    annotations = {"value": f"{var_name} = {value}"}
                    return None, annotations

                elif node.data in ["add", "sub", "mul", "div", "mod"]:
                    left_val, _ = annotate_tree(node.children[0], symbol_table)
                    right_val, _ = annotate_tree(node.children[1], symbol_table)
                    try:
                        result = eval(f"{left_val} {'+' if node.data=='add' else '-' if node.data=='sub' else '*' if node.data=='mul' else '/' if node.data=='div' else '%'} {right_val}")
                        return result, {"value": result}
                    except:
                        return None, {"value": "?"}

                elif node.data == "number":
                    return float(node.children[0]), {"value": float(node.children[0])}

                elif node.data == "var":
                    var_name = node.children[0].value
                    val = symbol_table.get(var_name, "?")
                    return val, {"value": val}

                else:
                    for child in node.children:
                        annotate_tree(child, symbol_table)

            return None, annotations

        #Layout calculation
        def layout(node, depth=0, x_offset=0, positions=None, widths=None):
            if positions is None:
                positions = {}
            if widths is None:
                widths = {}

            if isinstance(node, Tree):
                widths[node] = 0
                child_x = x_offset
                for child in node.children:
                    layout(child, depth + 1, child_x, positions, widths)
                    child_x += widths[child] + 1
                    widths[node] += widths[child] + 1
                widths[node] = max(1, widths[node] - 1)
                mid_x = x_offset + widths[node] / 2
            else:
                widths[node] = 1
                mid_x = x_offset + 0.5

            positions[node] = (mid_x, -depth)
            return positions, widths

        # Drawing the annotated tree
        def draw_tree(node, positions, symbol_table=None):
            x, y = positions[node]

            if isinstance(node, Tree):
                label = node.data
                _, ann = annotate_tree(node, symbol_table)
                if ann.get("value") is not None:
                    label += f"\n[{ann['value']}]"
            else:
                label = str(node)

            ax.text(x, y, label, ha="center", va="center", fontsize=10,
                    bbox=dict(facecolor='lightgreen', boxstyle='round,pad=0.4'))

            if isinstance(node, Tree):
                for child in node.children:
                    cx, cy = positions[child]
                    ax.plot([x, cx], [y, cy], 'k-', lw=1)
                    draw_tree(child, positions, symbol_table)

        # --- Final render ---
        symbol_table = {}
        positions, _ = layout(tree)
        draw_tree(tree, positions, symbol_table)

        ax.axis('off')

        tree_win = tk.Toplevel()
        tree_win.title("🧠 Annotated Parse Tree")

        canvas = FigureCanvasTkAgg(fig, master=tree_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    except ImportError:
        messagebox.showerror("Error", "Please install matplotlib: pip install matplotlib")
    except Exception as e:
        messagebox.showerror("Error", str(e))


#3. Three Address Code Generation
temp_counter = 0  # Ensure this is at the top-level of your file (outside any function)

def generate_three_address_code(node, tac=None, symbol_table=None):
    global temp_counter

    if tac is None:
        tac = []
    if symbol_table is None:
        symbol_table = {}

    def new_temp():
        global temp_counter  
        temp = f"t{temp_counter}"
        temp_counter += 1
        return temp

    def process(node):
        if isinstance(node, Tree):
            if node.data == "assignment":
                var_name = node.children[0].value
                expr = node.children[1]
                result = process(expr)
                tac.append(f"{var_name} = {result}")
                symbol_table[var_name] = result
                return var_name

            elif node.data in ["add", "sub", "mul", "div", "mod"]:
                a = process(node.children[0])
                b = process(node.children[1])
                temp = new_temp()
                op = {
                    "add": "+", "sub": "-", "mul": "*", "div": "/", "mod": "%"
                }[node.data]
                tac.append(f"{temp} = {a} {op} {b}")
                return temp

            elif node.data == "neg":
                val = process(node.children[0])
                temp = new_temp()
                tac.append(f"{temp} = -{val}")
                return temp

            elif node.data == "pos":
                return process(node.children[0])

            elif node.data == "number":
                return node.children[0]

            elif node.data == "var":
                return node.children[0]

        return str(node)

    process(node)
    return tac

def show_three_address_code():
    global user_code
    try:
        import tkinter as tk
        from tkinter import scrolledtext

        cleaned_code = remove_comments_and_blank_lines(user_code)
        global temp_counter
        temp_counter = 0
        tac_output = []

        try:
            tree = parser.parse(cleaned_code)
            print("Parsed tree root:", tree.data)

            if tree.data == "start":
                for child in tree.children:
                    if isinstance(child, Tree):
                        inner = child.children[0] if child.data == "statement" else child
                        tac = generate_three_address_code(inner)
                        tac_output.extend(tac)
            else:
                tac = generate_three_address_code(tree)
                tac_output.extend(tac)

        except Exception as e:
            tac_output.append(f"# ERROR during parse: {e}")

        tac_win = tk.Toplevel()
        tac_win.title("Three Address Code")
        tac_win.geometry("600x400")

        output = scrolledtext.ScrolledText(tac_win, font=("Courier New", 12))
        output.pack(expand=True, fill=tk.BOTH)

        if tac_output:
            output.insert(tk.END, '\n'.join(tac_output))
        else:
            output.insert(tk.END, "# No valid TAC generated.")

    except Exception as e:
        messagebox.showerror("TAC Error", str(e))




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

        # Handle function definition
        if re.match(r"(create |define |make )?function (\w+)(?:\s+with\s+(.+))?", text):
            match = re.match(r"(create |define |make )?function (\w+)(?:\s+with\s+(.+))?", text)
            func_name = match.group(2)
            params = match.group(3) if match.group(3) else ""
            
            # Process parameters if they exist
            if params:
                # Split by "and" or comma for multiple parameters
                param_list = re.split(r",\s*|\s+and\s+", params)
                params = ", ".join(param.strip() for param in param_list)
            
            return indent + f"def {func_name}({params}):"

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

        # While loop - Enhanced to handle natural language expressions
        if "while" in text:
            # Try to extract a condition after "while"
            match = re.search(r"while\s+(.+?)(?:\s+do)?$", text)
            if match:
                condition = match.group(1).strip()
                
                # Process natural language conditions
                condition = process_condition(condition)
                
                return indent + f"while {condition}:"
            else:
                return indent + "while True:  # Condition not recognized"

        # If condition
        if text.startswith("if "):
            condition = text.replace("if", "", 1).strip()
            # Process natural language conditions
            condition = process_condition(condition)
            return indent + f"if {condition}:"

        # Else
        if text.strip() == "else":
            return indent + "else:"

        # For loop
        match = re.search(r"for\s+(\w+)\s+(?:in\s+range\s+)?from (\d+) to (\d+)", text)
        if match:
            var_name, start, end = match.groups()
            return indent + f"for {var_name} in range({start}, {int(end)+1}):"
        
        match = re.search(r"from (\d+) to (\d+)", text)
        if match:
            start, end = match.groups()
            return indent + f"for i in range({start}, {int(end)+1}):"

    return indent + f"# Unrecognized: {text}"

# Helper function to process natural language conditions
def process_condition(condition):
    # Map natural language comparative expressions to code
    condition = condition.strip()
    
    # Replace phrases with proper syntax
    condition = re.sub(r"(\w+)\s+is\s+greater\s+than\s+(\w+|\d+)", r"\1 > \2", condition)
    condition = re.sub(r"(\w+)\s+is\s+less\s+than\s+(\w+|\d+)", r"\1 < \2", condition)
    condition = re.sub(r"(\w+)\s+is\s+equal\s+to\s+(\w+|\d+)", r"\1 == \2", condition)
    condition = re.sub(r"(\w+)\s+equals\s+(\w+|\d+)", r"\1 == \2", condition)
    condition = re.sub(r"(\w+)\s+is\s+not\s+equal\s+to\s+(\w+|\d+)", r"\1 != \2", condition)
    condition = re.sub(r"(\w+)\s+is\s+greater\s+than\s+or\s+equal\s+to\s+(\w+|\d+)", r"\1 >= \2", condition)
    condition = re.sub(r"(\w+)\s+is\s+less\s+than\s+or\s+equal\s+to\s+(\w+|\d+)", r"\1 <= \2", condition)
    
    return condition

# Voice recognition
def speak(text):
    tts_engine.say(text)
    tts_engine.runAndWait()

def recognize_speech_thread():
    global user_code
    try:
        with sr.Microphone() as source:
            status_label.configure(text="🎤 Listening...")  
            app.update() 
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
            status_label.configure(text="🧠 Recognizing...")

            text = recognizer.recognize_google(audio)
            status_label.configure(text=f"You said: {text}")

            mapped_code = map_speech_to_code(text, current_language, user_code)
            code_box.insert("end", mapped_code + "\n")  
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
    code_box.delete("1.0", "end")
    status_label.configure(text="Editor cleared")

def on_tokenize():
    global user_code
    tokens = tokenize_code(user_code)
    show_tokens_window(tokens)

def sync_user_code():
    global user_code
    user_code = code_box.get("1.0", "end-1c") 
    status_label.configure(text="Code synced from editor.")

#==GUI==
import customtkinter as ctk

current_theme = "Dark"  
ctk.set_appearance_mode(current_theme)
ctk.set_default_color_theme("blue")

# Toggle Theme Function 
def switch_theme():
    global current_theme
    if current_theme == "Dark":
        ctk.set_appearance_mode("Light")
        current_theme = "Light"
    else:
        ctk.set_appearance_mode("Dark")
        current_theme = "Dark"

app = ctk.CTk()
app.title("🧠 VoxCoder - Voice-Based Python Compiler")
app.geometry("1000x800")

# === UI Layout ===
top_frame = ctk.CTkFrame(app)
top_frame.pack(fill="x", pady=10)

ctk.CTkLabel(top_frame, text="🧠 VoxCoder", font=ctk.CTkFont(size=26, weight="bold")).pack(side="left", padx=20)
ctk.CTkButton(top_frame, text="🌗 Toggle Theme", command=switch_theme).pack(side="right", padx=20)

status_label = ctk.CTkLabel(app, text="Click 🎤 Speak to start coding", font=ctk.CTkFont(size=12))
status_label.pack(pady=5)

button_frame = ctk.CTkFrame(app)
button_frame.pack(pady=10)

ctk.CTkButton(button_frame, text="🎤 Speak", width=120, command=recognize_speech).pack(side="left", padx=10)
ctk.CTkButton(button_frame, text="▶️ Run", width=120, command=run_code).pack(side="left", padx=10)
ctk.CTkButton(button_frame, text="🧹 Clear", width=120, command=clear_code).pack(side="left", padx=10)
ctk.CTkButton(button_frame, text="💾 Sync", width=120, command=sync_user_code).pack(side="left", padx=10)

# Feature buttons
tool_frame = ctk.CTkFrame(app)
tool_frame.pack(pady=5)

ctk.CTkButton(tool_frame, text="🧩 Tokenize", width=120, command=on_tokenize).pack(side="left", padx=10)
ctk.CTkButton(tool_frame, text="🌲 Annotated Tree", width=140, command=lambda: show_annotated_matplotlib_tree(user_code)).pack(side="left", padx=10)
ctk.CTkButton(tool_frame, text="📜 3-Address Code", width=160, command=show_three_address_code).pack(side="left", padx=10)
ctk.CTkButton(tool_frame, text="🌳 Parse Tree", width=120, command=lambda: show_matplotlib_tree(user_code)).pack(side="left", padx=10)

# === Editor & Output Areas ===
ctk.CTkLabel(app, text="Editor", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20)

code_box = ctk.CTkTextbox(app, height=320, font=("JetBrains Mono", 13))
code_box.pack(padx=20, pady=5, fill="both", expand=True)


footer = ctk.CTkLabel(app, text="Team Machinist | Let your voice be the keyboard", font=("Arial", 10, "italic"))
footer.pack(pady=10)

app.mainloop()
