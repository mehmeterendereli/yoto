import os
import subprocess
import re
from typing import List, Optional, Dict
from config import print_error, print_success, print_warning, FFMPEG_PATH
import logging

# FFmpeg yolunu kontrol et
if not FFMPEG_PATH:
    raise ImportError("FFmpeg bulunamadı! Video işleme özellikleri kullanılamaz.")

def get_audio_duration(audio_file: str) -> float:
    """Ses dosyasının süresini al"""
    cmd = [
        FFMPEG_PATH,
        '-i', audio_file,
        '-show_entries', 'format=duration',
        '-v', 'quiet',
        '-of', 'csv=p=0'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print_warning(f"FFmpeg çıktısı: {result.stdout}")
    if result.stdout.strip():
        return float(result.stdout.strip())
    
    # Alternatif yöntem
    cmd = [FFMPEG_PATH, '-i', audio_file, '-f', 'null', '-']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.stderr:
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', result.stderr)
        if duration_match:
            hours, minutes, seconds = map(float, duration_match.groups())
            return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"FFmpeg ses dosyası süresini alamadı: {audio_file}")

def split_text_into_sentences(text: str) -> List[str]:
    """Metni cümlelere ayır"""
    # Noktalama işaretlerine göre böl
    sentences = re.split(r'[.!?]+', text)
    # Boş cümleleri temizle
    return [s.strip() for s in sentences if s.strip()]

def split_text_into_phrases(text: str) -> List[str]:
    """Metni 2-3 kelimelik parçalara ayır"""
    # Önce cümleleri ayır
    sentences = re.split(r'[.!?]+', text)
    phrases = []
    
    for sentence in sentences:
        # Boş cümleleri atla
        if not sentence.strip():
            continue
            
        # Kelimeleri ayır
        words = sentence.strip().split()
        
        # 2-3 kelimelik gruplar oluştur
        for i in range(0, len(words), 2):
            if i + 2 <= len(words):
                phrases.append(' '.join(words[i:i+2]))
            else:
                # Son kelime tek kaldıysa önceki gruba ekle
                if len(phrases) > 0:
                    phrases[-1] = phrases[-1] + ' ' + words[i]
                else:
                    phrases.append(words[i])
    
    return phrases

def create_subtitle_filter(text: str, audio_duration: float, aspect_ratio: str = "9:16") -> str:
    """Altyazı filtresi oluştur"""
    # Metni cümlelere ayır
    sentences = split_text_into_sentences(text)
    if not sentences:
        # Eğer cümle yoksa, metni doğrudan kullan
        sentences = [text]
    
    total_sentences = len(sentences)
    duration_per_sentence = audio_duration / total_sentences
    
    # Font boyutu ve pozisyonu ayarla (9:16 formatı için daha büyük font)
    font_size = "h/18" if aspect_ratio == "9:16" else "h/16"
    y_pos = "h-h/4" if aspect_ratio == "9:16" else "h-h/4"
    
    # Tek bir drawtext filtresi oluştur
    filters = []
    current_time = 0
    
    print_warning(f"Altyazı metni: {text}")
    print_warning(f"Cümle sayısı: {total_sentences}")
    
    for i, sentence in enumerate(sentences):
        # Metni temizle
        clean_sentence = sentence.replace("'", "'").replace('"', '\\"').strip()
        if not clean_sentence:
            continue
            
        print_warning(f"Cümle {i+1}: {clean_sentence}")
        
        start_time = current_time
        end_time = start_time + duration_per_sentence
        
        # Her altyazı için ayrı bir drawtext filtresi
        filter_text = (
            f"drawtext=text='{clean_sentence}'"
            f":fontsize={font_size}"
            f":fontcolor=white"
            f":box=1:boxcolor=black@0.7"  # Arka plan opaklığını artır
            f":x=(w-text_w)/2:y={y_pos}"
            f":enable='between(t,{start_time},{end_time})'"
        )
        
        filters.append(filter_text)
        current_time = end_time
    
    # Filtreleri virgülle birleştir
    return ','.join(filters)

