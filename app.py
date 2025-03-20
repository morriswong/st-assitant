import os
import io
import logging
import queue
import json
import time
import base64
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv()

import streamlit as st
from openai import AzureOpenAI
from streamlit import session_state as ss
from PIL import Image

# Constants
AZURE_DEPLOYMENT_NAME_FALLBACK = "gpt-4o"  # Default deployment name
AZURE_ASSISTANT_ID_FALLBACK = "assistant_id_fallback"

# Configure page
st.set_page_config(page_title="Data Analysis Assistant", page_icon="📊", layout="centered")

# Apply custom CSS
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def init_logging():
    logging.basicConfig(format="[%(asctime)s] %(levelname)+8s: %(message)s")
    local_logger = logging.getLogger()
    local_logger.setLevel(logging.INFO)
    return local_logger
logger = init_logging()

@st.cache_resource(show_spinner=False)
def create_assistants_client():
    logger.info("Creating Azure OpenAI client")
    
    # Get API key and endpoint
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    
    if not api_key or not endpoint:
        st.error("Azure OpenAI API key or endpoint not found. Please check your .env.local file.")
        logger.error(f"API Key present: {bool(api_key)}, Endpoint present: {bool(endpoint)}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Environment variables: {[key for key in os.environ.keys() if 'AZURE' in key]}")
        st.stop()
    
    logger.info(f"Using Azure OpenAI endpoint: {endpoint}")
    
    try:
        azure_client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2024-05-01-preview",
        )
        return azure_client
    except Exception as e:
        st.error(f"Error creating Azure OpenAI client: {e}")
        logger.error(f"Error creating Azure OpenAI client: {e}")
        st.stop()

# Initialize client
client = create_assistants_client()

# Initialize session state
if 'tool_requests' not in ss:
    ss['tool_requests'] = queue.Queue()
tool_requests = ss['tool_requests']

if "file_uploaded" not in ss:
    ss.file_uploaded = False

if "messages" not in ss:
    ss.messages = []

if "thread_id" not in ss:
    ss.thread_id = None

if "file_ids" not in ss:
    ss.file_ids = []

if "assistant_created_file_ids" not in ss:
    ss.assistant_created_file_ids = []

# Helper functions
def moderation_endpoint(text):
    """Check if text is flagged by the moderation endpoint"""
    try:
        response = client.moderations.create(input=text)
        return response.results[0].flagged
    except Exception as e:
        logger.error(f"Error checking moderation: {e}")
        return False

def delete_files(file_id_list):
    """Delete files from OpenAI"""
    for file_id in file_id_list:
        try:
            client.files.delete(file_id)
            logger.info(f"Deleted file: {file_id}")
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")

def delete_thread(thread_id):
    """Delete a thread"""
    try:
        client.beta.threads.delete(thread_id)
        logger.info(f"Deleted thread: {thread_id}")
    except Exception as e:
        logger.error(f"Error deleting thread {thread_id}: {e}")

def retrieve_assistant_created_files(thread_id):
    """Retrieve files created by the assistant in a thread"""
    assistant_created_file_ids = []
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        for message in messages.data:
            if message.role == "assistant":
                for attachment in message.attachments:
                    assistant_created_file_ids.append(attachment.file_id)
    except Exception as e:
        logger.error(f"Error retrieving assistant files: {e}")
    return assistant_created_file_ids

def render_download_files(file_id_list):
    """Render download buttons for files and return file data"""
    downloaded_files = []
    file_names = []
    
    if len(file_id_list) > 0:
        st.markdown("### 📂 Generated Files")
        for file_id in file_id_list:
            try:
                file_data = client.files.content(file_id)
                file = file_data.read()
                file_name = client.files.retrieve(file_id).filename
                
                # Store the downloaded file and its name
                downloaded_files.append(file)
                file_names.append(file_name)
                
                # Display the download button
                st.download_button(
                    label=f"Download {file_name}",
                    data=file,
                    file_name=file_name,
                    mime="application/octet-stream"
                )
            except Exception as e:
                logger.error(f"Error downloading file {file_id}: {e}")
    
    return downloaded_files, file_names

# Tool functions
def analyze_data(dataset_name: str, question: str) -> str:
    """
    Analyze the provided dataset based on the question
    """
    time.sleep(2)  # Simulate processing time
    return f"Analysis of {dataset_name} complete. The answer to '{question}' is in the generated visualizations and data."

