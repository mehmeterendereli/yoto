import os
import json
import argparse
from typing import Dict, Tuple, Optional
from modules.content_generator import generate_youtube_content
from modules.tts_generator import generate_tts
from modules.video_search_service import VideoSearchService
from modules.video_editor import create_video
from config import print_error, print_success, print_warning

def create_project_folder(topic: str) -> str:
    """Proje klasörünü oluştur"""
    folder_name = '_'.join(topic.split()[:2])
    folder_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in folder_name)
    folder_path = os.path.join("output", folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def save_content(content: Dict, project_dir: str) -> str:
    """İçeriği JSON olarak kaydet"""
    content_file = os.path.join(project_dir, "content.json")
    with open(content_file, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    return content_file

def download_video(video: Dict, project_dir: str) -> Optional[str]:
    """Pexels'ten video indir"""
    video_file = os.path.join(project_dir, "videos", f"video_{video['id']}.mp4")
    os.makedirs(os.path.dirname(video_file), exist_ok=True)
    
    video_service = VideoSearchService()
    return video_service.download_video(video, video_file)

def create_youtube_video(topic: str, duration: int = 60, language: str = "tr") -> Tuple[Optional[str], Optional[Dict]]:
    """
    YouTube videosu oluştur
    
    Args:
        topic (str): Video konusu
        duration (int): Video süresi (saniye)
        language (str): İçerik dili ("tr" veya "en")
        
    Returns:
        Tuple[Optional[str], Optional[Dict]]: (Video dosyası yolu, İçerik bilgileri)
    """
    try:
        # 1. Proje klasörü
        print_warning(f"🚀 Proje başlatılıyor: {topic}")
        project_dir = create_project_folder(topic)
        
        # 2. OpenAI API ile içerik üretimi
        print_warning(f"📝 İçerik oluşturuluyor... (Dil: {language.upper()})")
        content = generate_youtube_content(topic, duration, content_language=language)
        if not content:
            raise Exception("İçerik üretilemedi")
            
        # İçeriği kaydet
        content_file = save_content(content, project_dir)
        print_success(f"İçerik kaydedildi: {content_file}")
        
        # 3. TTS ile seslendirme
        print_warning("🎤 Seslendirme oluşturuluyor...")
        audio_file = os.path.join(project_dir, "audio.mp3")
        if not generate_tts(content["tts_text"], audio_file):
            raise Exception("Ses oluşturulamadı")
        print_success(f"Ses dosyası oluşturuldu: {audio_file}")
        
        # 4. Pexels'ten videolar
        print_warning("🎥 Videolar aranıyor...")
        video_service = VideoSearchService()
        video_files = []
        
        for idx, prompt in enumerate(content["pexels_prompts"], 1):
            print_warning(f"Video {idx}/{len(content['pexels_prompts'])}: {prompt}")
            
            # Video ara
            videos = video_service.search_videos(
                query=prompt,
                per_page=3,
                min_duration=3,
                max_duration=10
            )
            if not videos:
                raise Exception(f"Video bulunamadı: {prompt}")
                
            # İlk videoyu indir
            video_file = download_video(videos[0], project_dir)
            if not video_file:
                raise Exception(f"Video indirilemedi: {prompt}")
                
            video_files.append(video_file)
            print_success(f"Video indirildi: {video_file}")
            
        # 5. FFmpeg ile montaj
        print_warning("🎬 Video oluşturuluyor...")
        output_file = os.path.join(project_dir, "video.mp4")
        
        # TTS süresine göre video süresini ayarla
        from modules.video_editor import get_audio_duration
        audio_duration = get_audio_duration(audio_file)
        print_warning(f"TTS süresi: {audio_duration} saniye. Video bu süreye göre ayarlanıyor.")
        
        if not create_video(video_files, audio_file, output_file, duration=audio_duration, aspect_ratio="9:16"):
            raise Exception("Video oluşturulamadı")
            
        print_success(f"Video başarıyla oluşturuldu: {output_file}")
        return output_file, content
        
    except Exception as e:
        print_error(f"Hata: {str(e)}")
        return None, None

def main():
    """Ana program"""
    parser = argparse.ArgumentParser(description="YouTube Video Otomasyon Aracı")
    parser.add_argument("--topic", required=True, help="Video konusu")
    parser.add_argument("--duration", type=int, default=60, help="Video süresi (saniye)")
    parser.add_argument("--language", choices=["tr", "en"], default="tr", help="İçerik dili (tr veya en)")
    args = parser.parse_args()
    
    video_file, content = create_youtube_video(args.topic, args.duration, args.language)
    if video_file and content:
        print("\n✅ İşlem başarıyla tamamlandı!")
        print(f"Video: {video_file}")
        print(f"Başlık: {content['seo']['title']}")
        print(f"Açıklama: {content['seo']['description']}")
        print(f"Etiketler: {', '.join(content['seo']['tags'])}")
    else:
        print("\n❌ İşlem başarısız oldu!")
        
if __name__ == "__main__":
    main()
