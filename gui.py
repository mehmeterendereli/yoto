import sys
import os
import json
import vlc
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QMessageBox, QProgressBar, QMainWindow, QFrame,
    QSizePolicy, QTabWidget, QScrollArea, QSpacerItem,
    QSlider, QStyle, QComboBox, QPlainTextEdit,
    QGroupBox, QRadioButton, QGridLayout, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QClipboard

from modules.content_generator import generate_youtube_content
from modules.tts_generator import generate_tts
from modules.video_search_service import VideoSearchService
from modules.video_editor import create_video
from config import print_error, print_success, print_warning

class VideoWorker(QThread):
    """Video oluşturma işlemlerini arka planda yürüten worker sınıfı"""
    progress = pyqtSignal(int)
    log = pyqtSignal(str, str)
    finished = pyqtSignal(bool, str, dict)
    
    def __init__(self, topic: str, duration_seconds: int = 60, voice: str = "onyx", speed: float = 1.0, aspect_ratio: str = "16:9", quality: str = "1080p", video_style: dict = None, content_settings: dict = None,
                 content_language: str = "tr", subtitle_enabled: bool = True, subtitle_language: str = "tr"):
        super().__init__()
        self.topic = topic
        self.duration_seconds = duration_seconds
        self.voice = voice
        self.speed = speed
        self.aspect_ratio = aspect_ratio
        self.quality = quality
        self.project_dir = None
        self.video_service = VideoSearchService()
        self.video_style = video_style
        self.content_settings = content_settings
        self.content_language = content_language
        self.subtitle_enabled = subtitle_enabled
        self.subtitle_language = subtitle_language
        
    def update_progress(self, value: int):
        """İlerleme çubuğunu güncelle"""
        self.progress.emit(value)
        
    def create_project_folder(self) -> str:
        """Proje klasörünü oluştur"""
        folder_name = '_'.join(self.topic.split()[:2])
        folder_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in folder_name)
        folder_path = os.path.join("output", folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path
        
    def run(self):
        try:
            self.project_dir = self.create_project_folder()
            metadata = {
                "title": self.topic,
                "duration": self.duration_seconds,
                "voice": self.voice,
                "speed": self.speed,
                "aspect_ratio": self.aspect_ratio,
                "quality": self.quality,
                "folder_name": os.path.basename(self.project_dir),
                "video_style": self.video_style,
                "content_settings": self.content_settings,
                "content_language": self.content_language,
                "subtitle_enabled": self.subtitle_enabled,
                "subtitle_language": self.subtitle_language
            }
            
            # 1. OpenAI ile içerik üret (20%)
            self.log.emit(f"🚀 [{self.duration_seconds} saniye - Dil: {self.content_language.upper()} - Altyazı: {self.subtitle_language.upper()}] İçerik oluşturuluyor...", "info")
            content = generate_youtube_content(
                topic=self.topic,
                duration_seconds=self.duration_seconds,
                content_language=self.content_language,
                subtitle_language=self.subtitle_language
            )
            if not content:
                raise Exception("İçerik oluşturulamadı")
            self.update_progress(20)
            
            # İçeriği kaydet ve altyazıyı güncelle
            content_file = os.path.join(self.project_dir, "content.json")
            with open(content_file, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            metadata.update(content)
            
            # Altyazı metnini güncelle
            self.video_style["subtitle"]["text"] = content["subtitle_text"]
            
            # 2. Pexels'ten videolar (70%)
            self.log.emit(f"🎥 [{self.duration_seconds} saniye] Videolar aranıyor...", "info")
            videos_dir = os.path.join(self.project_dir, "videos")
            os.makedirs(videos_dir, exist_ok=True)
            
            video_files = []
            total_duration = 0
            video_index = 1
            min_scene_duration = self.content_settings.get("min_scene_duration", 5)
            
            # Her sahne için video ara ve indir
            for scene in content["pexels_prompts"]:
                if len(video_files) >= 6:  # En fazla 6 video
                    break
                    
                scene_duration = min(int(scene["duration"]), self.duration_seconds - total_duration)
                if scene_duration <= 0:
                    break
                    
                self.log.emit(f"🔍 Video aranıyor ({video_index}. sahne): {scene['description']}", "info")
                
                # Ana arama terimleri
                search_terms = [
                    scene['query'],  # Ana arama terimi
                    self.topic,  # Yedek olarak konuyu da dene
                    scene['description']  # Son çare olarak açıklamayı dene
                ]
                
                video_found = False
                for term in search_terms:
                    if video_found:
                        break
                        
                    self.log.emit(f"🔍 Arama terimi: {term}", "info")
                    videos = self.video_service.search_videos(
                        query=term,
                        min_duration=min_scene_duration,
                        max_duration=scene_duration + 5
                    )
                    
                    if videos:
                        for video in videos:
                            video_file = os.path.join(videos_dir, f"video_{video_index}.mp4")
                            if self.video_service.download_video(video, video_file):
                                video_files.append(video_file)
                                total_duration += video['duration']
                                video_index += 1
                                video_found = True
                                
                                # Video bilgilerini metadata'ya ekle
                                if 'videos' not in metadata:
                                    metadata['videos'] = []
                                metadata['videos'].append({
                                    'scene': scene['description'],
                                    'query': term,
                                    'duration': video['duration']
                                })
                                break
                
                if not video_found:
                    self.log.emit(f"⚠️ Video bulunamadı: {scene['description']}", "warning")
                    
                self.update_progress(20 + (50 * len(video_files) // len(content["pexels_prompts"])))
                
            # En az 2 video kontrolü
            if len(video_files) < 2:
                # Yedek arama terimleri ile tekrar dene
                backup_terms = [
                    self.topic,  # Ana konu
                    content["seo"]["title"],  # Video başlığı
                    content["pexels_prompts"][0]["query"]  # İlk sahnenin sorgusu
                ]
                
                for term in backup_terms:
                    if len(video_files) >= 2:
                        break
                        
                    self.log.emit(f"🔍 Yedek arama: {term}", "info")
                    videos = self.video_service.search_videos(
                        query=term,
                        min_duration=5,
                        max_duration=15
                    )
                    
                    if videos:
                        for video in videos[:2]:  # En fazla 2 video daha ekle
                            video_file = os.path.join(videos_dir, f"video_{video_index}.mp4")
                            if self.video_service.download_video(video, video_file):
                                video_files.append(video_file)
                                total_duration += video['duration']
                                video_index += 1
                                
                                # Video bilgilerini metadata'ya ekle
                                if 'videos' not in metadata:
                                    metadata['videos'] = []
                                metadata['videos'].append({
                                    'scene': 'Yedek video',
                                    'query': term,
                                    'duration': video['duration']
                                })
            
            if len(video_files) < 2:
                raise Exception(f"Yeterli video bulunamadı! Bulunan video sayısı: {len(video_files)}")
            
            self.log.emit(f"✅ Toplam {len(video_files)} video indirildi", "success")
            
            # 3. TTS ile seslendirme (90%)
            self.log.emit(f"🎤 [{self.duration_seconds} saniye - Ses: {self.voice} - Hız: {self.speed}x] Seslendirme oluşturuluyor...", "info")
            audio_file = os.path.join(self.project_dir, "audio.mp3")
            if not generate_tts(content["tts_text"], audio_file, self.voice, self.speed):
                raise Exception("Seslendirme oluşturulamadı")
            self.update_progress(90)
            
            # 4. Video montaj (100%)
            self.log.emit(f"🎬 [{self.duration_seconds} saniye] Final video oluşturuluyor...", "info")
            video_file = os.path.join(self.project_dir, "video.mp4")
            if not create_video(video_files, audio_file, video_file, video_style=self.video_style, duration=self.duration_seconds, aspect_ratio=self.aspect_ratio):
                raise Exception("Final video oluşturulamadı")
                
            self.update_progress(100)
            self.finished.emit(True, video_file, metadata)
            
        except Exception as e:
            self.log.emit(f"❌ Hata: {str(e)}", "error")
            self.finished.emit(False, "", {})

class VideoPlayer(QFrame):
    """Video oynatıcı widget"""
    log = pyqtSignal(str, str)  # Log sinyali ekle
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: black;")
        self.setMinimumHeight(300)

        # Ana layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video frame
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_frame, stretch=1)

        # VLC instance - donanım hızlandırma olmadan başlat
        vlc_args = ['--avcodec-hw=none']  # Donanım hızlandırmayı devre dışı bırak
        self.instance = vlc.Instance(vlc_args)
        self.media_player = self.instance.media_player_new()
        self.media_player.video_set_key_input(False)  # Klavye girişini devre dışı bırak
        self.media_player.video_set_mouse_input(False)  # Fare girişini devre dışı bırak

        # Video widget
        if sys.platform == "win32":
            self.media_player.set_hwnd(int(self.video_frame.winId()))
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(int(self.video_frame.winId()))
        else:
            self.media_player.set_xwindow(self.video_frame.winId())

        # Kontroller için frame
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.7);
                border-top: 1px solid #444444;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 4px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QLabel {
                color: white;
                padding: 0px 4px;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #444444;
                margin: 0px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #2979FF;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #2962FF;
            }
        """)
        controls_frame.setFixedHeight(40)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 4, 8, 4)
        controls_layout.setSpacing(8)

        # Geri sarma butonu
        self.rewind_button = QPushButton()
        self.rewind_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekBackward))
        self.rewind_button.setFixedSize(32, 32)
        self.rewind_button.clicked.connect(self.rewind_video)
        controls_layout.addWidget(self.rewind_button)

        # Oynat/Duraklat butonu
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.setFixedSize(32, 32)
        self.play_button.clicked.connect(self.play_pause)
        controls_layout.addWidget(self.play_button)

        # İleri sarma butonu
        self.forward_button = QPushButton()
        self.forward_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekForward))
        self.forward_button.setFixedSize(32, 32)
        self.forward_button.clicked.connect(self.forward_video)
        controls_layout.addWidget(self.forward_button)

        # Geçerli süre etiketi
        self.current_time = QLabel("00:00")
        self.current_time.setStyleSheet("color: white; min-width: 50px;")
        controls_layout.addWidget(self.current_time)

        # İlerleme çubuğu
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.position_slider.sliderPressed.connect(self.slider_pressed)
        self.position_slider.sliderReleased.connect(self.slider_released)
        controls_layout.addWidget(self.position_slider)

        # Toplam süre etiketi
        self.total_time = QLabel("00:00")
        self.total_time.setStyleSheet("color: white; min-width: 50px;")
        controls_layout.addWidget(self.total_time)

        layout.addWidget(controls_frame)

        # Timer for updating slider position
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_ui)

        # Slider takibi için değişkenler
        self.is_slider_pressed = False
        self.video_length = 0

    def play_pause(self):
        """Oynat/Duraklat"""
        if self.media_player.is_playing():
            self.media_player.pause()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.timer.stop()
        else:
            self.media_player.play()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.timer.start()

    def rewind_video(self):
        """5 saniye geri sar"""
        current_time = self.media_player.get_time()
        new_time = max(0, current_time - 5000)  # 5000ms = 5s
        self.media_player.set_time(new_time)

    def forward_video(self):
        """5 saniye ileri sar"""
        current_time = self.media_player.get_time()
        new_time = min(self.video_length, current_time + 5000)  # 5000ms = 5s
        self.media_player.set_time(new_time)

    def slider_pressed(self):
        """Slider'a tıklandığında"""
        self.is_slider_pressed = True
        if self.media_player.is_playing():
            self.media_player.pause()

    def slider_released(self):
        """Slider bırakıldığında"""
        self.is_slider_pressed = False
        self.set_position(self.position_slider.value())
        if self.play_button.icon().cacheKey() == self.style().standardIcon(QStyle.SP_MediaPause).cacheKey():
            self.media_player.play()

    def set_position(self, position):
        """Video pozisyonunu ayarla"""
        self.media_player.set_position(position / 1000.0)

    def format_time(self, ms):
        """Milisaniyeyi MM:SS formatına çevir"""
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"

    def update_ui(self):
        """UI'ı güncelle"""
        if not self.is_slider_pressed:
            media_pos = int(self.media_player.get_position() * 1000)
            self.position_slider.setValue(media_pos)

            # Süre etiketlerini güncelle
            current_ms = self.media_player.get_time()
            self.current_time.setText(self.format_time(current_ms))
            
            if self.video_length == 0:
                self.video_length = self.media_player.get_length()
                self.total_time.setText(self.format_time(self.video_length))

        if not self.media_player.is_playing():
            self.timer.stop()
            if not self.media_player.will_play():
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def loadVideo(self, file_path):
        """Video dosyasını yükle"""
        try:
            if os.path.exists(file_path):
                # Mevcut medyayı durdur ve temizle
                if self.media_player.is_playing():
                    self.media_player.stop()
                
                # Yeni medyayı yükle
                media = self.instance.media_new(file_path)
                self.media_player.set_media(media)
                
                # Medya durumunu kontrol et
                media.parse()
                if media.get_duration() == -1:
                    self.log.emit("❌ Video yüklenemedi: Medya parse edilemedi", "error")
                    return
                
                # Video uzunluğunu sıfırla ve oynatmayı başlat
                self.video_length = 0
                self.play_pause()  # Otomatik başlat
                self.log.emit(f"🎥 Video yüklendi: {file_path}", "success")
            else:
                self.log.emit(f"❌ Video dosyası bulunamadı: {file_path}", "error")
        except Exception as e:
            self.log.emit(f"❌ Video yükleme hatası: {str(e)}", "error")
            # Hata detaylarını logla
            import traceback
            self.log.emit(f"Hata detayları: {traceback.format_exc()}", "error")

class YouTubeAutomationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Otomasyon Aracı")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 600)
        self.worker = None
        self.initUI()
        self.setupStyles()

    def setupStyles(self):
        """Uygulama stillerini ayarla (arayüz görünümünü iyileştirdik)"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1C1C1C, stop:1 #121212);
            }
            QLabel {
                color: #E0E0E0;
                font-size: 12px;
                font-weight: 500;
            }
            QLineEdit, QPlainTextEdit {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 6px;
                font-size: 12px;
                selection-background-color: #2979FF;
            }
            QLineEdit:focus, QPlainTextEdit:focus {
                border: 2px solid #2979FF;
                background-color: #252525;
            }
            QPushButton {
                background-color: #2979FF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2962FF;
            }
            QPushButton:pressed {
                background-color: #2145CC;
            }
            QPushButton:disabled {
                background-color: #424242;
                color: #757575;
            }
            QTextEdit {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Consolas';
                font-size: 12px;
            }
            QProgressBar {
                border: none;
                background-color: #1E1E1E;
                height: 8px;
                text-align: center;
                border-radius: 4px;
                margin: 6px 0px;
            }
            QProgressBar::chunk {
                background-color: #2979FF;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #444444;
                border-radius: 4px;
                background-color: #1E1E1E;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #121212;
                color: #9E9E9E;
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11px;
                font-weight: normal;
                min-width: 100px;
                height: 16px;
            }
            QTabBar::tab:selected {
                background-color: #2979FF;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #252525;
                color: #E0E0E0;
            }
            QGroupBox {
                background-color: #1E1E1E;
                border: 1px solid #444444;
                border-radius: 4px;
                margin-top: 12px;
                padding: 8px;
                font-weight: normal;
            }
            QGroupBox::title {
                color: #E0E0E0;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
                background-color: #1E1E1E;
                font-size: 11px;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #444444;
                margin: 0px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #2979FF;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #2962FF;
            }
            QComboBox {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 4px 8px;
                min-width: 120px;
                font-size: 12px;
            }
            QComboBox:hover {
                border: 1px solid #2979FF;
                background-color: #252525;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E1E;
                color: #E0E0E0;
                selection-background-color: #2979FF;
                selection-color: white;
                border: 1px solid #444444;
                border-radius: 8px;
            }
            QCheckBox {
                color: #E0E0E0;
                spacing: 6px;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 2px solid #444444;
            }
            QCheckBox::indicator:checked {
                background-color: #2979FF;
                border: 2px solid #2979FF;
            }
            QCheckBox::indicator:unchecked {
                background-color: #1E1E1E;
            }
            QRadioButton {
                color: #E0E0E0;
                spacing: 6px;
                font-size: 12px;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 2px solid #444444;
            }
            QRadioButton::indicator:checked {
                background-color: #2979FF;
                border: 2px solid #2979FF;
            }
            QRadioButton::indicator:unchecked {
                background-color: #1E1E1E;
            }
        """)

    def initUI(self):
        """Kullanıcı arayüzünü oluştur"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Ana başlık ve video oluşturma butonu
        header_frame = QFrame()
        header_frame.setStyleSheet("QFrame { background-color: #1E1E1E; border-radius: 12px; }")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(12)

        # Sol taraf - Başlık ve Konu Girişi
        title_layout = QVBoxLayout()
        title_layout.setSpacing(8)

        title_label = QLabel("Video Konusu")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #E0E0E0;")
        title_layout.addWidget(title_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Örneğin: 'Yemek Tarifi - Tavuk Sote'")
        self.title_input.setMinimumHeight(40)
        title_layout.addWidget(self.title_input)

        header_layout.addLayout(title_layout, stretch=2)

        # Sağ taraf - Video Oluştur Butonu
        self.start_btn = QPushButton("Videoyu Oluştur")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setMinimumWidth(200)
        self.start_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_btn.clicked.connect(self.runAutomation)
        header_layout.addWidget(self.start_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)

        main_layout.addWidget(header_frame)

        # Ana sekme widget'ı
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444444;
                border-radius: 4px;
                background-color: #1E1E1E;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #121212;
                color: #9E9E9E;
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11px;
                font-weight: normal;
                min-width: 100px;
                height: 16px;
            }
            QTabBar::tab:selected {
                background-color: #2979FF;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #252525;
                color: #E0E0E0;
            }
        """)

        # 1. Video Ayarları Sekmesi
        video_settings_widget = QWidget()
        video_settings_layout = QVBoxLayout(video_settings_widget)
        video_settings_layout.setSpacing(16)
        video_settings_layout.setContentsMargins(16, 16, 16, 16)

        # Video ayarları grid'i
        settings_grid = QGridLayout()
        settings_grid.setSpacing(16)

        # Temel Video Ayarları Grubu
        basic_video_group = QGroupBox("Temel Video Ayarları")
        basic_video_layout = QGridLayout(basic_video_group)
        basic_video_layout.setSpacing(8)
        basic_video_layout.setContentsMargins(8, 8, 8, 8)

        # Video Süresi
        duration_label = QLabel("Video Süresi")
        self.duration_combo = QComboBox()
        self.duration_combo.addItems([f"{i*10} saniye" for i in range(1, 7)])
        self.duration_combo.setCurrentText("60 saniye")
        self.duration_combo.setFixedHeight(24)
        basic_video_layout.addWidget(duration_label, 0, 0)
        basic_video_layout.addWidget(self.duration_combo, 0, 1)

        # Format Seçimi
        format_label = QLabel("Video Formatı")
        format_layout = QHBoxLayout()
        format_layout.setSpacing(4)
        self.format_16_9 = QRadioButton("16:9")
        self.format_16_9.setChecked(True)
        self.format_9_16 = QRadioButton("9:16")
        format_layout.addWidget(self.format_16_9)
        format_layout.addWidget(self.format_9_16)
        basic_video_layout.addWidget(format_label, 1, 0)
        basic_video_layout.addLayout(format_layout, 1, 1)

        # Kalite Seçimi
        quality_label = QLabel("Video Kalitesi")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["1080p", "720p"])
        self.quality_combo.setFixedHeight(24)
        basic_video_layout.addWidget(quality_label, 2, 0)
        basic_video_layout.addWidget(self.quality_combo, 2, 1)

        settings_grid.addWidget(basic_video_group, 0, 0)

        # Dil ve Altyazı Ayarları Grubu
        language_group = QGroupBox("Dil ve Altyazı Ayarları")
        language_layout = QGridLayout(language_group)
        language_layout.setSpacing(8)
        language_layout.setContentsMargins(8, 8, 8, 8)

        # İçerik Dili
        content_lang_label = QLabel("İçerik Dili")
        self.content_language_combo = QComboBox()
        self.content_language_combo.addItems(["Türkçe", "İngilizce"])
        self.content_language_combo.setFixedHeight(24)
        language_layout.addWidget(content_lang_label, 0, 0)
        language_layout.addWidget(self.content_language_combo, 0, 1)

        # Altyazı Ayarları
        subtitle_label = QLabel("Altyazı")
        subtitle_layout = QHBoxLayout()
        subtitle_layout.setSpacing(4)
        self.subtitle_enabled = QCheckBox("Altyazı Ekle")
        self.subtitle_enabled.setChecked(True)
        self.subtitle_language_combo = QComboBox()
        self.subtitle_language_combo.addItems(["Türkçe", "İngilizce"])
        self.subtitle_language_combo.setFixedHeight(24)
        subtitle_layout.addWidget(self.subtitle_enabled)
        subtitle_layout.addWidget(self.subtitle_language_combo)
        language_layout.addWidget(subtitle_label, 1, 0)
        language_layout.addLayout(subtitle_layout, 1, 1)

        settings_grid.addWidget(language_group, 0, 1)

        # Ses Ayarları Grubu
        voice_group = QGroupBox("Ses Ayarları")
        voice_layout = QGridLayout(voice_group)
        voice_layout.setSpacing(8)
        voice_layout.setContentsMargins(8, 8, 8, 8)

        # Ses Seçimi
        voice_label = QLabel("Ses Tipi")
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["Onyx", "Nova", "Shimmer", "Echo"])
        self.voice_combo.setFixedHeight(24)
        voice_layout.addWidget(voice_label, 0, 0)
        voice_layout.addWidget(self.voice_combo, 0, 1)

        # Ses Hızı
        speed_label = QLabel("Ses Hızı")
        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(4)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_value = QLabel("1.0x")
        self.speed_slider.valueChanged.connect(self.updateSpeedLabel)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_value)
        voice_layout.addWidget(speed_label, 1, 0)
        voice_layout.addLayout(speed_layout, 1, 1)

        settings_grid.addWidget(voice_group, 1, 0, 1, 2)

        video_settings_layout.addLayout(settings_grid)
        self.main_tabs.addTab(video_settings_widget, "Video Ayarları")

        # 2. Efekt Ayarları Sekmesi
        effects_widget = QWidget()
        effects_layout = QVBoxLayout(effects_widget)
        effects_layout.setSpacing(16)
        effects_layout.setContentsMargins(16, 16, 16, 16)

        # Geçiş Efektleri Grubu
        transition_group = QGroupBox("Geçiş Efektleri")
        transition_layout = QGridLayout(transition_group)
        transition_layout.setSpacing(12)

        transition_label = QLabel("Geçiş Tipi")
        self.transition_combo = QComboBox()
        self.transition_combo.addItems(["Fade", "Dissolve", "Cut", "Slide"])
        self.transition_combo.setMinimumHeight(32)
        transition_layout.addWidget(transition_label, 0, 0)
        transition_layout.addWidget(self.transition_combo, 0, 1)

        effects_layout.addWidget(transition_group)

        # Renk Ayarları Grubu
        color_group = QGroupBox("Renk Ayarları")
        color_layout = QGridLayout(color_group)
        color_layout.setSpacing(12)

        # Parlaklık
        brightness_label = QLabel("Parlaklık")
        brightness_layout = QHBoxLayout()
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(-50, 50)
        self.brightness_slider.setValue(0)
        self.brightness_value = QLabel("0")
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_value)
        color_layout.addWidget(brightness_label, 0, 0)
        color_layout.addLayout(brightness_layout, 0, 1)

        # Kontrast
        contrast_label = QLabel("Kontrast")
        contrast_layout = QHBoxLayout()
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(-50, 50)
        self.contrast_slider.setValue(0)
        self.contrast_value = QLabel("0")
        contrast_layout.addWidget(self.contrast_slider)
        contrast_layout.addWidget(self.contrast_value)
        color_layout.addWidget(contrast_label, 1, 0)
        color_layout.addLayout(contrast_layout, 1, 1)

        # Doygunluk
        saturation_label = QLabel("Doygunluk")
        saturation_layout = QHBoxLayout()
        self.saturation_slider = QSlider(Qt.Horizontal)
        self.saturation_slider.setRange(-50, 50)
        self.saturation_slider.setValue(0)
        self.saturation_value = QLabel("0")
        saturation_layout.addWidget(self.saturation_slider)
        saturation_layout.addWidget(self.saturation_value)
        color_layout.addWidget(saturation_label, 2, 0)
        color_layout.addLayout(saturation_layout, 2, 1)

        effects_layout.addWidget(color_group)
        self.main_tabs.addTab(effects_widget, "Efekt Ayarları")

        # 3. İçerik Ayarları Sekmesi
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(16, 16, 16, 16)

        # İçerik Kontrol Grubu
        content_group = QGroupBox("İçerik Kontrol Ayarları")
        content_control_layout = QGridLayout(content_group)
        content_control_layout.setSpacing(12)

        # Sahne Sayısı
        scene_count_label = QLabel("Sahne Sayısı")
        self.scene_count_combo = QComboBox()
        self.scene_count_combo.addItems(["2", "3", "4", "5"])
        self.scene_count_combo.setCurrentText("3")
        self.scene_count_combo.setMinimumHeight(32)
        content_control_layout.addWidget(scene_count_label, 0, 0)
        content_control_layout.addWidget(self.scene_count_combo, 0, 1)

        # Minimum Sahne Süresi
        min_scene_duration_label = QLabel("Minimum Sahne Süresi")
        self.min_scene_duration = QComboBox()
        self.min_scene_duration.addItems([f"{i}s" for i in range(5, 16)])
        self.min_scene_duration.setCurrentText("5s")
        self.min_scene_duration.setMinimumHeight(32)
        content_control_layout.addWidget(min_scene_duration_label, 1, 0)
        content_control_layout.addWidget(self.min_scene_duration, 1, 1)

        # Arama Hassasiyeti
        search_sensitivity_label = QLabel("Arama Hassasiyeti")
        search_layout = QHBoxLayout()
        self.search_sensitivity = QSlider(Qt.Horizontal)
        self.search_sensitivity.setRange(30, 70)
        self.search_sensitivity.setValue(40)
        self.search_sensitivity_value = QLabel("0.4")
        search_layout.addWidget(self.search_sensitivity)
        search_layout.addWidget(self.search_sensitivity_value)
        content_control_layout.addWidget(search_sensitivity_label, 2, 0)
        content_control_layout.addLayout(search_layout, 2, 1)

        content_layout.addWidget(content_group)
        self.main_tabs.addTab(content_widget, "İçerik Ayarları")

        # 4. SEO Bilgileri Sekmesi
        seo_widget = QWidget()
        seo_layout = QVBoxLayout(seo_widget)
        seo_layout.setSpacing(16)
        seo_layout.setContentsMargins(16, 16, 16, 16)

        # Başlık
        title_group = QGroupBox("Video Başlığı")
        title_layout = QVBoxLayout(title_group)
        self.title_edit = QPlainTextEdit()
        self.title_edit.setPlaceholderText("Video başlığı...")
        self.title_edit.setMaximumHeight(80)
        title_layout.addWidget(self.title_edit)
        seo_layout.addWidget(title_group)

        # Açıklama
        desc_group = QGroupBox("Video Açıklaması")
        desc_layout = QVBoxLayout(desc_group)
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Video açıklaması...")
        desc_layout.addWidget(self.description_edit)
        seo_layout.addWidget(desc_group)

        # Etiketler
        tags_group = QGroupBox("Video Etiketleri")
        tags_layout = QVBoxLayout(tags_group)
        self.tags_edit = QPlainTextEdit()
        self.tags_edit.setPlaceholderText("Video etiketleri (virgülle ayırın)...")
        self.tags_edit.setMaximumHeight(80)
        tags_layout.addWidget(self.tags_edit)
        seo_layout.addWidget(tags_group)

        # Kopyalama Butonları
        copy_layout = QHBoxLayout()
        self.copy_title_button = QPushButton("Başlığı Kopyala")
        self.copy_description_button = QPushButton("Açıklamayı Kopyala")
        self.copy_tags_button = QPushButton("Etiketleri Kopyala")
        copy_layout.addWidget(self.copy_title_button)
        copy_layout.addWidget(self.copy_description_button)
        copy_layout.addWidget(self.copy_tags_button)
        seo_layout.addLayout(copy_layout)

        self.copy_all_button = QPushButton("Tümünü Kopyala")
        seo_layout.addWidget(self.copy_all_button)

        self.main_tabs.addTab(seo_widget, "SEO Bilgileri")

        # 5. Önizleme Sekmesi
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setSpacing(16)
        preview_layout.setContentsMargins(16, 16, 16, 16)

        self.video_player = VideoPlayer()
        self.video_player.setMinimumHeight(300)
        self.video_player.log.connect(self.log)
        preview_layout.addWidget(self.video_player)

        self.main_tabs.addTab(preview_widget, "Önizleme")

        main_layout.addWidget(self.main_tabs)

        # İlerleme Çubuğu
        progress_frame = QFrame()
        progress_frame.setStyleSheet("QFrame { background-color: #1E1E1E; border-radius: 8px; }")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(16, 16, 16, 16)
        progress_layout.setSpacing(8)

        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setTextVisible(True)
        self.progress.setMinimumHeight(8)
        progress_layout.addWidget(self.progress)

        # Log Alanı
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("İşlem günlükleri burada görünecek...")
        self.log_output.setMaximumHeight(100)
        progress_layout.addWidget(self.log_output)

        main_layout.addWidget(progress_frame)

    def updateDurationLabel(self, index):
        """Süre etiketini güncelle"""
        duration = (index + 1) * 10
        self.duration_label.setText(f"Süre: {duration} saniye")

    def updateSpeedLabel(self, value):
        """Hız etiketini güncelle"""
        speed = value / 100.0
        self.speed_value.setText(f"{speed:.1f}x")

    def log(self, message, message_type="info"):
        """Log mesajını görüntüle"""
        color = {
            "info": "#ffffff",
            "error": "#ff4d4d",
            "warning": "#ffa500",
            "success": "#00cc66"
        }.get(message_type, "#ffffff")

        self.log_output.append(f"<span style='color: {color};'>{message}</span>")

    def onProcessFinished(self, success, video_file, metadata):
        """Video oluşturma işlemi tamamlandığında çağrılır"""
        try:
            if success and os.path.exists(video_file):
                self.log("✅ Video başarıyla oluşturuldu!", "success")
                
                # Video önizleme
                self.main_tabs.setCurrentIndex(0)
                self.video_player.loadVideo(video_file)
                
                # SEO bilgilerini göster
                if "seo" in metadata:
                    seo_data = metadata["seo"]
                    self.title_edit.setPlainText(seo_data.get("title", ""))
                    self.description_edit.setPlainText(seo_data.get("description", ""))
                    self.tags_edit.setPlainText(", ".join(seo_data.get("tags", [])))
            else:
                self.log("❌ Video oluşturma başarısız oldu!", "error")
                if not os.path.exists(video_file):
                    self.log("❌ Video dosyası bulunamadı!", "error")
                
        except Exception as e:
            self.log(f"❌ Önizleme yüklenirken hata: {str(e)}", "error")
        finally:
            self.start_btn.setEnabled(True)
            self.progress.setValue(0)

    def copy_title(self):
        """Başlığı kopyala"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.title_edit.toPlainText())
        QMessageBox.information(self, "Bilgi", "Başlık panoya kopyalandı.")

    def copy_description(self):
        """Açıklamayı kopyala"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.description_edit.toPlainText())
        QMessageBox.information(self, "Bilgi", "Açıklama panoya kopyalandı.")

    def copy_tags(self):
        """Etiketleri kopyala"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.tags_edit.toPlainText())
        QMessageBox.information(self, "Bilgi", "Etiketler panoya kopyalandı.")

    def copy_all_seo(self):
        """Tüm SEO bilgilerini kopyala"""
        all_text = f"Başlık:\n{self.title_edit.toPlainText()}\n\n"
        all_text += f"Açıklama:\n{self.description_edit.toPlainText()}\n\n"
        all_text += f"Etiketler:\n{self.tags_edit.toPlainText()}"
        
        clipboard = QApplication.clipboard()
        clipboard.setText(all_text)
        
        QMessageBox.information(self, "Bilgi", "Tüm SEO bilgileri panoya kopyalandı.")

    def runAutomation(self):
        """Video oluşturma sürecini başlat"""
        topic = self.title_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "Uyarı", "Video konusu boş olamaz!")
            return

        self.start_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log_output.clear()
        self.title_edit.clear()
        self.description_edit.clear()
        self.tags_edit.clear()

        duration = (self.duration_combo.currentIndex() + 1) * 10
        voice = self.voice_combo.currentText()
        speed = self.speed_slider.value() / 100.0
        aspect_ratio = "16:9" if self.format_16_9.isChecked() else "9:16"
        quality = self.quality_combo.currentText()
        content_language = "tr" if self.content_language_combo.currentText() == "Türkçe" else "en"
        subtitle_enabled = self.subtitle_enabled.isChecked()
        subtitle_language = "tr" if self.subtitle_language_combo.currentText() == "Türkçe" else "en"

        # Video stili ayarlarını hazırla
        video_style = {
            "transitions": {
                "type": self.transition_combo.currentText().lower(),
                "duration": 0.5
            },
            "filters": {
                "brightness": self.brightness_slider.value(),
                "contrast": self.contrast_slider.value(),
                "saturation": self.saturation_slider.value()
            },
            "text": {
                "font": "Arial",
                "size": 24,
                "color": "#FFFFFF",
                "animation": "fade",
                "position": "center"
            },
            "subtitle": {
                "enabled": subtitle_enabled,
                "language": subtitle_language,
                "text": "",  # Bu alan content üretildikten sonra doldurulacak
                "font": "Arial",
                "size": 24,
                "color": "#FFFFFF",
                "background": "#000000",
                "opacity": 0.8
            },
            "audio": {
                "music_type": "none",
                "volume": 100,
                "fade": True
            }
        }

        # İçerik kontrolü ayarlarını hazırla
        content_settings = {
            "scene_count": int(self.scene_count_combo.currentText()),
            "min_scene_duration": int(self.min_scene_duration.currentText().replace('s', '')),
            "search_sensitivity": self.search_sensitivity.value() / 100.0,
            "language": content_language
        }
        
        self.worker = VideoWorker(
            topic=topic,
            duration_seconds=duration,
            voice=voice,
            speed=speed,
            aspect_ratio=aspect_ratio,
            quality=quality,
            video_style=video_style,
            content_settings=content_settings,
            content_language=content_language,
            subtitle_enabled=subtitle_enabled,
            subtitle_language=subtitle_language
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.onProcessFinished)
        self.worker.start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = YouTubeAutomationApp()
    window.show()
    sys.exit(app.exec_())
