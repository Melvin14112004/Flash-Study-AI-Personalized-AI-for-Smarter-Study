import os
import requests
from tqdm import tqdm
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification
)
from sentence_transformers import SentenceTransformer

os.makedirs("local_models", exist_ok=True)

def save_transformer_model(model_name, model_class):
    print(f"🔄 Downloading {model_name} ...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = model_class.from_pretrained(model_name)
        path = f"local_models/{model_name.split('/')[-1]}"
        tokenizer.save_pretrained(path)
        model.save_pretrained(path)
        print(f"✅ Saved {model_name}\n")
    except Exception as e:
        print(f"❌ Failed to download {model_name}: {e}\n")

def save_sentence_transformer(model_name):
    print(f"🔄 Downloading {model_name} ...")
    try:
        model = SentenceTransformer(model_name)
        path = f"local_models/{model_name.split('/')[-1]}"
        model.save(path)
        print(f"✅ Saved {model_name}\n")
    except Exception as e:
        print(f"❌ Failed to download {model_name}: {e}\n")

def save_cross_encoder(model_name):
    print(f"🔄 Downloading {model_name} ...")
    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder(model_name)
        path = f"local_models/{model_name.split('/')[-1]}"
        model.save(path)
        print(f"✅ Saved {model_name}\n")
    except Exception as e:
        print(f"❌ Failed to download {model_name}: {e}\n")

def save_whisper_model(model_name="tiny"):
    print(f"🔄 Downloading Whisper ({model_name}) ...")
    try:
        import whisper
        model = whisper.load_model(model_name)
        model_dir = f"local_models/openai-whisper-{model_name}"
        os.makedirs(model_dir, exist_ok=True)
        print(f"✅ Whisper model ready in {model_dir}\n")
    except Exception as e:
        print(f"❌ Failed to download Whisper model: {e}\n")

# ========== RESUMABLE DOWNLOAD HELPER ==========
def download_with_resume(url, output_path):
    headers = {}
    if os.path.exists(output_path):
        downloaded_bytes = os.path.getsize(output_path)
        headers['Range'] = f'bytes={downloaded_bytes}-'
        print(f"⏸️ Resuming download from {downloaded_bytes / (1024*1024):.2f} MB...")
    else:
        downloaded_bytes = 0
        print("⬇️ Starting new download...")

    response = requests.get(url, headers=headers, stream=True)
    total_size = int(response.headers.get('content-length', 0)) + downloaded_bytes

    with open(output_path, 'ab') as f:
        for data in tqdm(response.iter_content(chunk_size=8192),
                         total=total_size // 8192,
                         unit='KB', initial=downloaded_bytes // 8192):
            f.write(data)

    print(f"✅ Download completed: {output_path}")

# ========== ESPnet MODEL FIXED WITH RESUME ==========
def save_espnet_model():
    print("🔄 Downloading ESPnet TTS model (kan-bayashi/ljspeech_vits) ...")
    try:
        url = "https://zenodo.org/record/5443814/files/tts_train_vits_raw_phn_tacotron_g2p_en_no_space_train.total_count.ave.zip?download=1"
        cache_dir = os.path.expanduser("~/.cache/espnet")
        os.makedirs(cache_dir, exist_ok=True)
        output_file = os.path.join(cache_dir, "kan-bayashi_ljspeech_vits.zip")

        download_with_resume(url, output_file)
        print(f"✅ ESPnet TTS model saved at {output_file}")
    except Exception as e:
        print(f"❌ Failed to download ESPnet model: {e}\n")

# -------------------------------
# 🧠 MODEL DOWNLOADS START HERE
# -------------------------------
save_transformer_model("t5-small", AutoModelForSeq2SeqLM)
save_transformer_model("iarfmoose/t5-base-question-generator", AutoModelForSeq2SeqLM)
save_transformer_model("distilbert-base-uncased", AutoModelForSequenceClassification)
save_sentence_transformer("sentence-transformers/all-MiniLM-L6-v2")
save_transformer_model("ml6team/keyphrase-extraction-distilbert-inspec", AutoModelForTokenClassification)
save_transformer_model("facebook/bart-large-mnli", AutoModelForSeq2SeqLM)
save_transformer_model("j-hartmann/emotion-english-distilroberta-base", AutoModelForSequenceClassification)
save_espnet_model()
save_whisper_model("tiny")
save_cross_encoder("cross-encoder/stsb-roberta-base")

print("🎯 All models have been downloaded and saved in /local_models")
