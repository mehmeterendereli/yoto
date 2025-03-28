import os
import requests
import json
import time
from typing import List, Dict, Optional, Tuple
from config import print_error, print_success, print_warning, print_info
from .video_analyzer import VideoAnalyzer
import openai
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# API anahtarlarını al
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Sabitleri tanımla
CACHE_DIR = "cache/pexels"
CACHE_DURATION = 6 * 60 * 60  # 6 saat (saniye cinsinden)

class VideoSearchService:
    """Pexels API ile akıllı video arama servisi"""
    
    def __init__(self):
        if not PEXELS_API_KEY:
            raise ValueError("PEXELS_API_KEY bulunamadı!")
            
        # API endpoint ve headers
        self.api_url = "https://api.pexels.com/videos/search"
        self.headers = {
            "Authorization": PEXELS_API_KEY
        }
        
        # OpenAI istemcisi
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY bulunamadı!")
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Video analiz servisi
        self.analyzer = VideoAnalyzer()
        
        # Cache dizinini oluştur
        os.makedirs(CACHE_DIR, exist_ok=True)
        
    def _get_english_search_term(self, query: str) -> str:
        """GPT ile Türkçe sorguyu İngilizce arama terimine çevir"""
        try:
            prompt = f"""Verilen Türkçe konuyu analiz et ve Pexels'te video aramak için en uygun İngilizce arama terimlerini üret.

Önemli kurallar:
1. Önce konuyu analiz et ve ana konuyu (main_subject) belirle
2. Her arama terimi SADECE TEK KELİME olmalı
3. Arama terimleri şu şekilde olmalı:
   - Birincil terimler: Ana konuyu temsil eden tek kelimeler (örn: "pasta", "kebap", "dolma")
   - İkincil terimler: Ana konuyla ilgili diğer tek kelimeler (örn: "makarna", "et", "sebze")
   - Bağlam terimleri: Ana konunun bağlamıyla ilgili tek kelimeler (örn: "mutfak", "yemek", "tarif")
4. Arama terimleri şu yapıda olmalı:
   - Sadece tek kelime
   - Yemek tarifi ise yemek adı olmalı (örn: "kebap", "dolma", "baklava")
   - Doğa/hayvan konuları ise canlı adı olmalı (örn: "kuş", "aslan", "orman")
5. Asla konudan sapma! Örnek:
   - "Makarna tarifi" için -> "pasta", "makarna", "spagetti"
   - "Kuşların beslenmesi" için -> "kuş", "tohum", "yem"
6. Her terim sadece tek kelime olmalı

Örnek 1:
Konu: "Makarna nasıl yapılır?"
Analiz: 
- Ana konu: pasta/spaghetti
Birincil terimler: 
- "pasta"
- "spaghetti"
- "noodle"
İkincil terimler:
- "sauce"
- "tomato"
- "cheese"
Bağlam terimleri:
- "kitchen"
- "cooking"
- "food"

Türkçe konu: "{query}"
Yanıtı JSON formatında ver:
{{
    "analysis": {{
        "main_subject": "Ana konu/yemek/canlı adı",
        "subject_type": "food/animal/nature/other",
        "context": "Bağlam açıklaması"
    }},
    "search_terms": {{
        "primary": ["terim1", "terim2", "terim3"],
        "secondary": ["terim1", "terim2", "terim3"],
        "context": ["terim1", "terim2", "terim3"]
    }}
}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Güncel model adı
                messages=[{
                    "role": "system",
                    "content": "Sen bir doğa belgeseli ve video içerik uzmanısın. Konuları derinlemesine analiz edip, "
                              "en uygun ve doğal video sahnelerini bulmak için arama terimleri üretiyorsun."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.7,
                max_tokens=200
            )
            
            # Yanıtı parse et
            try:
                content = response.choices[0].message.content.strip()
                # JSON başlangıç ve bitiş noktalarını bul
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                    search_data = json.loads(json_str)
                else:
                    raise ValueError("JSON verisi bulunamadı")
                    
            except (json.JSONDecodeError, ValueError) as e:
                print_warning(f"JSON parse hatası: {str(e)}")
                # Basit bir arama verisi oluştur
                search_data = {
                    "analysis": {
                        "main_subject": query,
                        "subject_type": query.split()[0],
                        "context": query
                    },
                    "search_terms": {
                        "primary": ["bird eating seeds", "bird catching insects", "bird pecking food"],
                        "secondary": ["bird feeding nature", "bird foraging", "bird hunting"],
                        "context": ["birds habitat", "bird natural", "birds wildlife"]
                    }
                }
            
            # Analizi logla
            print_success(f"Konu Analizi:")
            print_success(f"- Ana Konu: {search_data['analysis']['main_subject']}")
            print_success(f"- Konu Tipi: {search_data['analysis']['subject_type']}")
            print_success(f"- Bağlam: {search_data['analysis']['context']}")
            
            # Arama terimlerini logla
            print_success(f"\nBirincil Terimler: {', '.join(search_data['search_terms']['primary'])}")
            print_success(f"İkincil Terimler: {', '.join(search_data['search_terms']['secondary'])}")
            print_success(f"Bağlam Terimleri: {', '.join(search_data['search_terms']['context'])}")
            
            return search_data
            
        except Exception as e:
            print_warning(f"Arama terimi oluşturma hatası: {str(e)}")
            return {
                "analysis": {
                    "main_subject": query,
                    "subject_type": query.split()[0],
                    "context": query
                },
                "search_terms": {
                    "primary": ["bird eating"],
                    "secondary": ["bird nature"],
                    "context": ["bird wildlife"]
                }
            }

    def search_videos(self, query: str, min_duration: int = 5, max_duration: int = 15, per_page: int = 10) -> List[dict]:
        """Pexels'te video ara"""
        try:
            videos = []
            used_video_ids = set()  # Kullanılan video ID'lerini takip et
            
            # Eğer query bir dict ise, query alanını al
            if isinstance(query, dict):
                query = query.get('query', '')
            
            # Ana konuyu belirle
            search_data = self._get_english_search_term(query)
            main_subject = search_data['analysis']['main_subject']
            subject_type = search_data['analysis']['subject_type']
            
            # Yedek arama terimleri
            backup_terms = [
                "cooking food",
                "kitchen cooking",
                "food preparation",
                "cooking ingredients",
                "food serving",
                "kitchen preparation"
            ]
            
            # Arama terimlerini hazırla
            search_terms = []
            # Birincil terimleri ekle
            search_terms.extend(search_data['search_terms']['primary'][:2])
            # İkincil terimleri ekle
            search_terms.extend(search_data['search_terms']['secondary'][:2])
            # Bağlam terimlerini ekle
            search_terms.extend(search_data['search_terms']['context'][:2])
            # Yedek terimleri ekle
            search_terms.extend(backup_terms)
            
            # Her terim için arama yap
            for term in search_terms:
                if len(videos) >= 6:  # 6 video bulduysak dur
                    break
                    
                print_info(f"Arama: {term}")
                
                # Ana konuyu içeren spesifik arama terimi oluştur
                if subject_type == 'food':
                    # Yemek konuları için sadece tek kelime yeterli
                    search_term = term
                else:
                    # Diğer konular için ana konuyu ekle (örn: "Istanbul bridge")
                    # Ana konu tek kelime ise ve terim de aynıysa tekrar ekleme
                    if ' ' not in main_subject and term.lower() == main_subject.lower():
                        search_term = term
                    else:
                        search_term = f"{main_subject} {term}"
                
                print_info(f"Spesifik arama: {search_term}")
                
                # Arama yap
                results = self._search_pexels_videos(
                    query=search_term,
                    min_duration=min_duration,
                    max_duration=max_duration
                )
                
                # Sonuçları filtrele ve ekle
                for video in results:
                    if video['id'] not in used_video_ids:
                        used_video_ids.add(video['id'])
                        # Her videodan 10 saniye alacağız
                        video['target_duration'] = 10
                        videos.append(video)
                        if len(videos) >= 6:
                            break
                
                if len(videos) > 0 and videos[-1]['id'] not in used_video_ids:
                    break  # Bu terim için video bulduk
            
            # En az 1 video olsun
            if not videos:
                raise Exception(f"Hiç video bulunamadı!")
                
            return videos[:6]  # En fazla 6 video döndür
            
        except Exception as e:
            print_error(f"Video arama hatası: {str(e)}")
            raise

    def _check_subject_relevance(self, video: Dict, main_subject: str) -> bool:
        """Video içeriğinin ana özneyle alakalı olup olmadığını kontrol et"""
        try:
            # Video başlığı, açıklaması ve etiketlerinde ana özneyi ara
            content = f"{video.get('title', '')} {video.get('description', '')} {' '.join(video.get('tags', []))}"
            content = content.lower()
            
            # Ana özneyi ve ilgili terimleri kontrol et
            subject_terms = {
                'bird': ['bird', 'birds', 'avian', 'fowl', 'feather'],
                'lion': ['lion', 'lions', 'feline', 'predator', 'cat'],
                'elephant': ['elephant', 'elephants', 'pachyderm', 'trunk'],
                'fish': ['fish', 'fishes', 'marine', 'aquatic', 'underwater'],
                # Diğer yaygın özneler için benzer eşleşmeler eklenebilir
            }
            
            # Ana özneyi normalize et
            main_subject = main_subject.lower()
            
            # Direkt eşleşme kontrolü
            if main_subject in content:
                return True
                
            # İlgili terimler kontrolü
            for subject, terms in subject_terms.items():
                if subject in main_subject:
                    return any(term in content for term in terms)
            
            return False
            
        except Exception as e:
            print_warning(f"Özne kontrolü hatası: {str(e)}")
            return True  # Hata durumunda videoyu eleme

    def _process_video_results(self, videos: List[Dict], search_term: str, min_duration: int, max_duration: int) -> List[Dict]:
        """Video sonuçlarını işle ve filtrele"""
        processed_videos = []
        for video in videos:
            duration = video['duration']
            if duration < min_duration or duration > max_duration:
                continue
                
            video['search_term'] = search_term
            processed_videos.append(video)
            
        return processed_videos

    def download_video(self, video: Dict, output_path: str, chunk_size: int = 8192) -> Optional[str]:
        """
        Videoyu indir
        
        Args:
            video (Dict): Video bilgileri
            output_path (str): Çıktı dosyası yolu
            chunk_size (int): İndirme parça boyutu
            
        Returns:
            Optional[str]: İndirilen dosyanın yolu veya None
        """
        try:
            # Klasörü oluştur
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Videoyu indir
            response = requests.get(video["download_url"], stream=True, timeout=30)
            response.raise_for_status()
            
            # Toplam boyutu al
            total_size = int(response.headers.get('content-length', 0))
            
            # Dosyaya kaydet
            with open(output_path, 'wb') as f:
                if total_size == 0:
                    # Boyut bilinmiyorsa direkt kaydet
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                else:
                    # İlerleme göster
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = (downloaded / total_size) * 100
                            print(f"\rİndiriliyor: %{progress:.1f}", end="")
                    print()  # Yeni satır
                        
            print_success(f"Video indirildi: {output_path}")
            return output_path
            
        except requests.exceptions.RequestException as e:
            print_error(f"Video indirme hatası: {str(e)}")
        except Exception as e:
            print_error(f"Beklenmeyen hata: {str(e)}")
            return None

    def _search_pexels_videos(self, query: str, min_duration: int = 5, max_duration: int = 15) -> List[dict]:
        """Pexels API ile video ara"""
        try:
            # API'ye istek at
            response = requests.get(
                self.api_url,
                headers=self.headers,
                params={
                    "query": query,
                    "per_page": 10,
                    "min_duration": min_duration,
                    "max_duration": max_duration
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data and 'videos' in data and data['videos']:
                # Videoları filtrele
                filtered_videos = []
                for video in data['videos']:
                    # Video süresini kontrol et
                    duration = video['duration']
                    if duration < min_duration or duration > max_duration:
                        continue
                    
                    # En iyi kalitedeki video dosyasını bul
                    if not video.get('video_files'):
                        continue
                        
                    # Video dosyalarını kaliteye göre sırala
                    best_quality = None
                    for vf in video['video_files']:
                        width = vf.get('width', 0)
                        height = vf.get('height', 0)
                        
                        # HD kalitede video seç (720p ve üzeri)
                        if width >= 1280 or height >= 720:
                            if not best_quality or (vf.get('height', 0) > best_quality.get('height', 0)):
                                best_quality = vf
                                best_quality['quality'] = 'hd'
                    
                    if best_quality:
                        filtered_videos.append({
                            'id': video['id'],
                            'duration': duration,
                            'width': best_quality.get('width', 0),
                            'height': best_quality.get('height', 0),
                            'download_url': best_quality['link'],
                            'quality': best_quality.get('quality', 'sd')
                        })
                
                return filtered_videos
            
            return []
            
        except Exception as e:
            print_error(f"Pexels API hatası: {str(e)}")
            return []

if __name__ == "__main__":
    # Test
    service = VideoSearchService()
    
    def inspect_video_data(query: str):
        """API'den gelen ham video verisini incele"""
        try:
            # API'ye direkt istek at
            response = requests.get(
                service.api_url,
                headers=service.headers,
                params={"query": query, "per_page": 1},
                timeout=10
            )
            response.raise_for_status()
            
            # Ham veriyi al
            data = response.json()
            if data.get("videos"):
                video = data["videos"][0]
                print("\nPexels API Ham Video Verisi:")
                print(json.dumps(video, indent=2, ensure_ascii=False))
                
                print("\nKullanılabilir Alanlar:")
                for key, value in video.items():
                    print(f"\n{key}:")
                    if isinstance(value, dict):
                        for k, v in value.items():
                            print(f"  - {k}: {v}")
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                print("  -", json.dumps(item))
                            else:
                                print(f"  - {item}")
                    else:
                        print(f"  {value}")
            
        except Exception as e:
            print_error(f"API inceleme hatası: {str(e)}")
    
    # Normal test
    test_query = "cat playing"
    print("\n=== Normal Arama Testi ===")
    videos = service.search_videos(test_query)
    
    if videos:
        # Videoyu indir
        video = videos[0]
        output_path = f"test_video_{video['id']}.mp4"
        
        if service.download_video(video, output_path):
            print("\nTest başarılı!")
            print(f"Video: {video['url']}")
            print(f"Süre: {video['duration']} saniye")
            print(f"Boyut: {video['width']}x{video['height']}")
            print(f"Kalite: {video['quality']}")
        else:
            print("\nTest başarısız: Video indirilemedi!")
    else:
        print("\nTest başarısız: Video bulunamadı!")
        
    # API yanıtını incele
    print("\n=== API Yanıt İncelemesi ===")
    inspect_video_data(test_query)
