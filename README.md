# Analog Visual Computing Project

This project explores a novel paradigm for computing that bypasses traditional compilation in favor of direct visual execution. The core idea is to treat code and AI model outputs not as abstract instructions for a hidden virtual machine, but as a sequence of visual, inspectable, and interactive events.

This repository contains two main prototypes that demonstrate this concept:
1.  An **Analog Timeline Editor** for creating keyframed animations.
2.  A **Visual LLM Interface** for interacting with Large Language Models in a more direct, visual way.

---

## 1. Analog Timeline Editor

The `index.html` file is a sophisticated, self-contained timeline editor for creating keyframed animations.

### Key Features
- **Interactive Timeline:** Drag the playhead, zoom, and pan to navigate your animation.
- **Keyframe Manipulation:** Add, delete, duplicate, and drag keyframes directly on the timeline.
- **Live Preview:** A pixel-perfect preview canvas that renders the animation in real-time, using a custom 5x7 bitmap font for a retro aesthetic.
- **Project Persistence:** Work is automatically saved to your browser's `localStorage`. You can also import and export projects as JSON files.
- **Journal Lane:** A conceptual "commit strobe" that flashes when you save or export, tying into the analog OS theme.

### How to Use
1.  Open the `index.html` file in a modern web browser.
2.  Use the controls to create and manipulate keyframes.
3.  The editor is ready to use out-of-the-box, with no dependencies required.

---

## 2. Visual LLM Interface

This component demonstrates how the "analog bypass" concept can be applied to Large Language Models. It consists of a Python backend server and an HTML frontend client.

### The Core Concept
Instead of the traditional, slow, sequential text generation, this system allows an LLM to emit a stream of **Visual IR (Intermediate Representation)** commands. The frontend renders these commands instantly, providing a real-time visualization of the AI's "thinking" process.

### How to Run
**1. Install Dependencies:**
You will need Python 3.9+ and the following packages:
```bash
pip install fastapi uvicorn sse-starlette llama-cpp-python
```

**2. Download a Model:**
This system is designed to run local GGUF models. Download a model of your choice, for example, Llama 3 8B Instruct.

**3. Set Environment Variable:**
Set the `MODEL_PATH` environment variable to the absolute path of your downloaded GGUF model file.
```bash
# On macOS/Linux
export MODEL_PATH="/path/to/your/model.gguf"

# On Windows (Command Prompt)
set MODEL_PATH="C:\path\to\your\model.gguf"
```

**4. Run the Backend Server:**
In your terminal, run the following command:
```bash
uvicorn server:py --reload --port 8844
```
The server will start on `http://localhost:8844`.

**5. Run the Frontend:**
To avoid CORS issues, you need to serve the `llm_interface.html` file from a local web server. The simplest way is to use Python's built-in server. Open a **new terminal** in the project directory and run:
```bash
python -m http.server 8080
```
Then, open your web browser and navigate to:
**`http://localhost:8080/llm_interface.html`**

You can now interact with the local LLM through the visual interface.

---

## The Universal Visual IR (UVIR)

The underlying concept that connects these tools is the **Universal Visual IR**. This is a simple, JSON-based "opcode" language for describing visual events. It includes commands like `TEXT`, `BAR`, `RECT`, and `LINK`.

The goal is to create a universal language that any program or AI model can compile to, and any visual renderer can execute. This decouples the logic from the rendering and makes computation transparent and inspectable.