# Tool handling
def handle_requires_action(tool_request):
    st.toast("Running data analysis...", icon="📊")
    tool_outputs = []
    data = tool_request.data
    
    for tool in data.required_action.submit_tool_outputs.tool_calls:
        if tool.function.arguments:
            function_arguments = json.loads(tool.function.arguments)
        else:
            function_arguments = {}
            
        match tool.function.name:
            case "analyze_data":
                logger.info("Calling analyze_data function")
                answer = analyze_data(**function_arguments)
                tool_outputs.append({"tool_call_id": tool.id, "output": answer})
            case _:
                logger.error(f"Unrecognized function name: {tool.function.name}. Tool: {tool}")
                ret_val = {
                    "status": "error",
                    "message": f"Function name is not recognized. Please check your request structure."
                }
                tool_outputs.append({"tool_call_id": tool.id, "output": json.dumps(ret_val)})
                
    st.toast("Analysis complete", icon="✅")
    return tool_outputs, data.thread_id, data.id

# Streaming functions
def data_streamer():
    """Stream data from the assistant"""
    logger.info(f"Starting data streamer on {ss.stream}")
    st.toast("Analyzing data...", icon="🔍")
    content_produced = False
    
    for response in ss.stream:
        match response.event:
            case "thread.message.delta":
                content = response.data.delta.content[0]
                match content.type:
                    case "text":
                        value = content.text.value
                        content_produced = True
                        yield value
                    case "image_file":
                        logger.info(f"Image file: {content}")
                        image_content = io.BytesIO(client.files.content(content.image_file.file_id).read())
                        
                        # Save the image for download later
                        ss.assistant_created_file_ids.append(content.image_file.file_id)
                        
                        content_produced = True
                        yield Image.open(image_content)
            case "thread.run.requires_action":
                logger.info(f"Run requires action: {response}")
                tool_requests.put(response)
                if not content_produced:
                    yield "[Running data analysis...]"
                return
            case "thread.run.failed":
                logger.error(f"Run failed: {response}")
                yield "[Analysis failed. Please try again.]"
                return
                
    st.toast("Analysis complete", icon="✅")
    logger.info(f"Finished data streamer on {ss.stream}")

def add_message_to_state_session(message):
    """Add a message to the session state"""
    if message and (isinstance(message, str) and len(message) > 0 or not isinstance(message, str)):
        ss.messages.append({"role": "assistant", "content": message})

def display_stream(content_stream, create_context=True):
    """Display the streaming content"""
    ss.stream = content_stream
    
    if create_context:
        with st.chat_message("assistant", avatar="📊"):
            response = st.write_stream(data_streamer)
    else:
        response = st.write_stream(data_streamer)
        
    if response is not None:
        if isinstance(response, list):
            # Multiple messages in the response
            for message in response:
                add_message_to_state_session(message)
        else:
            # Single message in response
            add_message_to_state_session(response)

