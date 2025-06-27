# 🎙️ VoxCoder - Voice-Based Python Compiler

**VoxCoder** is an intelligent, voice-enabled Python compiler that transforms spoken programming instructions into functional code. Built with **Tkinter**, **CustomTkinter**, **SpeechRecognition**, and **Matplotlib**, VoxCoder provides a powerful GUI for compiling, visualizing, and executing Python code — all through voice commands.

---

## 🚀 Features

- 🎤 **Voice to Code**: Speak to generate Python code.
- 🧠 **Natural Language Mapping**: Converts spoken phrases like "create function add with a and b" into valid code.
- 🌗 **Theme Toggle**: Switch between light and dark themes.
- 🧹 **Code Editor**: CustomTkinter-based editor for editing and running generated code.
- 🧩 **Tokenization**: Break down your code into lexical tokens.
- 🌲 **Parse Trees**:
  - Standard parse tree visualization
  - Annotated semantic tree with value propagation
- 📜 **Three Address Code Generation**: Generates intermediate representation for expressions and assignments.

---

## 📦 Requirements

Make sure you have Python 3.x and the following libraries installed:

```bash
pip install speechrecognition pyttsx3 customtkinter matplotlib lark pillow
```

> For microphone access, ensure you also have:
```bash
sudo apt-get install portaudio19-dev  # (Linux only)
pip install pyaudio
```

---

## 🛠️ How to Run

1. **Clone the Repository**:
```bash
git clone https://github.com/Pranav-Uniyal/Vox-Coder-Voice-Enabled-Compiler.git
cd Vox-Coder-Voice-Enabled-Compiler
```

2. **Run the Compiler**:
```bash
python main.py
```
## 📸 Screenshots

### 🧠 VoxCoder Interface
![VoxCoder-GUI-Dark](https://github.com/user-attachments/assets/b433dc95-0a89-4960-a7d4-57ca67af17a7)
![VoxCoder-GUI-Light](https://github.com/user-attachments/assets/c833837b-1dc0-44c7-b7cb-167f579d4867)



### 🎤 Voice to Code in Action
![Voice Command Demo](https://github.com/user-attachments/assets/b66f31f9-cb97-4f69-9537-408b4d712860)

### 🧩 Tokenization
![Tokenization](https://github.com/user-attachments/assets/d2d659e3-f989-4ac3-9233-1c1d726e7712)

### 🌳 Parse Tree Visualization
![Parse Tree](https://github.com/user-attachments/assets/3f5f2dd5-bc09-48a4-9bec-dc4009279049)

### 🌳 Annotated Parse Tree Visualization
![Annotated Parse Tree](https://github.com/user-attachments/assets/d4a111d8-c775-44fa-999a-ab84569c40c2)

### 📜 Three Address Code Output
![TAC](https://github.com/user-attachments/assets/5fd938ce-7c1b-4db5-b65c-8b3557d0603c)


## 🎓 Educational Value

VoxCoder is ideal for:
- Students learning compiler design
- Practicing speech-to-code integration
- Visualizing parsing, tokenization, and code generation

---

## 🧠 Project Highlights

| Module                  | Purpose                                         |
|------------------------|-------------------------------------------------|
| Speech Mapping          | Converts phrases to code using regex & rules   |
| Tokenizer               | Lexical analyzer for Python                     |
| Annotated Parse Tree    | Evaluates and visualizes computation steps     |
| 3-Address Code Generator| Generates TAC for expressions                  |
| CustomTkinter GUI       | Interactive GUI with modern components         |

---

## 👨‍💻 Author

Developed by **Pranav Uniyal**, **Parthvi Sah**, **Soni Pathak**, **Srijan Petwal**  
GitHub: [Pranav-Uniyal](https://github.com/Pranav-Uniyal)

---

## 📜 License

This project is licensed under the MIT License.
