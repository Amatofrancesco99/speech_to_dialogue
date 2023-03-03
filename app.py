

import streamlit as st, datetime, langcodes, speech_recognition as sr, random, json, os
from dotenv import load_dotenv
from pydub import AudioSegment
from google.cloud import speech_v1 as speech
from google.cloud.speech_v1 import enums, types
from google.oauth2 import service_account

apptitle = 'Speech to Dialogue'
st.set_page_config(page_title=apptitle, page_icon='🦑')
st.title(apptitle + ' 🦑')

# Load environment variables from .env file
load_dotenv()

# Get the counter and last reset date
def get_password():
    admin_password = json.loads(os.getenv("PASSWORDS"))["admin"]
    return admin_password


# Define a helper function to check if the password is correct
def is_password_correct(entered_password):
    return entered_password == get_password()


# Function to get the sidebar content
def get_sidebar():
    with st.sidebar:
        st.subheader(":green[About]")
        st.write("The Speech to Dialogue web-app has been purposely created in order to :blue[build a dialogue starting from an audio track].\n"
                "You can copy the obtained dialogue, once the entire procedure has been concluded (our plan has a *maximum of 60 minutes of audio per month* that can be used, so some problem may occur if the users exeed this maximum).\n\n"
                "*Why you should use this service?*\nIs **simpler, and requires less configuration time with respect to all the other websites** you can find on the web that do the"
                " same. Please notice that the final obtained dialogue can contain some error, with respect to the original audio track.")
        st.subheader(":green[Author]")
        st.write("If you want to get further details on the author, you can have a look [here](https://amatofrancesco.altervista.org).\n\n"
                "Contact me or consider contributing to this repository with any suggestion or question.")


# Define a login page
def login():
    get_sidebar()
    st.subheader("Please enter the password to access the app")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if is_password_correct(password):
            session_state.is_authenticated = True


# Define the app content
def app():
    # Get the counter and last reset date
    def get_counter_env():
        # Load the counter and last reset date from the environment variables
        counter_data = json.loads(os.getenv("COUNTER"))
        counter = counter_data["counter"]
        last_reset = datetime.datetime.strptime(counter_data["last_reset"], "%Y-%m-%d").date()
        return counter, last_reset

    # Define a function to write the counter and last reset date to the file
    def write_counter_env(counter, last_reset):
        with open(".env", "w") as f:
            f.write(f"COUNTER={{'counter': {counter}, 'last_reset': '{last_reset}'}}\n")

    # Get the current date and time
    now = datetime.datetime.now()

    # If it's the first request of the month, reset the counter
    if now.date().month != get_counter_env()[1].month:
        counter = 0
        last_reset = now.date()
        write_counter_env(counter, last_reset)


    # Initialize the Recognizer object
    r = sr.Recognizer()

    # Create credentials object from the key file
    credentials_info = json.loads(os.getenv("CREDENTIALS"))
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    client = speech.SpeechClient(credentials=credentials)

    # Define a dictionary to store the people and their associated colors
    person_colors = {}

    # Define a list of available colors
    colors = ['red', 'blue', 'green']


    # Define a function to process the audio file and returns the dialogue
    def speech_to_dialogue(audio, language):
        # Get details of counter and last reset
        counter, last_reset = get_counter_env()
        # Increment the counter with the duration of the audio
        counter += audio.duration_seconds
        # If the counter exceeds 60 minutes, display an error message and exit the function
        if counter > 3600:
            st.error("Exceeded the maximum usage limit of 60 minutes for this month.")
            return False
        
        with sr.AudioFile(audio.export(format="wav")) as source:
            # Use file audio as input for speech recognition
            audio_text = r.record(source)

            # Convert audio to text using voice recognition service
            try:
                audio = types.RecognitionAudio(content=audio_text.get_raw_data())
                config = types.RecognitionConfig(
                    encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=audio_text.sample_rate,
                    language_code=language,
                )

                # Performs speech recognition on audio file
                response = client.recognize(config=config, audio=audio)

                # Extract text from response
                text = ""
                for result in response.results:
                    text += result.alternatives[0].transcript

                # Analyze text to identify dialogue between people
                dialogue = ""
                current_person = "Person 1"
                person_colors = {current_person: random.choice(colors)}
                current_color = person_colors[current_person]
                for sentence in text.split('.'):
                    # Skip over empty sentences
                    if not sentence.strip():
                        continue
                    # Switch to the next person
                    current_person = "Person {}".format(len(person_colors) + 1)
                    if current_person not in person_colors:
                        current_color = random.choice(colors)
                        person_colors[current_person] = current_color
                    # Add punctuation to the end of the sentence
                    if sentence[-1] not in {".", "?", "!"}:
                        sentence += "."
                    # Write out the sentence, along with the person's name and color
                    dialogue += f"**:{current_color}[{current_person}]** > {sentence.strip()}\n"
                    st.write(f"**:{current_color}[{current_person}]** > {sentence.strip()}\n")

                # Store the updated counter and last reset date in the file
                write_counter_env(counter, last_reset.strftime("%Y-%m-%d"))

            except Exception as e:
                st.exception(e)
                return False

        return True

    get_sidebar()

    audio = st.file_uploader("Select an audio track", type=['wav', 'mp3', 'flac', 'ogg', 'm4a', 'aac', 'aif', 'aiff', 'au', 'wma', 'mid', 'midi'])
    # List of allowed languages (can be expanded if needed)
    allowed_languages = ["English", "American", "Spanish", "Chinese", "Arabic", "Russian", "Portuguese", "French", "German", "Italian", "Japanese", "Korean", "Dutch", "Polish", "Swedish", "Turkish", "Indonesian", "Danish", "Norwegian", "Finnish", "Greek", "Thai", "Hebrew", "Hindi", "Czech", "Bengali", "Vietnamese"]
    language = st.selectbox('Spoken language', options=allowed_languages)

    if st.button(label="Build dialogue", type="primary"):
        # Convert audio to WAV format
        audio = AudioSegment.from_file(audio)
        status = speech_to_dialogue(audio, langcodes.find(language).language)
        if (status):
            st.success('Dialogue completed', icon="🦜")

# Create the Streamlit app and SessionState object
session_state = st.session_state
if "is_authenticated" not in session_state:
    session_state.is_authenticated = False

# Display the appropriate page based on authentication status
if not session_state.is_authenticated:
    login()
else:
    app()