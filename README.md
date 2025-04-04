# Mermaid Flowchart Generator

This project is a web application that uses AI (specifically OpenAI's GPT models) to automatically generate and refine Mermaid flowchart diagrams from text descriptions or uploaded DOCX files.

## Features

*   **Generate from Text:** Input a description of a process, and the application will generate the corresponding Mermaid flowchart code.
*   **Generate from DOCX:** Upload a `.docx` file containing a process description, and the application will extract the text and generate the flowchart.
*   **Refine Flowchart:** Provide instructions to modify an existing Mermaid flowchart, and the AI will attempt to update the code accordingly.
*   **Interactive UI:** Simple web interface to input text/files, view the generated flowchart, and provide refinement instructions.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/L-earner/Mermaid.git
    cd Mermaid
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure API Key:**
    *   Rename the `.env.example` file (if provided) or create a new file named `.env` in the project root.
    *   Add your OpenAI API key to the `.env` file:
        ```
        OPENAI_API_KEY='your_openai_api_key_here'
        ```
    *   **Important:** Ensure `.env` is listed in your `.gitignore` file to prevent accidentally committing your API key.

## Usage

1.  **Run the Flask application:**
    ```bash
    python app.py
    ```
2.  Open your web browser and navigate to `http://127.0.0.1:5000` (or the address provided in the terminal).
3.  Use the interface to generate or refine flowcharts.