def create_video(video_files: List[str], audio_file: str, output_file: str, video_style: Dict = None, duration: float = None, aspect_ratio: str = "9:16") -> bool:
    """
    Videoları ve ses dosyasını birleştir
    
    Args:
        video_files (List[str]): Video dosyalarının yolları
        audio_file (str): Ses dosyası yolu
        output_file (str): Çıktı video dosyası yolu
        video_style (Dict, optional): Video stili
        duration (float, optional): Manuel video süresi (saniye)
        aspect_ratio (str, optional): Video en-boy oranı ("16:9" veya "9:16")
        
    Returns:
        bool: Başarılı ise True, değilse False
    """
    try:
        print_warning(f"Video dosyaları: {video_files}")
        print_warning(f"Ses dosyası: {audio_file}")
        print_warning(f"Çıktı dosyası: {output_file}")
        
        # Dosyaların varlığını kontrol et
        for video_file in video_files:
            if not os.path.exists(video_file):
                print_error(f"Video bulunamadı: {video_file}")
                return False
            else:
                print_warning(f"Video dosyası mevcut: {video_file}")
                
        if not os.path.exists(audio_file):
            print_error(f"Ses dosyası bulunamadı: {audio_file}")
            return False
        else:
            print_warning(f"Ses dosyası mevcut: {audio_file}")
            
        # Ses dosyasının süresini al
        audio_duration = get_audio_duration(audio_file)
        print_warning(f"Ses dosyası süresi: {audio_duration} saniye")
        
        # Her video için gereken süreyi hesapla
        video_count = len(video_files)
        duration_per_video = audio_duration / video_count if not duration else duration / video_count
        
        # İstenen en-boy oranı için boyutları belirle
        if aspect_ratio == "16:9":
            target_width = 1920
            target_height = 1080
        else:  # 9:16
            target_width = 1080
            target_height = 1920
        
        # Çıktı dizinini oluştur
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        
        # Video birleştirme ve altyazı ekleme
        if video_style and 'subtitle' in video_style and video_style['subtitle'].get('enabled', False):
            subtitle_text = video_style['subtitle'].get('text', '')
            if subtitle_text:
                # Önce videoları birleştir
                video_inputs = ''.join(f'[v{i}]' for i in range(len(video_files)))
                filter_chains = []
                
                # Her video için scale, trim ve setsar
                for i in range(len(video_files)):
                    filter_chains.append(
                        f'[{i}:v]trim=0:{duration_per_video},setpts=PTS-STARTPTS,'
                        f'scale={target_width}:{target_height}:force_original_aspect_ratio=increase,'
                        f'crop={target_width}:{target_height},setsar=1:1[v{i}]'
                    )
                
                # Videoları birleştir
                filter_chains.append(f'{video_inputs}concat=n={len(video_files)}:v=1:a=0[base]')
                
                # Altyazı filtrelerini ekle
                subtitle_filter = create_subtitle_filter(subtitle_text, audio_duration, aspect_ratio)
                filter_chains.append(f'[base]{subtitle_filter}[vfinal]')
                
                # Ses işleme
                filter_chains.append(f'[{len(video_files)}:a]asetpts=PTS-STARTPTS[afinal]')
                
                # Tüm filtreleri birleştir
                filter_complex = ';'.join(filter_chains)
            else:
                # Altyazı yoksa sadece videoları birleştir
                filter_complex = simple_concat_filter(video_files, audio_file, duration_per_video, target_width, target_height)
        else:
            # Altyazı devre dışıysa sadece videoları birleştir
            filter_complex = simple_concat_filter(video_files, audio_file, duration_per_video, target_width, target_height)
        
        # FFmpeg komutunu oluştur
        input_args = []
        for video_file in video_files:
            input_args.extend(['-i', video_file])
        input_args.extend(['-i', audio_file])
        
        # Önce NVIDIA GPU ile deneyelim
        final_cmd = [
            FFMPEG_PATH,
            '-y',
            *input_args,
            '-filter_complex', filter_complex,
            '-map', '[vfinal]',
            '-map', '[afinal]',
            '-c:v', 'h264_nvenc',
            '-preset', 'p4',
            '-rc:v', 'vbr',
            '-b:v', '5M',
            '-maxrate:v', '10M',
            '-bufsize:v', '10M',
            '-r', '30',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_file
        ]
        
        print_warning(f"NVIDIA GPU ile deneniyor...")
        print_warning(f"FFmpeg komutu: {' '.join(final_cmd)}")
        result = subprocess.run(final_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        # Eğer NVIDIA GPU ile başarısız olursa, CPU kodlayıcısını dene
        if result.returncode != 0:
            print_warning("NVIDIA GPU ile başarısız oldu, CPU kodlayıcısı deneniyor...")
            
            # CPU kodlayıcısı ile yeni komut
            final_cmd = [
                FFMPEG_PATH,
                '-y',
                *input_args,
                '-filter_complex', filter_complex,
                '-map', '[vfinal]',
                '-map', '[afinal]',
                '-c:v', 'libx264',  # CPU kodlayıcısı
                '-preset', 'medium',  # Hız/kalite dengesi
                '-crf', '23',  # Kalite seviyesi (0-51, düşük=daha iyi)
                '-r', '30',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '192k',
                output_file
            ]
            
            print_warning(f"FFmpeg komutu (CPU): {' '.join(final_cmd)}")
            result = subprocess.run(final_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode != 0:
            print_error(f"FFmpeg hatası: {result.stderr}")
            return False
            
        print_success(f"Video başarıyla oluşturuldu: {output_file}")
        return True
        
    except Exception as e:
        print_error(f"Video oluşturma hatası: {str(e)}")
        import traceback
        print_error(f"Hata ayrıntıları: {traceback.format_exc()}")
        return False

def simple_concat_filter(video_files: List[str], audio_file: str, duration_per_video: float, target_width: int, target_height: int) -> str:
    """
    Basit birleştirme filtresi oluştur
    
    Args:
        video_files (List[str]): Video dosyalarının listesi
        audio_file (str): Ses dosyası yolu
        duration_per_video (float): Her video için süre
        target_width (int): Hedef video genişliği
        target_height (int): Hedef video yüksekliği
    """
    filter_chains = []
    
    # Her video için scale, trim ve setsar
    for i in range(len(video_files)):
        filter_chains.append(
            f'[{i}:v]trim=0:{duration_per_video},setpts=PTS-STARTPTS,'
            f'scale={target_width}:{target_height}:force_original_aspect_ratio=increase,'
            f'crop={target_width}:{target_height},setsar=1:1[v{i}]'
        )
    
    # Videoları birleştir
    video_inputs = ''.join(f'[v{i}]' for i in range(len(video_files)))
    filter_chains.append(f'{video_inputs}concat=n={len(video_files)}:v=1:a=0[vfinal]')
    
    # Ses işleme
    filter_chains.append(f'[{len(video_files)}:a]asetpts=PTS-STARTPTS[afinal]')
    
    return ';'.join(filter_chains)

if __name__ == "__main__":
    # Test
    test_videos = ["test_video_1.mp4", "test_video_2.mp4"]
    test_audio = "test_audio.mp3"
    test_output = "test_video.mp4"
    
    if create_video(test_videos, test_audio, test_output):
        print("\nTest başarılı!")
    else:
        print("\nTest başarısız!")
