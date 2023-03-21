from flask import Flask,render_template, request, redirect, url_for
from vimeo_downloader import Vimeo
import whisper
from yt_dlp import YoutubeDL
import os
import ffmpeg 

# 動画をダウンロードする
ydl_opts = {'format': 'bestaudio', 'outtmpl': './input/' + 'CHATGPT'+'_.mp4'}
#format : 品質 best 映像のみ bestvideo 音声のみ bestaudio，outtmpl : 出力形式

#def Whisper():
global model
print('model load start')
model = whisper.load_model('tiny') #tiny, base, small, medium, large  
print('model load end')

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('./flask_api_index.html')

@app.route('/result_1',methods=['POST'])
def result_1():
    if request.files['file']:
        file = request.files['file']
        # ファイル保存
        savePath = file.filename
        file.save('./input/CHATGPT_.mp4')
    else :
        return redirect('/')
    # 実行
    result = model.transcribe('./input/CHATGPT_.mp4',verbose=True,fp16=False)
    print(result['text'])

    os.remove('./input/CHATGPT_.mp4')
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
            if len(s) == 0:
                return redirect(url_for('index'))
            best_stream = s[-1]
            best_stream.download(download_directory='./input/',filename='CHATGPT_.mp4')
        else:
            return redirect(url_for('index'))

    # 実行
    result = model.transcribe('./input/CHATGPT_.mp4',verbose=True,fp16=False)
    #print(result["text"])

    os.remove('./input/CHATGPT_.mp4')
    return render_template('./result.html', title='結果', result_text=result['text'])


def main():
    app.debug = False
    Whisper()
    app.run(host='0.0.0.0',port=80)

if __name__ == '__main__':
    main()
   
