import openai
from typing import Dict, List, Tuple
from config import print_error, print_warning, print_success, OPENAI_API_KEY

# OpenAI istemcisini yapılandır
openai.api_key = OPENAI_API_KEY

class VideoAnalyzer:
    """Video içerik analizi ve kalite değerlendirmesi için sınıf"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
    def _extract_title_from_url(self, url: str) -> str:
        """URL'den video başlığını çıkar"""
        try:
            # URL'yi parçala ve son kısmı al
            parts = url.rstrip('/').split('/')
            last_part = parts[-1]
            
            # ID'yi kaldır
            title = '-'.join(last_part.split('-')[:-1])
            
            # Tire işaretlerini boşluğa çevir
            return ' '.join(title.split('-'))
        except:
            return ""
            
    def analyze_content_relevance(self, query: str, video_data: Dict) -> Tuple[float, str]:
        """
        Video içeriğinin arama sorgusuyla alakasını analiz et
        
        Returns:
            Tuple[float, str]: (Alakalılık skoru (0-1), Açıklama)
        """
        try:
            # URL'den başlığı çıkar
            url_title = self._extract_title_from_url(video_data.get('url', ''))
            
            # Video bilgilerini birleştir (daha detaylı format)
            video_content = {
                "url_title": url_title,
                "title": video_data.get('title', ''),
                "description": video_data.get('description', ''),
                "tags": ', '.join(video_data.get('tags', [])),
                "user_info": {
                    "name": video_data.get('user', {}).get('name', ''),
                    "url": video_data.get('user', {}).get('url', '')
                }
            }
            
            # System prompt tanımla
            system_prompt = "Sen bir video içerik analisti ve alakalılık uzmanısın. Verilen video içeriğinin arama sorgusuyla ne kadar alakalı olduğunu değerlendiriyorsun."
            
            # Daha detaylı prompt
            prompt = f"""Video içeriğini arama sorgusuyla karşılaştır ve alakalılık skoru ver.

Arama Sorgusu: '{query}'

Video İçeriği:
1. URL Başlığı: {video_content['url_title']}
2. Başlık: {video_content['title']}
3. Açıklama: {video_content['description']}
4. Etiketler: {video_content['tags']}
5. Yükleyici: {video_content['user_info']['name']}

Yanıt formatı:
Skor:[0-1]
Neden:[Kısa açıklama]"""
            
            # OpenAI API'yi çağır
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7
            )
            
            # Yanıtı parse et
            response_text = response.choices[0].message.content.strip()
            score_line = [line for line in response_text.split('\n') if line.startswith('Skor:')][0]
            explanation_line = [line for line in response_text.split('\n') if line.startswith('Neden:')][0]
            
            # Skoru düzgün şekilde parse et
            score_text = score_line.split(':')[1].strip()
            if score_text.startswith('[') and score_text.endswith(']'):
                score_text = score_text[1:-1]  # Köşeli parantezleri kaldır
            score = float(score_text)
            
            explanation = explanation_line.split(':')[1].strip()
            
            return min(max(score, 0), 1), explanation
            
        except Exception as e:
            print_warning(f"İçerik analizi hatası: {str(e)}")
            return 0.5, "Analiz sırasında hata oluştu"
            
    def calculate_quality_score(self, video: Dict) -> Tuple[float, Dict[str, float]]:
        """
        Video kalitesini değerlendir
        
        Returns:
            Tuple[float, Dict[str, float]]: (Toplam kalite skoru, Alt skorlar)
        """
        try:
            scores = {}
            
            # 1. Çözünürlük Skoru (1080p = 1.0)
            resolution = video['width'] * video['height']
            scores['resolution'] = min(resolution / (1920 * 1080), 1.0)
            
            # 2. FPS Skoru (30fps = 1.0)
            fps = video.get('fps', 30)
            scores['fps'] = min(fps / 30, 1.0)
            
            # 3. Süre Uygunluğu (10-30 sn arası ideal)
            duration = video['duration']
            if 10 <= duration <= 30:
                scores['duration'] = 1.0
            elif duration < 10:
                scores['duration'] = duration / 10
            else:
                scores['duration'] = max(1 - (duration - 30) / 30, 0)
            
            # 4. Görüntü Kalitesi
            quality_map = {
                'hd': 1.0,
                'sd': 0.7,
                'low': 0.3
            }
            video_quality = video.get('quality', 'sd').lower() if video.get('quality') else 'sd'
            scores['quality'] = quality_map.get(video_quality, 0.5)
            
            # 5. Popülerlik ve Etkileşim (eğer varsa)
            if 'views' in video:
                scores['popularity'] = min(video['views'] / 10000, 1.0)
            if 'likes' in video and 'dislikes' in video:
                total_reactions = video['likes'] + video['dislikes']
                scores['engagement'] = video['likes'] / total_reactions if total_reactions > 0 else 0.5
            
            # Ağırlıklı ortalama
            weights = {
                'resolution': 0.3,
                'fps': 0.1,
                'duration': 0.2,
                'quality': 0.2,
                'popularity': 0.1,
                'engagement': 0.1
            }
            
            # Sadece mevcut skorları kullan
            total_score = 0
            total_weight = 0
            for key, score in scores.items():
                if key in weights:
                    total_score += score * weights[key]
                    total_weight += weights[key]
            
            final_score = total_score / total_weight if total_weight > 0 else 0.5
            return final_score, scores
            
        except Exception as e:
            print_warning(f"Kalite hesaplama hatası: {str(e)}")
            return 0.5, {'error': str(e)}
            
    def get_video_score(self, query: str, video: Dict, weights: Dict[str, float] = None) -> Dict:
        """
        Video için toplam skor hesapla
        
        Args:
            query (str): Arama sorgusu
            video (Dict): Video bilgileri
            weights (Dict[str, float]): Skorların ağırlıkları
                {'relevance': 0.6, 'quality': 0.4} varsayılan
                
        Returns:
            Dict: Detaylı skor bilgileri
        """
        if weights is None:
            weights = {'relevance': 0.6, 'quality': 0.4}
            
        # İçerik alakalılığını analiz et
        relevance_score, relevance_explanation = self.analyze_content_relevance(query, video)
        
        # Kalite skorunu hesapla
        quality_score, quality_details = self.calculate_quality_score(video)
        
        # Toplam skoru hesapla
        total_score = (
            relevance_score * weights['relevance'] +
            quality_score * weights['quality']
        )
        
        return {
            'total_score': total_score,
            'relevance': {
                'score': relevance_score,
                'explanation': relevance_explanation
            },
            'quality': {
                'score': quality_score,
                'details': quality_details
            }
        }
