import os
import json
import requests
import streamlit as st
import tempfile
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
import base64
from gtts import gTTS
import io

# Load environment variables
load_dotenv()

# Get API key from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# API URL
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# Initialize session states
if 'gemini_response' not in st.session_state:
    st.session_state.gemini_response = ""
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = ""
if 'quiz_content' not in st.session_state:
    st.session_state.quiz_content = ""
if 'play_response_audio' not in st.session_state:
    st.session_state.play_response_audio = False
if 'play_quiz_audio' not in st.session_state:
    st.session_state.play_quiz_audio = False
if 'play_custom_audio' not in st.session_state:
    st.session_state.play_custom_audio = False
if 'custom_text' not in st.session_state:
    st.session_state.custom_text = ""

# Function to handle API requests with error handling
def make_api_request(url, headers, data):
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.ConnectionError as e:
        st.error(f"Connection error: {str(e)}")
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again later.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Request error: {str(e)}")
        return None
    except json.JSONDecodeError:
        st.error("Error parsing response from API.")
        return None

# Function to call Gemini API
def get_gemini_response(prompt):
    if not GEMINI_API_KEY:
        return "Error: Gemini API key not found in environment variables."
    
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    response_data = make_api_request(GEMINI_API_URL, headers, data)
    if response_data:
        try:
            return response_data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return "Error: Unexpected response format from Gemini API."
    return "Failed to get response from Gemini API."

# Function to extract text from PDFs
def extract_text_from_pdf(pdf_file):
    try:
        text = ""
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return ""

# Function to extract content from a webpage
def extract_text_from_webpage(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return ' '.join([p.text for p in soup.find_all('p')])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching webpage: {str(e)}")
        return ""

# Function to generate quiz questions
def generate_quiz(text):
    prompt = f"Generate 5 multiple-choice questions from the following text:\n{text}"
    return get_gemini_response(prompt)

# Function to convert text to speech using gTTS (Google Text-to-Speech)
def text_to_speech(text, lang='en'):
    if not text or len(text.strip()) == 0:
        st.warning("No text to convert to speech.")
        return None
    
    try:
        # Print for debugging (you can remove this later)
        print(f"Converting to speech: {text[:100]}... (length: {len(text)})")
        
        tts = gTTS(text=text, lang=lang, slow=False)
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        return audio_bytes
    except Exception as e:
        st.error(f"Error generating speech: {str(e)}")
        # More details for debugging
        print(f"Full error: {repr(e)}")
        return None

# Callback functions for buttons

# Callback functions for buttons
def on_get_answer_click():
    user_input = st.session_state.user_input
    if user_input:
        with st.spinner("Fetching response..."):
            # Include extracted text from PDF in the prompt
            if st.session_state.extracted_text:
                context_prompt = f"Based on the following content:\n\n{st.session_state.extracted_text}\n\nUser question: {user_input}"
                st.session_state.gemini_response = get_gemini_response(context_prompt)
            else:
                # If no PDF is uploaded, just use the user's question
                st.session_state.gemini_response = get_gemini_response(user_input)


def on_listen_response_click():
    st.session_state.play_response_audio = True

def on_generate_quiz_click():
    if st.session_state.extracted_text:
        with st.spinner("Generating quiz..."):
            st.session_state.quiz_content = generate_quiz(st.session_state.extracted_text)

def on_listen_quiz_click():
    st.session_state.play_quiz_audio = True

def on_speak_custom_text_click():
    st.session_state.custom_text = st.session_state.tts_text
    st.session_state.play_custom_audio = True

# Streamlit UI
st.title("📚 Student Assistant Chatbot")

# Sidebar
st.sidebar.header("Upload Documents")
uploaded_files = st.sidebar.file_uploader("Upload PDF", type=["pdf"], accept_multiple_files=True)
webpage_url = st.sidebar.text_input("Enter webpage URL")

# Add language selection for TTS
st.sidebar.header("Text-to-Speech Settings")
tts_language = st.sidebar.selectbox(
    "Select Language",
    options=[
        "English", "Spanish", "French", "German", 
        "Italian", "Portuguese", "Hindi", "Chinese"
    ]
)

# Language code mapping
language_codes = {
    "English": "en", "Spanish": "es", "French": "fr", 
    "German": "de", "Italian": "it", "Portuguese": "pt",
    "Hindi": "hi", "Chinese": "zh-CN"
}

# Process uploaded files
if uploaded_files:
    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(uploaded_file.read())
            temp_file_path = temp_file.name
        
        extracted_text = extract_text_from_pdf(temp_file_path)
        st.session_state.extracted_text = extracted_text
        st.text_area("Extracted Text", extracted_text, height=200)
        
        # Clean up temp file
        try:
            os.unlink(temp_file_path)
        except:
            pass

# Process webpage URL
if webpage_url and st.sidebar.button("Extract Text from URL"):
    extracted_text = extract_text_from_webpage(webpage_url)
    st.session_state.extracted_text = extracted_text
    st.text_area("Extracted Webpage Content", extracted_text, height=200)

# Chatbot Input
st.text_input("Ask something:", key="user_input")
st.button("Get Answer", on_click=on_get_answer_click)

# Display Gemini response and TTS button
# Replace your current response audio section with this code
if st.session_state.gemini_response:
    st.subheader("Gemini Response:")
    st.write(st.session_state.gemini_response)
    
    col1, col2 = st.columns([1, 5])  # Create columns for better layout
    with col1:
        listen_button = st.button("🔊 Listen", key="listen_response_button", on_click=on_listen_response_click)
    
    # Play audio if requested
    if st.session_state.play_response_audio:
        lang_code = language_codes.get(tts_language, "en")
        with st.spinner("Generating audio..."):
            response_text = st.session_state.gemini_response
            # Limit text length if needed
            if len(response_text) > 5000:  # gTTS has limitations
                response_text = response_text[:5000] + "..."
            audio_bytes = text_to_speech(response_text, lang=lang_code)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")
            else:
                st.error("Failed to generate audio. Text may be too long or contain unsupported characters.")
        st.session_state.play_response_audio = False  # Reset the state

# Quiz Generator
st.button("Generate Quiz from Extracted Text", on_click=on_generate_quiz_click)

# Display quiz and TTS button
if st.session_state.quiz_content:
    st.subheader("Generated Quiz:")
    st.write(st.session_state.quiz_content)
    
    # Add text-to-speech button for quiz
    st.button("🔊 Listen to Quiz", on_click=on_listen_quiz_click)
    
    # Play audio if requested
    if st.session_state.play_quiz_audio:
        lang_code = language_codes.get(tts_language, "en")
        with st.spinner("Generating audio..."):
            audio_bytes = text_to_speech(st.session_state.quiz_content, lang=lang_code)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")
        st.session_state.play_quiz_audio = False

# Simple Text-to-Speech input for any other text
st.subheader("Custom Text-to-Speech")
st.text_area("Enter any text to convert to speech:", height=100, key="tts_text")
st.button("🔊 Speak Text", on_click=on_speak_custom_text_click)

# Play custom text audio if requested
if st.session_state.play_custom_audio and st.session_state.custom_text:
    lang_code = language_codes.get(tts_language, "en")
    with st.spinner("Converting text to speech..."):
        audio_bytes = text_to_speech(st.session_state.custom_text, lang=lang_code)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")
    st.session_state.play_custom_audio = False