# Main application
def main():
    st.title("📊 Data Analysis Assistant")
    st.markdown("Upload your dataset and ask questions to analyze it.")
    
    # Initialize or retrieve the assistant
    if "assistant" not in ss:
        try:
            # Try to retrieve existing assistant
            assistant_id = os.environ.get("AZURE_ASSISTANT_ID", AZURE_ASSISTANT_ID_FALLBACK)
            assistant = client.beta.assistants.retrieve(assistant_id=assistant_id)
            logger.info(f"Located assistant: {assistant.name}")
        except Exception as e:
            logger.info(f"Creating new assistant: {e}")
            # Create a new assistant if not found
            deployment_name = os.environ.get("AZURE_DEPLOYMENT_NAME", AZURE_DEPLOYMENT_NAME_FALLBACK)
            assistant = client.beta.assistants.create(
                name="Data Analysis Assistant",
                instructions="""You are a data analysis assistant. Your job is to help analyze datasets and answer questions about them.
                When analyzing data:
                1. First, explore and understand the dataset structure
                2. Clean and preprocess the data as needed
                3. Perform the requested analysis
                4. Create visualizations when appropriate
                5. Explain your findings in clear, non-technical language
                
                Always be concise and focus on the most important insights.
                """,
                tools=[
                    {"type": "code_interpreter"},
                    {"type": "function", "function": {
                        "name": "analyze_data",
                        "description": "Analyze a dataset based on a specific question",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "dataset_name": {"type": "string"},
                                "question": {"type": "string"}
                            },
                            "required": ["dataset_name", "question"]
                        }
                    }}
                ],
                model=deployment_name
            )
            logger.info(f"Created new assistant: {assistant.id}")
        ss["assistant"] = assistant
    assistant = ss["assistant"]
    
    # File upload section
    if not ss.file_uploaded:
        with st.container():
            st.subheader("Step 1: Upload Your Dataset")
            uploaded_files = st.file_uploader(
                "Upload CSV, Excel, or other data files",
                accept_multiple_files=True,
                type=["csv", "xlsx", "xls", "json", "txt"]
            )
            
            if uploaded_files and st.button("Upload and Analyze", type="primary"):
                ss.file_ids = []
                
                with st.spinner("Uploading files..."):
                    for file in uploaded_files:
                        try:
                            oai_file = client.files.create(
                                file=file,
                                purpose='assistants'
                            )
                            ss.file_ids.append(oai_file.id)
                            logger.info(f"Uploaded file: {file.name} with ID: {oai_file.id}")
                        except Exception as e:
                            st.error(f"Error uploading {file.name}: {e}")
                            continue
                
                if ss.file_ids:
                    st.success(f"✅ Successfully uploaded {len(ss.file_ids)} file(s)")
                    ss.file_uploaded = True
                    st.rerun()
    
    # Analysis section
    if ss.file_uploaded:
        st.subheader("Step 2: Ask Questions About Your Data")
        
        # Display uploaded files
        st.info(f"📁 {len(ss.file_ids)} file(s) uploaded and ready for analysis")
        
        # Create a thread if not already created
        if not ss.thread_id:
            thread = client.beta.threads.create()
            ss.thread_id = thread.id
            logger.info(f"Created new thread: {ss.thread_id}")
            
            # Attach files to the thread
            client.beta.threads.update(
                thread_id=ss.thread_id,
                tool_resources={"code_interpreter": {"file_ids": ss.file_ids}}
            )
        
        # Display chat history
        for message in ss.messages:
            with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "📊"):
                if isinstance(message["content"], str):
                    st.markdown(message["content"])
                else:
                    # Handle non-text content like images
                    st.image(message["content"])
        
        # Question input
        question = st.chat_input("Ask a question about your data...")
        
        if question:
            # Check moderation
            if moderation_endpoint(question):
                st.error("⚠️ Your question has been flagged. Please try a different question.")
                return
            
            # Display user question
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(question)
            
            # Add to message history
            ss.messages.append({"role": "user", "content": question})
            
            # Send question to assistant
            client.beta.threads.messages.create(
                thread_id=ss.thread_id,
                role="user",
                content=question
            )
            
            # Run the assistant
            with client.beta.threads.runs.stream(
                thread_id=ss.thread_id,
                assistant_id=assistant.id,
            ) as stream:
                # Display streaming response
                display_stream(stream)
                
                # Handle tool calls
                while not tool_requests.empty():
                    logger.info("Handling tool requests")
                    with st.chat_message("assistant", avatar="📊"):
                        tool_outputs, thread_id, run_id = handle_requires_action(tool_requests.get())
                        with client.beta.threads.runs.submit_tool_outputs_stream(
                            thread_id=thread_id,
                            run_id=run_id,
                            tool_outputs=tool_outputs
                        ) as tool_stream:
                            display_stream(tool_stream, create_context=False)
            
            # Get files created by the assistant
            ss.assistant_created_file_ids = retrieve_assistant_created_files(ss.thread_id)
            
            # Render download buttons for generated files
            if ss.assistant_created_file_ids:
                render_download_files(ss.assistant_created_file_ids)
        
        # Reset button
        if st.button("Start New Analysis", type="secondary"):
            # Clean up
            if ss.thread_id:
                delete_thread(ss.thread_id)
            if ss.file_ids:
                delete_files(ss.file_ids)
            if ss.assistant_created_file_ids:
                delete_files(ss.assistant_created_file_ids)
            
            # Reset session state
            ss.file_uploaded = False
            ss.messages = []
            ss.thread_id = None
            ss.file_ids = []
            ss.assistant_created_file_ids = []
            
            st.rerun()

# Run the app
if __name__ == "__main__":
    main()