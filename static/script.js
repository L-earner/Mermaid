document.addEventListener('DOMContentLoaded', () => {
    // Initialize Mermaid.js - disable auto-rendering
    mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' }); // Use 'loose' to allow dynamic rendering

    // --- DOM Element References ---
    const generateBtn = document.getElementById('generate-btn');
    const refineBtn = document.getElementById('refine-btn');
    const processTextInput = document.getElementById('process-text');
    const processFileInput = document.getElementById('process-file');
    const chatInstructionInput = document.getElementById('chat-instruction');
    const flowchartSection = document.getElementById('flowchart-section');
    const mermaidContainer = document.getElementById('mermaid-container');
    const mermaidCodeDisplay = document.getElementById('mermaid-code-display'); // Hidden pre tag
    const chatHistory = document.getElementById('chat-history');
    const loadingInitial = document.getElementById('loading-initial');
    const errorInitial = document.getElementById('error-initial');
    const loadingRefine = document.getElementById('loading-refine');
    const errorRefine = document.getElementById('error-refine');

    // --- Helper Functions ---
    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        // Define entities to avoid issues with literal quotes in replace
        const entities = {
            '&': '&', // Use '&' for ampersand
            '<': '<',  // Use '<' for less than
            '>': '>',  // Use '>' for greater than
            '"': '"', // Use '"' for double quote
            "'": '&#039;' // Use '&#039;' for single quote
        };
        // Use a regex to replace characters with their corresponding entities
        return unsafe.replace(/[&<>"']/g, char => entities[char]);
    }


    function addChatMessage(sender, message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'system-message');
        // Use textContent to prevent XSS from Mermaid code potentially containing HTML
        messageDiv.textContent = message;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to bottom
    }

    function showError(element, message) {
        element.textContent = message;
        element.style.display = 'block';
    }

    function clearErrors() {
        errorInitial.style.display = 'none';
        errorInitial.textContent = '';
        errorRefine.style.display = 'none';
        errorRefine.textContent = '';
    }

    async function renderFlowchart(mermaidCode) {
        clearErrors(); // Clear previous errors before attempting render
        if (!mermaidCode) {
            mermaidContainer.innerHTML = '<p>No flowchart code to render.</p>';
            return;
        }
        mermaidContainer.innerHTML = ''; // Clear previous chart

        try {
            // Use mermaid.render to generate SVG
            // Provide a unique ID for the temporary div
            const renderId = 'mermaid-render-' + Date.now();
            const { svg } = await mermaid.render(renderId, mermaidCode);
            mermaidContainer.innerHTML = svg;
            mermaidCodeDisplay.textContent = mermaidCode; // Store the successfully rendered code
            flowchartSection.style.display = 'block'; // Show the section
        } catch (error) {
            console.error("Mermaid rendering error:", error);
            showError(errorRefine, `Mermaid Syntax Error: ${error.message}. Please check the generated code or refine.`);
            // Display the problematic code for debugging
            // Use the corrected escapeHtml function here
            mermaidContainer.innerHTML = `<pre><code>${escapeHtml(mermaidCode)}</code></pre>`;
            mermaidCodeDisplay.textContent = mermaidCode; // Store even if rendering failed, for refinement
            flowchartSection.style.display = 'block'; // Still show section to allow refinement
        }
    }

    // --- Event Handlers ---
    async function handleInitialGeneration() {
        clearErrors();
        loadingInitial.style.display = 'block';
        flowchartSection.style.display = 'none'; // Hide flowchart section initially
        chatHistory.innerHTML = ''; // Clear previous chat
        mermaidContainer.innerHTML = ''; // Clear previous flowchart
        mermaidCodeDisplay.textContent = ''; // Clear stored code

        const text = processTextInput.value.trim();
        const file = processFileInput.files[0];
        const formData = new FormData();

        if (file) {
            formData.append('file', file);
        } else if (text) {
            formData.append('text', text);
        } else {
            showError(errorInitial, 'Please provide process description text or upload a .docx file.');
            loadingInitial.style.display = 'none';
            return;
        }

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }

            if (result.mermaid_code) {
                await renderFlowchart(result.mermaid_code);
                // Optionally clear the input fields after successful generation
                // processTextInput.value = '';
                // processFileInput.value = ''; // Reset file input
            } else {
                 showError(errorInitial, 'Failed to generate flowchart. No Mermaid code received.');
            }

        } catch (error) {
            console.error('Error during initial generation:', error);
            showError(errorInitial, `Generation failed: ${error.message}`);
        } finally {
            loadingInitial.style.display = 'none';
        }
    }

    async function handleRefinement() {
        clearErrors();
        const instruction = chatInstructionInput.value.trim();
        const currentMermaid = mermaidCodeDisplay.textContent; // Get code from hidden pre

        if (!instruction) {
            showError(errorRefine, 'Please enter a refinement instruction.');
            return;
        }
        if (!currentMermaid) {
            showError(errorRefine, 'No current flowchart to refine. Generate one first.');
            return;
        }

        loadingRefine.style.display = 'block';
        addChatMessage('user', instruction); // Show user message immediately

        try {
            const response = await fetch('/refine', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    current_mermaid: currentMermaid,
                    instruction: instruction,
                }),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }

            if (result.mermaid_code) {
                await renderFlowchart(result.mermaid_code);
                addChatMessage('system', 'Flowchart updated.'); // Add system confirmation
                chatInstructionInput.value = ''; // Clear input field
            } else {
                showError(errorRefine, 'Refinement failed. No updated Mermaid code received.');
                addChatMessage('system', 'Sorry, I could not refine the flowchart.');
            }

        } catch (error) {
            console.error('Error during refinement:', error);
            showError(errorRefine, `Refinement failed: ${error.message}`);
            addChatMessage('system', `Error: ${error.message}`);
        } finally {
            loadingRefine.style.display = 'none';
        }
    }

    // --- Event Listeners ---
    generateBtn.addEventListener('click', handleInitialGeneration);
    refineBtn.addEventListener('click', handleRefinement);
    chatInstructionInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent default form submission if it were in a form
            handleRefinement();
        }
    });

    // Clear file input if text is entered, and vice-versa (optional usability)
    processTextInput.addEventListener('input', () => {
        if (processTextInput.value.trim() !== '') {
            processFileInput.value = ''; // Clear file input
        }
    });
    processFileInput.addEventListener('change', () => {
         if (processFileInput.files.length > 0) {
            processTextInput.value = ''; // Clear text area
        }
    });

});
