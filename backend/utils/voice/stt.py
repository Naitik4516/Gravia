import speech_recognition as sr

# Initialize recognizer
recognizer = sr.Recognizer()

# Use the default microphone as source
with sr.Microphone() as source:
    print("Adjusting for background noise... Please wait.")
    recognizer.adjust_for_ambient_noise(source, duration=2)  # reduce noise
    print("Listening... Speak now!")

    # Capture the audio
    audio = recognizer.listen(source)

try:
    # Recognize speech using Google
    text = recognizer.recognize_google(audio)
    print("You said:", text)

except sr.UnknownValueError:
    print("Sorry, could not understand the audio.")
except sr.RequestError as e:
    print(f"Could not request results from Google Speech Recognition service; {e}")
