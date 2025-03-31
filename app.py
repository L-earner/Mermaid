import os
import io
import asyncio
from flask import Flask, request, jsonify, render_template
from docx import Document
import openai # For OpenAI integration
from openai import OpenAI, AsyncOpenAI # Import the Async client as well
from dotenv import load_dotenv # Import load_dotenv
import httpx # Import httpx

# --- Configuration ---
# Load environment variables from .env file FIRST
load_dotenv()

# Now, access the environment variable
llm_api_key = os.getenv("OPENAI_API_KEY")
if not llm_api_key:
    print("Warning: OPENAI_API_KEY environment variable not set.")
    # Optionally, you could raise an error or disable LLM features
    # raise ValueError("OPENAI_API_KEY environment variable is required.")
else:
   # Initialize httpx client, ignoring environment proxies
   http_client = httpx.AsyncClient(trust_env=False)
   # Initialize your LLM client here, passing the custom http_client
   # Use AsyncOpenAI since our helper functions are async
   client = AsyncOpenAI(api_key=llm_api_key, http_client=http_client)
   print("OpenAI Async client initialized, ignoring environment proxies.") # Optional: Confirm client is ready

app = Flask(__name__)

# --- Routes ---
@app.route('/')
def index():
    """Renders the main page."""
    return render_template('index.html')

# --- Helper Functions ---

