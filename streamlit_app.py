import streamlit as st
import requests
import time
import uuid
from datetime import datetime
import re 

st.set_page_config(
    page_title="LA Property Analysis",
    layout="wide"
)

st.title("LA Property Analysis")

API_URL = "http://localhost:8000"

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

if 'current_address' not in st.session_state:
    st.session_state.current_address = ""

def validate_address(house_number, street_name):
    """Validate that house_number is numeric and street_name contains only English letters and allowed characters."""
    if not house_number.isdigit():
        return False, "House number must be numeric."
    if not re.match(r'^[A-Za-z0-9\s\.,-]+$', street_name):
        return False, "Street name must contain only English letters and valid characters (spaces, commas, dots, hyphens)."
    return True, None

def start_analysis(address):
    """Send a request to start property analysis and return the task ID or error."""
    try:
        response = requests.post(
            f"{API_URL}/api/analyze",
            json={
                "address": address,
                "analysis_depth": "standard"
            },
            timeout=100
        )
        
        if response.status_code == 503:
            return None, "System is at capacity. Please try again in a few minutes."
        elif response.status_code == 200:
            data = response.json()
            return data.get('analysis_id'), None
        else:
            return None, f"Error starting analysis: {response.status_code} - {response.text}"
            
    except requests.exceptions.Timeout:
        return None, "Request timed out"
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to backend server"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def get_task_status(task_id):
    """Check the current status of a running analysis task from backend."""
    try:
        response = requests.get(f"{API_URL}/api/status/{task_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.warning(f"Status check failed: {response.status_code}")
            return None
    except requests.exceptions.Timeout:
        st.warning("Status check timed out")
        return None
    except requests.exceptions.ConnectionError:
        st.warning("Cannot connect to server for status check")
        return None
    except Exception as e:
        st.warning(f"Status check error: {str(e)}")
        return None

def extract_analysis_content(api_response):
    """Extract meaningful analysis text or structured content from API response."""
    if not isinstance(api_response, dict):
        return api_response
    
    try:
        if 'analysis' in api_response and isinstance(api_response['analysis'], str):
            return api_response['analysis']
        
        for key in ['llm_response', 'llm_analysis', 'content', 'result']:
            if key in api_response and isinstance(api_response[key], str):
                return api_response[key]
        
        return api_response
        
    except Exception as e:
        st.error(f"Error extracting analysis content: {e}")
        return api_response

def display_progress_with_status(task_id):
    """Continuously check backend for task status and update progress bar in UI."""
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    time_placeholder = st.empty()
    
    start_time = datetime.now()
    consecutive_failures = 0
    
    with progress_placeholder.container():
        st.progress(0)
    with status_placeholder.container():
        st.info("Starting analysis...")
    
    while True:
        current_time = datetime.now()
        elapsed = (current_time - start_time).seconds
        
        status = get_task_status(task_id)
        
        if status:
            consecutive_failures = 0  
            progress = status.get('progress', 0)
            current_step = status.get('current_step', 'Processing...')
            task_status = status.get('status', 'processing')
            
            with progress_placeholder.container():
                progress_val = max(0, min(100, progress))
                st.progress(progress_val / 100)
            
            with status_placeholder.container():
                st.info(f"**Progress:** {progress}% - {current_step}")
            
            with time_placeholder.container():
                st.caption(f"Elapsed time: {elapsed} seconds")
            
            if task_status == 'completed':
                with progress_placeholder.container():
                    st.progress(1.0)
                with status_placeholder.container():
                    st.success("Analysis completed successfully!")
                return status.get('result')
            
            elif task_status in ['failed', 'failed_zimas_search', 'error_zimas_search']:
                error = status.get('error', 'Unknown error')
                with status_placeholder.container():
                    if task_status == 'failed_zimas_search':
                        st.error("Address not found in ZIMAS")
                    elif task_status == 'error_zimas_search':
                        st.error("ZIMAS search error occurred")
                    else:
                        st.error(f"Analysis failed: {error}")
                return status.get('result')
            
        else:
            consecutive_failures += 1
            with status_placeholder.container():
                st.warning(f"Waiting for server response... (attempt {consecutive_failures})")
            with time_placeholder.container():
                st.caption(f"Elapsed time: {elapsed} seconds")
            
            if consecutive_failures > 10:
                with status_placeholder.container():
                    st.error("Lost connection to server - too many failed status checks")
                return None
        
        if elapsed > 600:
            with status_placeholder.container():
                st.error("Analysis timed out after 10 minutes")
            return None
        
        time.sleep(3)

def send_chat_message(message, analysis_context=None):
    """Send a chat message to the backend and get a response."""
    try:
        payload = {
            "message": message,
            "session_id": st.session_state.session_id
        }
        
        if analysis_context:
            payload["context"] = analysis_context
            payload["address"] = st.session_state.current_address
        
        response = requests.post(
            f"{API_URL}/api/chat",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('response', 'Sorry, I could not process your message.')
        else:
            return f"Error: {response.status_code} - {response.text}"
            
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "Cannot connect to backend server."
    except Exception as e:
        return f"Unexpected error: {str(e)}"

def display_chat_interface():
    """Display the chat interface for follow-up questions."""
    if not st.session_state.analysis_result:
        return  
    
    st.markdown("---")
    st.subheader("Ask Follow-up Questions")
    st.info(f"Ask questions about the analysis for: **{st.session_state.current_address}**")
    
    chat_input = st.text_input(
        "Ask a question about the property analysis:",
        placeholder="e.g., What are the main investment risks? Can you explain the zoning details?",
        key="chat_input"
    )
    
    send_chat = st.button("Send", type="primary", disabled=not chat_input.strip())
    
    if send_chat and chat_input.strip():
        with st.spinner("Getting response..."):
            analysis_content = extract_analysis_content(st.session_state.analysis_result)
            bot_response = send_chat_message(chat_input.strip(), analysis_content)
            
            st.markdown("### Response:")
            st.markdown(bot_response)


st.markdown("### Enter Property Address:")

col1, col2 = st.columns([1, 2])

with col1:
    house_number = st.text_input("House Number:", placeholder="1600", key="house_number")

with col2:
    street_name = st.text_input("Street Name:", placeholder="Vine", key="street_name")

if house_number.strip() and street_name.strip():
    valid, error_msg = validate_address(house_number.strip(), street_name.strip())
    if not valid:
        st.warning(error_msg)
else:
    valid = False

col1, col2 = st.columns([1, 3])
with col1:
    analyze_button = st.button("Analyze Property", type="primary", disabled=not valid)
with col2:
    st.empty()

if analyze_button:
    full_address = f"{house_number.strip()} {street_name.strip()}"
    st.session_state.current_address = full_address
    
    st.markdown("---")
    st.subheader(f"Analyzing: {full_address}")
    
    with st.spinner("Connecting to backend server..."):
        task_id, error = start_analysis(full_address)
    
    if task_id and not error:
        st.success(f"Analysis started successfully! Task ID: {task_id}")
        st.info("Showing real-time progress from backend...")
        
        result = display_progress_with_status(task_id)
        
        if result:
            result_status = result.get('status', '')
            
            if result_status == 'completed':
                st.balloons()
                st.session_state.analysis_result = result
                analysis_content = extract_analysis_content(result)
                
                st.markdown("---")
                st.markdown("## Analysis Results:")
                
                if isinstance(analysis_content, str):
                    st.markdown("### AI Analysis:")
                    st.markdown(analysis_content)
                else:
                    st.markdown("### Analysis Data:")
                    st.json(analysis_content)
                    
                with st.expander("Complete Backend Response"):
                    st.json(result)
                
                if isinstance(analysis_content, str):
                    st.download_button(
                        label="Download Analysis Report",
                        data=analysis_content,
                        file_name=f"analysis_{house_number}_{street_name.replace(' ', '_').replace(',', '')}.txt",
                        mime="text/plain"
                    )
        
            elif result_status == 'failed_zimas_search':
                st.markdown("---")
                st.error("Address Not Found")
                error_message = result.get('message', 'No data found in ZIMAS for this address.')
                st.warning(error_message)
                st.info("Please verify the address and try again.")
                
                with st.expander("Debug Information"):
                    st.json(result)
        
            elif result_status == 'error_zimas_search':
                st.markdown("---")
                st.error("ZIMAS Search Error")
                error_message = result.get('message', 'An error occurred during ZIMAS search.')
                st.warning(error_message)
                st.info("Please try again later.")
                
                with st.expander("Debug Information"):
                    st.json(result)
        
            else:
                st.markdown("---")
                st.error(f"Analysis failed with status: {result_status}")
                error_message = result.get('message', result.get('error', 'Unknown error occurred'))
                st.warning(error_message)
                
                with st.expander("Complete Backend Response"):
                    st.json(result)
        
        else:
            st.error("Analysis failed or timed out")
            
    else:
        st.error(f"Failed to start analysis: {error}")
        st.info("Please check if the backend server is running and accessible")

if st.session_state.analysis_result:
    display_chat_interface()

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### System Status:")
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            st.success("Backend server is running")
            if 'active_tasks' in health_data:
                st.metric("Active Tasks", health_data['active_tasks'])
        else:
            st.error(f"Backend server error: {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend server")
    except requests.exceptions.Timeout:
        st.error("Backend server timeout")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")

with col2:
    st.markdown("### Session Info:")
    st.caption(f"Session ID: {st.session_state.session_id[:8]}...")
    st.caption(f"Last check: {datetime.now().strftime('%H:%M:%S')}")
    if st.session_state.analysis_result:
        st.caption(f"Analysis available for: {st.session_state.current_address}")

with st.expander("Debug Information"):
    if st.button("Test Backend Connection"):
        with st.spinner("Testing connection..."):
            try:
                health_resp = requests.get(f"{API_URL}/health", timeout=5)
                st.success(f"Health check: {health_resp.status_code}")
                st.json(health_resp.json())
            except Exception as e:
                st.error(f"Connection test failed: {str(e)}")
    
    if st.button("Show Session State"):
        st.json({
            "session_id": st.session_state.session_id,
            "current_address": st.session_state.current_address,
            "has_analysis_result": st.session_state.analysis_result is not None
        })