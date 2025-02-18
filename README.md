@@ -1,281 +0,0 @@
# Yoto - Video İçerik Oluşturucu
Yoto, yapay zeka destekli otomatik video içeriği oluşturma aracıdır. Verilen bir konu hakkında:
- İçerik oluşturur (OpenAI GPT-4)
- Video araması yapar (Pexels API)
- Ses sentezler (OpenAI TTS)
- Videoları birleştirir (FFmpeg)
- Altyazı ekler
## 🚀 Özellikler
- 🎥 Pexels API ile ücretsiz otomatik video araması
- 🗣️ OpenAI TTS ile gerçekçi ses sentezi
- ✍️ GPT-4 ile içerik oluşturma
- 🎬 FFmpeg ile profesyonel video düzenleme
- 📝 Otomatik altyazı ekleme
- 🎨 Kullanıcı dostu GUI arayüzü
## 📋 Gereksinimler
- Python 3.8 veya üzeri
- FFmpeg
- NVIDIA GPU (isteğe bağlı, GPU hızlandırma için)
- OpenAI API anahtarı
- Pexels API anahtarı
## ⚙️ Kurulum
1. Repository'yi klonlayın:
```bash
git clone https://github.com/mehmeterendereli/yoto.git
cd yoto
```
2. Python sanal ortamı oluşturun ve aktif edin:
```bash
# Windows
python -m venv venv
venv\Scripts\activate
# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```
3. Gerekli Python paketlerini yükleyin:
```bash
pip install -r requirements.txt
```
4. FFmpeg'i yükleyin:
   - Windows: [FFmpeg İndirme Sayfası](https://ffmpeg.org/download.html#build-windows)'ndan indirin ve `bin` klasörüne çıkartın
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`
5. `.env.example` dosyasını `.env` olarak kopyalayın:
```bash
cp .env.example .env
```
6. `.env` dosyasını düzenleyin:
```ini
# API anahtarlarınızı ekleyin
OPENAI_API_KEY=your_openai_api_key
PEXELS_API_KEY=your_pexels_api_key
# FFmpeg yolunu ayarlayın (Windows için)
FFMPEG_PATH=bin/ffmpeg.exe  # veya tam yol: C:/ffmpeg/bin/ffmpeg.exe
```
## 🎮 Kullanım
1. GUI uygulamasını başlatın:
```bash
python gui.py
```
2. Konu başlığını girin (örn: "Kedilerin Davranışları")
3. "Başlat" butonuna tıklayın
4. Program otomatik olarak:
   - GPT-4 ile içerik oluşturacak
   - Pexels'ten uygun videolar arayacak
   - OpenAI TTS ile sesi sentezleyecek
   - FFmpeg ile final videoyu oluşturacak
5. İşlem bittiğinde video `output/{konu_adi}/video.mp4` konumunda olacak
## 📁 Proje Yapısı
```
yoto/
├── modules/               # Ana modüller
│   ├── content_generator.py  # İçerik oluşturma
│   ├── video_search_service.py  # Video arama
│   ├── tts_generator.py   # Ses sentezi
│   ├── video_editor.py    # Video düzenleme
│   └── ...
├── bin/                  # FFmpeg dizini
├── output/               # Çıktı dosyaları
├── gui.py               # GUI uygulaması
├── config.py            # Yapılandırma
└── requirements.txt     # Python bağımlılıkları
```
## 🔧 Sorun Giderme
1. FFmpeg Hataları:
   - FFmpeg'in doğru konumda olduğundan emin olun
   - `.env` dosyasındaki `FFMPEG_PATH` değerini kontrol edin
   - Windows'ta tam yolu deneyin: `C:/ffmpeg/bin/ffmpeg.exe`
2. API Hataları:
   - API anahtarlarının doğru olduğunu kontrol edin
   - OpenAI API'nin aktif olduğundan emin olun
   - Pexels API kotanızı kontrol edin
3. Video İndirme Hataları:
   - İnternet bağlantınızı kontrol edin
   - Pexels API'nin erişilebilir olduğundan emin olun
   - `output` dizininin yazılabilir olduğunu kontrol edin
## 📝 Lisans
Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.
## 🤝 Katkıda Bulunma
1. Fork'layın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit'leyin (`git commit -m 'feat: Add amazing feature'`)
4. Branch'i push'layın (`git push origin feature/amazing-feature`)
5. Pull Request açın
## 📞 İletişim
- GitHub Issues üzerinden soru sorabilir ve önerilerde bulunabilirsiniz
- Email: mehmeterendereli@gmail.com
---
# Yoto - AI Video Content Generator
Yoto is an AI-powered automatic video content creation tool. For a given topic, it:
- Generates content (OpenAI GPT-4)
- Searches for videos (Pexels API)
- Synthesizes speech (OpenAI TTS)
- Combines videos (FFmpeg)
- Adds subtitles
## 🚀 Features
- 🎥 Free automatic video search with Pexels API
- 🗣️ Realistic speech synthesis with OpenAI TTS
- ✍️ Content generation with GPT-4
- 🎬 Professional video editing with FFmpeg
- 📝 Automatic subtitle generation
- 🎨 User-friendly GUI interface
## 📋 Requirements
- Python 3.8 or higher
- FFmpeg
- NVIDIA GPU (optional, for GPU acceleration)
- OpenAI API key
- Pexels API key
## ⚙️ Installation
1. Clone the repository:
```bash
git clone https://github.com/mehmeterendereli/yoto.git
cd yoto
```
2. Create and activate Python virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate
# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```
3. Install required Python packages:
```bash
pip install -r requirements.txt
```
4. Install FFmpeg:
   - Windows: Download from [FFmpeg Download Page](https://ffmpeg.org/download.html#build-windows) and extract to `bin` folder
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`
5. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
6. Edit `.env` file:
```ini
# Add your API keys
OPENAI_API_KEY=your_openai_api_key
PEXELS_API_KEY=your_pexels_api_key
# Set FFmpeg path (for Windows)
FFMPEG_PATH=bin/ffmpeg.exe  # or full path: C:/ffmpeg/bin/ffmpeg.exe
```
## 🎮 Usage
1. Start the GUI application:
```bash
python gui.py
```
2. Enter a topic (e.g., "Cat Behavior")
3. Click "Start" button
4. The program will automatically:
   - Generate content with GPT-4
   - Search for suitable videos from Pexels
   - Synthesize speech with OpenAI TTS
   - Create final video with FFmpeg
5. When finished, the video will be at `output/{topic_name}/video.mp4`
## 📁 Project Structure
```
yoto/
├── modules/               # Core modules
│   ├── content_generator.py  # Content generation
│   ├── video_search_service.py  # Video search
│   ├── tts_generator.py   # Speech synthesis
│   ├── video_editor.py    # Video editing
│   └── ...
├── bin/                  # FFmpeg directory
├── output/               # Output files
├── gui.py               # GUI application
├── config.py            # Configuration
└── requirements.txt     # Python dependencies
```
## 🔧 Troubleshooting
1. FFmpeg Errors:
   - Ensure FFmpeg is in the correct location
   - Check `FFMPEG_PATH` value in `.env` file
   - Try full path on Windows: `C:/ffmpeg/bin/ffmpeg.exe`
2. API Errors:
   - Verify API keys are correct
   - Ensure OpenAI API is active
   - Check your Pexels API quota
3. Video Download Errors:
   - Check your internet connection
   - Ensure Pexels API is accessible
   - Verify `output` directory is writable
## 📝 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.
## 🤝 Contributing
1. Fork it
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
## 📞 Contact
- Feel free to ask questions and make suggestions through GitHub Issues
- Email: mehmeterendereli@gmail.com 
