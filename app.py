import streamlit as st, datetime, langcodes, speech_recognition as sr, random, json
from pydub import AudioSegment
from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech_v1p1beta1 import enums, types
from google.oauth2 import service_account

apptitle = 'Speech to Dialogue'
st.set_page_config(page_title=apptitle, page_icon='🦑')
st.title(apptitle + ' 🦑')

CREDENTIAL_PATH = "utils/credentials.json"
COUNTER_PATH = "utils/counter.json"
PASSWORDS_PATH = "utils/passwords.json"

# Get the counter and last reset date
def get_password():
    with open(PASSWORDS_PATH, "r") as f:
                data = json.load(f)
    return data["Admin"]


# Define a helper function to check if the password is correct
def is_password_correct(entered_password):
    return entered_password == get_password()


# Function to get the sidebar content
def get_sidebar():
    with st.sidebar:
        st.subheader(":green[About]")
        st.write("The Speech to Dialogue web-app has been purposely created in order to :blue[build a dialogue starting from an audio track].\n"
                "You can copy the obtained dialogue, once the entire procedure has been concluded (free plan has a *maximum of 60 minutes of audio" 
                " per month* that can be used, issues may occur if the user exeeds this maximum).\n\n"
                "*Why you should use this service?*\nIt is **user friendly and free**, but requires a small configuration time (entire configuration"
                " procedure description [here](https://www.github.com/Amatofrancesco99/speech_to_dialogue)). "
                "Please notice that the final obtained dialogue can contain some error, with respect to the original audio track.")
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
    get_sidebar()
    
    # Define a function to read the counter and last reset date from the file
    def read_counter_file():
        try:
            with open(COUNTER_PATH, "r") as f:
                data = json.load(f)
        except:
            data = {"counter": 0, "last_reset": now.strftime("%Y-%m-%d")}
        return data

    # Define a function to write the counter and last reset date to the file
    def write_counter_file(counter, last_reset):
        data = {"counter": counter, "last_reset": last_reset}
        with open(COUNTER_PATH, "w") as f:
            json.dump(data, f)

    # Read the counter and last reset date from the file
    counter_data = read_counter_file()
    counter = counter_data["counter"]
    last_reset = datetime.datetime.strptime(counter_data["last_reset"], "%Y-%m-%d").date()

    # Get the current date and time
    now = datetime.datetime.now()

    # If it's the first request of the month, reset the counter
    if now.date().month != last_reset.month:
        counter = 0
        last_reset = now.date()
        write_counter_file(counter, last_reset)

    # Initialize the Recognizer object
    r = sr.Recognizer()

    # Create credentials object from the key file
    with open(CREDENTIAL_PATH) as f:
        credentials_dict = json.load(f)
    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    client = speech.SpeechClient(credentials=credentials)

    # Define a list of available colors
    colors = ['red', 'blue', 'green']


    # Define a function to process the audio file and returns the dialogue
    def speech_to_dialogue(audio, language, num_speakers):
        # Get details of counter and last reset
        counter_data = read_counter_file()
        counter = counter_data["counter"]
        last_reset = datetime.datetime.strptime(counter_data["last_reset"], "%Y-%m-%d").date()
        # Increment the counter with the duration of the audio
        counter += audio.duration_seconds
        # If the counter exceeds 60 minutes, display an error message and exit the function
        if counter > 3600:
            st.error("Exceeded the maximum usage limit of 60 minutes for this month.")
            return False

        with sr.AudioFile(audio.export(format="wav")) as source:
            try:
                # Use file audio as input for speech recognition
                audio_text = r.record(source)
                audio = types.RecognitionAudio(content=audio_text.get_raw_data())

                config = {
                    "encoding": enums.RecognitionConfig.AudioEncoding.LINEAR16,
                    "sample_rate_hertz": audio_text.sample_rate,
                    "language_code": language,
                    "enable_speaker_diarization": True,
                    "diarization_speaker_count": num_speakers,
                    "use_enhanced": True,
                }

                # Performs speech recognition on audio file
                response = client.recognize(config=config, audio=audio)
                # Keep track of the sentences for each speaker
                speaker_sentences = {}
                for result in response.results:
                    # Get the speaker tag for the current result
                    speaker_tag = result.alternatives[0].words[-1].speaker_tag
                    # Skip duplicates and empty transcripts
                    if speaker_tag in speaker_sentences or not result.alternatives[0].transcript.strip():
                        continue
                    # Get the transcript for the current result
                    transcript = result.alternatives[0].transcript.strip()
                    # Add punctuation to the end of the transcript if needed
                    if transcript and transcript[-1] not in {".", "?", "!"}:
                        transcript += "."
                    # Get the start time of the current result as a timedelta object
                    start_time = datetime.timedelta(seconds=result.alternatives[0].words[0].start_time.seconds)
                    # Store the sentence in the speaker_sentences dictionary
                    speaker_sentences[speaker_tag] = (start_time, transcript)

                # Sort the sentences for each speaker by timestamp
                for speaker_tag in sorted(speaker_sentences.keys()):
                    current_color = random.choice(colors)
                    # Write out the transcript, along with the speaker's name and color
                    st.write(f"**:{current_color}[Person {speaker_tag + 1}]** > {speaker_sentences[speaker_tag][1]}")

                # Store the updated counter and last reset date in the file
                write_counter_file(counter, last_reset.strftime("%Y-%m-%d"))

            except Exception as e:
                st.exception(e)
                return False

        return True


    audio = st.file_uploader("Select an audio track", type=['wav', 'mp3', 'flac', 'ogg', 'm4a', 'aac', 'aif', 'aiff', 'au', 'wma', 'mid', 'midi'])
    # List of allowed languages (can be expanded if needed)
    allowed_languages = ["English", "American", "Spanish", "Chinese", "Arabic", "Russian", "Portuguese", "French", "German", "Italian", "Japanese", "Korean", "Dutch", "Polish", "Swedish", "Turkish", "Indonesian", "Danish", "Norwegian", "Finnish", "Greek", "Thai", "Hebrew", "Hindi", "Czech", "Bengali", "Vietnamese"]
    language = st.selectbox('Spoken language', options=allowed_languages)
    people = st.number_input('Number of people involved', value=1, min_value=1)

    if st.button(label="Build dialogue", type="primary"):
        # Convert audio to WAV format
        audio = AudioSegment.from_file(audio)
        status = speech_to_dialogue(audio, langcodes.find(language).language, people)
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