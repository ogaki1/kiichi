from flask import Flask,render_template, request, redirect
from vimeo_downloader import Vimeo
import whisper
from yt_dlp import YoutubeDL
import os
import ffmpeg 

# 動画をダウンロードする
ydl_opts = {'format': 'bestaudio', 'outtmpl': 'CHATGPT'+'_.mp3'}
#format : 品質 best 映像のみ bestvideo 音声のみ bestaudio，outtmpl : 出力形式

app = Flask(__name__)

def Whisper():
    global model
    print('model load start')
    model = whisper.load_model("small") #tiny, base, small, medium, large  
    print('model load end')
    


@app.route('/')
def index():
    return render_template('./flask_api_index.html')

@app.route('/result_1',methods=['POST'])
def result_1():
    if request.files['file']:
        file = request.files['file']
        # ファイル保存
        savePath = file.filename
        file.save('CHATGPT_.mp3')
    # 実行
    result = model.transcribe("CHATGPT_.mp4",verbose=True,fp16=False)
    print(result["text"])

    os.remove('CHATGPT_.mp3')
    return render_template('./result.html', title='結果', result_text=result['text'])
    #return redirect('/')


@app.route('/result_2', methods=['POST'])
def result_2():
    if request.form['url']:
    #動画のURLを指定
        url = request.form['url']
        if 'youtu.be' in url:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        elif 'vimeo.com' in url:
            v = Vimeo(url)
            s = v.streams
            best_stream = s[-1]
            best_stream.download(filename='CHATGPT_.mp4')
        else:
            return redirect('/')


    # 実行
    result = model.transcribe('CHATGPT_.mp4',verbose=True,fp16=False)
    #print(result["text"])

    os.remove('CHATGPT_.mp4')
    return render_template('./result.html', title='結果', result_text=result['text'])


def main():
    app.debug = False
    Whisper()
    app.run(host='localhost', port=5000)

if __name__ == '__main__':
    main()
   