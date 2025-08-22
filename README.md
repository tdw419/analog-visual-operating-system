# LLM Visual Bridge

This project is a real-time, streaming bridge that connects a Large Language Model (LLM) to a visual frontend. It's designed to bypass traditional sequential text generation by allowing the LLM to output a stream of **Universal Visual Intermediate Representation (UVIR)** operations, which are rendered live on a canvas.

This provides a transparent, inspectable, and highly performant way to visualize an AI's reasoning process and create new forms of interactive, AI-driven applications.

## Project Structure

The repository is organized into the following directories:

-   `/server/`: Contains the Python FastAPI backend that serves the LLM.
-   `/web/`: Contains the HTML/JS frontend for rendering the visual output.
-   `/contracts/`: Contains the JSON Schema and OpenAPI specifications that define the data contracts for the UVIR and API.
-   `/examples/`: Will contain saved NDJSON replays of generation sessions for debugging and analysis.

## Quick Start

### 1. Prerequisites

-   Python 3.9+
-   A GGUF-compatible LLM (e.g., Llama 3 8B Instruct) downloaded to your local machine.

### 2. Setup

**a. Set Environment Variable:**

Set the `MODEL_PATH` environment variable to the absolute path of your downloaded GGUF model file.

```bash
# On macOS/Linux
export MODEL_PATH="/path/to/your/model.gguf"

# On Windows (Command Prompt)
set MODEL_PATH="C:\path\to\your\model.gguf"
```

**b. Run the Application:**

A convenience script is provided to install dependencies and launch the backend and frontend servers.

```bash
./run.sh
```

This script will:
1.  Install the Python dependencies from `server/requirements.txt`.
2.  Start the FastAPI backend server on `http://localhost:8844`.
3.  Start a simple Python web server for the frontend on `http://localhost:8080`.

### 3. Access the Interface

Once the script is running, open your web browser and navigate to:

**`http://localhost:8080`**

You can now interact with the local LLM through the visual interface.