async def call_llm_for_initial_flowchart(process_text):
    """
    Calls the OpenAI API to generate Mermaid code from process text.
    """
    if not llm_api_key:
        return "graph TD\\nError[LLM API Key Not Configured]"

    prompt = f"""
    Convert the following process description into Mermaid flowchart syntax (using graph TD for top-down).
    Keep the flowchart clear and concise. Use brief node descriptions.
    Ensure the output is ONLY the Mermaid code block, starting with ```mermaid and ending with ```.

    Process Description:
    ---
    {process_text}
    ---

    Mermaid Code:
    """
    try:
        # Use the initialized client instance
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo", # Or "gpt-4" if preferred and available
            messages=[
                {"role": "system", "content": "You are an expert in generating Mermaid flowchart syntax."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5, # Adjust creativity vs determinism
            max_tokens=1000 # Limit response length
        )
        mermaid_code = response.choices[0].message.content.strip()

        # Basic cleanup: Extract content within ```mermaid ... ``` if present
        if mermaid_code.startswith("```mermaid"):
            mermaid_code = mermaid_code[len("```mermaid"):].strip()
        if mermaid_code.endswith("```"):
            mermaid_code = mermaid_code[:-len("```")].strip()

        # Further validation could be added here (e.g., check for 'graph TD')
        if not mermaid_code.strip().startswith("graph"):
             print("Warning: LLM response doesn't look like Mermaid code:", mermaid_code)
             # Fallback or error handling
             return "graph TD\\nError[LLM did not return valid Mermaid code]"

        return mermaid_code

    except Exception as e:
        print(f"Error calling OpenAI API (Initial): {e}")
        return f"graph TD\\nError[Error calling LLM: {e}]"


async def call_llm_for_refinement(current_mermaid, instruction):
    """
    Calls the OpenAI API to refine existing Mermaid code based on instructions.
    """
    if not llm_api_key:
        return current_mermaid + "\\n%% Error: LLM API Key Not Configured"

    prompt = f"""
    Refine the following Mermaid flowchart based on the user's instruction.
    Output ONLY the complete, updated Mermaid code block, starting with ```mermaid and ending with ```.
    Do not include explanations or apologies.

    Current Mermaid Code:
    ---
    ```mermaid
    {current_mermaid}
    ```
    ---

    User Instruction:
    ---
    {instruction}
    ---

    Updated Mermaid Code:
    """
    try:
        # Use the initialized client instance
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo", # Or "gpt-4"
            messages=[
                {"role": "system", "content": "You are an expert in refining Mermaid flowchart syntax based on instructions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=1500
        )
        updated_mermaid_code = response.choices[0].message.content.strip()

        # Basic cleanup
        if updated_mermaid_code.startswith("```mermaid"):
            updated_mermaid_code = updated_mermaid_code[len("```mermaid"):].strip()
        if updated_mermaid_code.endswith("```"):
            updated_mermaid_code = updated_mermaid_code[:-len("```")].strip()

        # Further validation
        if not updated_mermaid_code.strip().startswith("graph"):
             print("Warning: LLM refinement response doesn't look like Mermaid code:", updated_mermaid_code)
             # Fallback: return original code with comment
             return current_mermaid + f"\\n%% LLM Error: Invalid refinement response"

        return updated_mermaid_code

    except Exception as e:
        print(f"Error calling OpenAI API (Refinement): {e}")
        return current_mermaid + f"\\n%% LLM Error: {e}"


def extract_text_from_docx(file_stream):
    """
    Extracts text content from a DOCX file stream.

    Args:
        file_stream: A file-like object (e.g., from request.files).

    Returns:
        A string containing the extracted text, or None if an error occurs.
    """
    try:
        document = Document(file_stream)
        full_text = []
        for para in document.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        # Consider logging the error more formally
        return None

# --- API Endpoints ---
@app.route('/generate', methods=['POST'])
def generate_flowchart():
    """
    Generates the initial Mermaid flowchart from text or a DOCX file.
    """
    process_text = None
    error_message = None

    try:
        # Check for file upload first
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                error_message = "No file selected."
            elif file and file.filename.lower().endswith('.docx'):
                # Use io.BytesIO to treat the file stream correctly
                file_stream = io.BytesIO(file.read())
                process_text = extract_text_from_docx(file_stream)
                if process_text is None:
                    error_message = "Error extracting text from DOCX file."
            else:
                error_message = "Invalid file type. Please upload a .docx file."
        # If no valid file, check for text input
        elif 'text' in request.form:
            process_text = request.form['text'].strip()
            if not process_text:
                error_message = "Text input cannot be empty."

        # If neither input is valid or text extraction failed
        if error_message:
            return jsonify({"error": error_message}), 400
        if process_text is None:
             return jsonify({"error": "No valid input provided (text or .docx file)."}), 400

        # --- LLM Call ---
        print(f"Generating flowchart for text (length: {len(process_text)} chars)")
        # Run the async function synchronously within the Flask route
        mermaid_code = asyncio.run(call_llm_for_initial_flowchart(process_text))
        print("LLM generation complete.")
        # --- End LLM Call ---

        return jsonify({"mermaid_code": mermaid_code})

    except Exception as e:
        print(f"Error in /generate route: {e}")
        # Consider more specific error logging
        return jsonify({"error": "An unexpected error occurred on the server."}), 500

@app.route('/refine', methods=['POST'])
def refine_flowchart():
    """
    Refines the existing Mermaid flowchart based on user instructions.
    Expects JSON data: {'current_mermaid': '...', 'instruction': '...'}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request data. Expected JSON."}), 400

        current_mermaid = data.get('current_mermaid')
        instruction = data.get('instruction')

        if not current_mermaid or not instruction:
            return jsonify({"error": "Missing 'current_mermaid' or 'instruction' in request."}), 400

        # --- LLM Call ---
        print(f"Refining flowchart with instruction: '{instruction}'")
        # Run the async function synchronously within the Flask route
        updated_mermaid = asyncio.run(call_llm_for_refinement(current_mermaid, instruction))
        print("LLM refinement complete.")
        # --- End LLM Call ---

        return jsonify({"mermaid_code": updated_mermaid})

    except Exception as e:
        print(f"Error in /refine route: {e}")
        # Consider more specific error logging
        return jsonify({"error": "An unexpected error occurred during refinement."}), 500


# --- Main Execution ---
if __name__ == '__main__':
    # Note: Setting debug=True is convenient for development but should be
    # disabled in production for security and performance reasons.
    app.run(debug=True)
