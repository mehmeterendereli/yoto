import os
import sys
import logging
from dotenv import load_dotenv
from typing import Dict, List, Union
from colorama import init, Fore, Style
import shutil
import platform

# Renkli konsol çıktısı için colorama'yı başlat
init()

# .env dosyasını yükle
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if not load_dotenv(dotenv_path):
    print_warning(f".env dosyası bulunamadı: {dotenv_path}")
    sys.exit(1)

# Logging yapılandırması
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'app.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def print_error(message: str) -> None:
    """Hata mesajını logla ve kırmızı renkte yazdır"""
    logger.error(message)
    print(f"{Fore.RED}Hata: {message}{Style.RESET_ALL}")

def print_warning(message: str) -> None:
    """Uyarı mesajını logla ve sarı renkte yazdır"""
    logger.warning(message)
    print(f"{Fore.YELLOW}Uyarı: {message}{Style.RESET_ALL}")

def print_success(message: str) -> None:
    """Başarı mesajını logla ve yeşil renkte yazdır"""
    logger.info(message)
    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")

def print_info(message: str):
    """Mavi renkli bilgi mesajı yazdır"""
    print(f"\033[94m[INFO] {message}\033[0m")

def validate_video_quality(quality: str) -> str:
    """Video kalitesi doğrulama"""
    valid_qualities = ["720p", "1080p", "1440p", "2160p"]
    quality = quality.lower()
    if quality not in valid_qualities:
        print_warning(f"Geçersiz video kalitesi. Varsayılan olarak 1080p kullanılacak.")
        return "1080p"
    return quality

def parse_int_env(key: str, default: int) -> int:
    """Integer çevre değişkeni parse etme"""
    try:
        value = os.getenv(key)
        if value is None:
            print_warning(f"{key} bulunamadı. Varsayılan değer ({default}) kullanılacak.")
            return default
        return int(value)
    except ValueError:
        print_warning(f"{key} bir tam sayı olmalıdır. Varsayılan değer ({default}) kullanılacak.")
        return default

# Kritik API anahtarlarını kontrol et
CRITICAL_VARS: Dict[str, str] = {
    "OPENAI_API_KEY": "OpenAI API anahtarı",
}

missing_critical = []
for var, description in CRITICAL_VARS.items():
    if not os.getenv(var):
        missing_critical.append(f"{description} ({var})")

if missing_critical:
    print_error("Aşağıdaki kritik değerler eksik:")
    for item in missing_critical:
        print(f"  - {item}")
    print("\nLütfen .env dosyasını kontrol edin ve eksik değerleri ekleyin.")
    print("Örnek .env dosyası için README.md dosyasına bakın.")
    sys.exit(1)

# API Anahtarları
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
YOUTUBE_CLIENT_SECRET_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Çıktı dizinleri
OUTPUT_DIR = os.getenv("VIDEO_OUTPUT_DIR", "output")
TEMP_DIR = os.getenv("TEMP_DIR", "temp")

# Video dizinlerini oluştur
for directory in [OUTPUT_DIR, TEMP_DIR]:
    try:
        os.makedirs(directory, exist_ok=True)
    except PermissionError:
        print_error(f"{directory} dizini oluşturulamıyor. Yetki hatası!")
        sys.exit(1)
    except Exception as e:
        print_error(f"Dizin oluşturma hatası: {str(e)}")
        sys.exit(1)

# Sayısal değerleri parse et
MAX_VIDEO_DURATION = parse_int_env("MAX_VIDEO_DURATION", 600)
VIDEO_QUALITY = validate_video_quality(os.getenv("VIDEO_QUALITY", "1080p"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "tr")

# DALL-E Ayarları
DALLE_SETTINGS = {
    "dall-e-2": {
        "sizes": ["256x256", "512x512", "1024x1024"],
        "quality": ["standard"],
        "max_images": 10
    },
    "dall-e-3": {
        "sizes": ["1024x1024", "1024x1792", "1792x1024"],
        "quality": ["standard", "hd"],
        "max_images": 1
    }
}

# Video Ayarları
DEFAULT_VIDEO_SETTINGS: Dict[str, Union[str, List[str], int]] = {
    "title_prefix": "AI Üretimi - ",
    "description_footer": "\n\nBu video yapay zeka tarafından oluşturulmuştur.",
    "default_tags": ["yapay zeka", "otomasyon", "teknoloji"],
    "category": "22",  # Eğitim kategorisi
    "privacy": "public",
    "video_quality": VIDEO_QUALITY,
    "video_preset": os.getenv("VIDEO_PRESET", "medium"),
    "video_crf": int(os.getenv("VIDEO_CRF", "23")),
    "max_duration": MAX_VIDEO_DURATION,
    "language": DEFAULT_LANGUAGE,
    "image_size": os.getenv("IMAGE_SIZE", "1024x1024"),
    "image_quality": os.getenv("IMAGE_QUALITY", "hd")
}

# Ayarları doğrula
if MAX_VIDEO_DURATION <= 0:
    print_warning("Video süresi 0'dan büyük olmalıdır. Varsayılan değer (600) kullanılacak.")
    MAX_VIDEO_DURATION = 600
elif MAX_VIDEO_DURATION > 3600:
    print_warning("Video süresi 3600 saniyeden fazla olamaz. Maksimum değer (3600) kullanılacak.")
    MAX_VIDEO_DURATION = 3600

if DEFAULT_LANGUAGE not in ["tr", "en"]:
    print_warning("Geçersiz dil seçeneği. Varsayılan olarak 'tr' kullanılacak.")
    DEFAULT_LANGUAGE = "tr"

def get_ffmpeg_path() -> str:
    """FFmpeg yolunu dinamik olarak tespit et"""
    # Önce proje içindeki bin klasörüne bak
    bin_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe")
    if os.path.exists(bin_ffmpeg):
        print_success(f"FFmpeg bulundu: {bin_ffmpeg}")
        return bin_ffmpeg
        
    # Sonra PATH'te ara
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        print_success(f"FFmpeg PATH'te bulundu: {ffmpeg_path}")
        return ffmpeg_path
        
    # Windows için yaygın konumları kontrol et
    if platform.system() == "Windows":
        common_paths = [
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            r"C:\Windows\System32\ffmpeg.exe"
        ]
        for path in common_paths:
            if os.path.exists(path):
                print_success(f"FFmpeg sistem yolunda bulundu: {path}")
                return path
                
    # Linux/Mac için yaygın konumları kontrol et
    else:
        common_paths = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg"
        ]
        for path in common_paths:
            if os.path.exists(path):
                print_success(f"FFmpeg sistem yolunda bulundu: {path}")
                return path
    
    print_error("FFmpeg bulunamadı! Lütfen FFmpeg'i yükleyin veya bin klasörüne kopyalayın.")
    return None

# FFmpeg yolunu al
FFMPEG_PATH = get_ffmpeg_path()
if not FFMPEG_PATH:
    print_error("FFmpeg bulunamadı! Video işleme özellikleri çalışmayacak.")
