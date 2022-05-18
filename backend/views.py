from flask import Blueprint, jsonify, request
from . import db
from .models import Podcast
import os 
import speech_recognition as sr 
import requests
import librosa
from pydub import AudioSegment
from pydub.silence import split_on_silence

main = Blueprint("main", __name__)

@main.route("/transcript_podcast", methods=["POST"])
def transcript_podcast():
    db.create_all()
    podcast_data = request.get_json()
    episodeUrl=podcast_data["url"]
    new_podcast = Podcast(url=episodeUrl, transcript=transcribe_from_url(episodeUrl))
    db.session.add(new_podcast)
    db.session.commit()
    return "Done", 201

@main.route("/podcasts")
def podcasts():
    podcasts_list = Podcast.query.all()
    podcasts = []
    for podcast in podcasts_list:
        podcasts.append({"url": podcast.url, "transcript": podcast.transcript})
    return jsonify({"podcasts": podcasts})

r = sr.Recognizer()

def transcribe_from_url(url):

    # download podcast
    downloaded_obj = requests.get(url)
    with open("podcast.mp3", "wb") as file:
        file.write(downloaded_obj.content)
    AudioSegment.from_mp3("podcast.mp3").export("podcast.wav", format="wav") # converts mp3 to wav
 
    transcript = ""
    startTime = 0.000
    sound = AudioSegment.from_wav("podcast.wav") 
    chunks = split_on_silence(sound,
        min_silence_len = 500, 
        silence_thresh = sound.dBFS-14,
        keep_silence=500,
    )

    folder_name = "backend/audio-chunks"

    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)

    for i, audio_chunk in enumerate(chunks, start=1):
        chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
        audio_chunk.export(chunk_filename, format="wav")
        
        with sr.AudioFile(chunk_filename) as source:
            audio_listened = r.record(source)
            try:
                sentence = r.recognize_google(audio_listened)
            except sr.UnknownValueError as e:
                print("Error:", str(e))
            else:
                sentence = f"{sentence.capitalize()}. "
                duration =  librosa.get_duration(filename=chunk_filename)
                endTime = startTime + duration
                transcript += "startTime: " + str(startTime) + "; endTime: " + str(endTime) + "; sentence: " + sentence
                startTime += duration
    
    # cleanup
    os.remove("podcast.mp3") 
    os.remove("podcast.wav") 
    
    return transcript