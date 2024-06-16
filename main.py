import openai
import speech_recognition as sr
import requests
import os
from dotenv import load_dotenv
from gtts import gTTS
import simpleaudio
import json
import io
import base64
import sys
from gtts import gTTS
from pydub import AudioSegment
import simpleaudio as sa

# .envファイルが読込
load_dotenv()

# 環境変数の確認
if not os.getenv("OPENAI_API_KEY") or not os.getenv("VOICEBOX_API_URL"):
    print("環境変数が設定されていません。.envファイルを確認してください。")
    exit(1)

# 音声の取り込み時間（秒）
PHRASE_TIME_LIMIT = 5

# 取り込む音声の言語
VOICE_LANGUAGE = "ja"

# 自然言語処理モデル
MODEL = "gpt-3.5-turbo"

# OpenAIのAPIにAPIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# Recognizerオブジェクト生成
recognizer = sr.Recognizer()

print("VOICEBOX_API_URL:", os.getenv("VOICEBOX_API_URL"))

def get_voice():
    with sr.Microphone() as source:
        print("音声取り込み中・・・")
        voice = recognizer.listen(source=source, phrase_time_limit=PHRASE_TIME_LIMIT)
    return voice

def transcribe_with_voicebox(voice_data, text, speaker):
    url = os.getenv("VOICEBOX_API_URL")
    if not url:
        print("VOICEBOX_API_URL is not set. Please set the environment variable correctly.")
        return ""
    
    voice_data_base64 = base64.b64encode(voice_data).decode('utf-8')
    audio_query_response = requests.post(
        url + "/audio_query/",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"voice_data": voice_data_base64}),
        params={"text": text, "speaker": speaker}
    )
    
    if audio_query_response.status_code != 200:
        print("Error in audio query:", audio_query_response.status_code, audio_query_response.text)
        return ""
    
    audio_query_data = audio_query_response.json()
    synthesis_response = requests.post(
        url + "/synthesis/",
        headers={"Content-Type": "application/json"},
        data=json.dumps(audio_query_data),
        params={"speaker": speaker}
    )
    
    if synthesis_response.status_code == 200:
        wav_obj = simpleaudio.WaveObject.from_wave_file(io.BytesIO(synthesis_response.content))
        wav_obj.play().wait_done()
        return synthesis_response.json().get('transcription', '')
    else:
        print("Error in synthesis:", synthesis_response.status_code, synthesis_response.text)
        return ""

def transcribe_voice(voice):
    try:
        voice_data = voice.get_wav_data()
        text = recognizer.recognize_google(voice, language=VOICE_LANGUAGE)
        if not text:
            print("音声認識に成功しましたが、テキストが空です。")
            return ""
        return text
    except Exception as e:
        print("音声を認識できませんでした。エラー内容: ", str(e))
        return ""

def get_chatgpt_answer(text):
    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": text}],
            temperature=0.5
        )
        if response and 'choices' in response and len(response['choices']) > 0:
            answer = response["choices"][0]["message"]["content"]
            print("ChatGPTからの応答: ", answer)
            return answer
        else:
            print("ChatGPTから適切な応答が得られませんでした。")
            return "応答を取得できませんでした。"
    except Exception as e:
        print("ChatGPT APIからの応答に失敗しました:", str(e))
        return "応答を取得できませんでした。"

def read_text(text):
    tts = gTTS(text=text, lang='ja')
    tts.save("output.mp3")
    
    # MP3をWAVに変換
    sound = AudioSegment.from_mp3("output.mp3")
    sound.export("output.wav", format="wav")
    
    # WAVファイルを再生
    wave_obj = sa.WaveObject.from_wave_file("output.wav")
    wave_obj.play().wait_done()

if __name__ == "__main__":
    try:
        while True:
            voice = get_voice()  # 音声を取得
            voice_text = transcribe_voice(voice)  # 音声をテキストに変換
            if voice_text:
                answer = get_chatgpt_answer(text=voice_text)  # テキストをChatGPTに送信し、回答を取得
                read_text(text=answer)  # 取得した回答を音声で出力
    except KeyboardInterrupt:
        print("プログラムを終了します。")
        sys.exit(0)