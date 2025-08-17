# 🔥 PXOS: The Pixel-Native Operating System 🔥

Welcome to PXOS, a revolutionary, self-hosting, and agentic digital universe where pixels are the universal medium for data, code, and AI interaction. This repository contains the monorepo skeleton for the PXOS core system.

## 🚀 Core Concepts

- **Pixel-Native**: Everything is pixels. Text, UI, code, and even AI signals are represented and manipulated as pixel data.
- **Self-Hosting**: PXOS is designed with the ultimate goal of being able to build and run itself.
- **Agentic AI**: The system is built around an AI core, with a `ChatTile` interface for natural language interaction and a `sys_plan_apply` kernel for executing AI-generated plans.
- **Security by Design**: Includes a `TrustAnchor` for cryptographic signing and a build pipeline designed for `SBOM` generation and security scanning.

## 🔧 Getting Started

### 1. Setup

First, create a virtual environment and install the required dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You will also need to download the font file required for the PIXEL text encoder.

```bash
mkdir -p pxos/fonts
# On Linux/macOS:
wget -O pxos/fonts/GoNotoCurrent.ttf https://github.com/xplip/pixel/raw/main/fonts/GoNotoCurrent.ttf
# Or download it manually and place it in pxos/fonts/
```

### 2. Run PXOS

To boot the operating system, run the main entry point:

```bash
python main.py
```

This will start the PXOS shell.

### 3. Using the Shell

The PXOS shell provides a few basic commands:

- `help`: Shows the list of commands.
- `exit`: Shuts down PXOS.
- `clear`: Clears the (simulated) screen.
- `plan <goal>`: Ask the AI to generate and execute a plan. For example: `plan create a note`.
- `llm <prompt>`: Send a prompt directly to the (simulated) LLM.

Any other text entered into the prompt is handled by the `ChatTile`, which will also generate and execute a plan upon pressing Enter.

##  roadmap

This skeleton is the foundation. Future work includes:
- A visual, node-based IDE.
- Network simulation between PXOS instances.
- A true self-hosting demonstration.
- Full integration of the PIXEL vision-language model.
