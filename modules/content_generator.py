import openai
import json
import re
from typing import Dict, Any
from config import OPENAI_API_KEY, print_error, print_success, print_warning

# OpenAI istemcisini yapılandır
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def fix_json_format(json_str: str) -> str:
    """
    OpenAI API'den gelen hatalı JSON formatını düzelt
    
    Args:
        json_str (str): Düzeltilecek JSON string
        
    Returns:
        str: Düzeltilmiş JSON string
    """
    try:
        # Markdown kod bloğunu temizle
        if json_str.startswith("```json"):
            json_str = json_str.replace("```json", "", 1)
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        
        json_str = json_str.strip()
        
        # Eksik virgülleri ekle
        # 1. Satır sonlarında } veya ] karakterinden sonra , olmayan yerlere , ekle
        json_str = re.sub(r'([\}\]])\s*\n\s*"', r'\1,\n"', json_str)
        
        # 2. Satır sonlarında " karakterinden sonra , olmayan yerlere , ekle (değer-anahtar çiftleri arasında)
        json_str = re.sub(r'("[^"]*")\s*\n\s*"', r'\1,\n"', json_str)
        
        # 3. Satır sonlarında sayı karakterinden sonra , olmayan yerlere , ekle
        json_str = re.sub(r'(\d+)\s*\n\s*"', r'\1,\n"', json_str)
        
        # 4. Dizi elemanları arasında virgül ekle
        json_str = re.sub(r'(\{[^\{\}]*\})\s*\n\s*\{', r'\1,\n{', json_str)
        
        # 5. Dizi elemanları arasında virgül ekle (string elemanlar için)
        json_str = re.sub(r'("[^"]*")\s*\n\s*"', r'\1,\n"', json_str)
        
        # JSON'ı doğrula
        json.loads(json_str)
        
        return json_str
    except Exception as e:
        print_warning(f"JSON düzeltme hatası: {str(e)}")
        return json_str

def generate_youtube_content(topic: str, duration_seconds: int, content_language: str = "tr", subtitle_language: str = None) -> Dict[str, Any]:
    """
    OpenAI API ile video içeriği üret
    
    Args:
        topic (str): Video konusu
        duration_seconds (int): Video süresi (saniye)
        content_language (str): İçerik dili ("tr" veya "en")
        subtitle_language (str, optional): Altyazı dili ("tr" veya "en"). None ise content_language kullanılır.
        
    Returns:
        Dict[str, Any]: Video içeriği
    """
    try:
        # Altyazı dili belirtilmemişse içerik dilini kullan
        subtitle_language = subtitle_language or content_language
        
        # Her sahne için minimum 5, maksimum 15 saniye
        scene_count = max(duration_seconds // 10, 2)  # En az 2 sahne olsun
        
        # Dil ayarlarını belirle
        lang_settings = {
            "tr": {
                "system_prompt": "Sen bir Türkçe video içerik uzmanısın. Verilen konu için "
                               "video senaryosu ve basit arama terimleri üretiyorsun.",
                "content_note": "Türkçe, anlaşılır metin",
                "title_note": "Video başlığı (Türkçe)",
                "desc_note": "Video açıklaması (Türkçe)",
                "tags_note": "Türkçe etiketler"
            },
            "en": {
                "system_prompt": "You are an English video content expert. You create "
                               "video scripts and simple search terms for given topics.",
                "content_note": "Clear English text",
                "title_note": "Video title (English)",
                "desc_note": "Video description (English)",
                "tags_note": "English tags"
            }
        }
        
        settings = lang_settings.get(content_language, lang_settings["tr"])
        
        # OpenAI API'ye gönderilecek istem
        prompt = f"""
        {topic} konusunda {duration_seconds} saniyelik bir video için içerik üret.
        İçerik dili: {content_language.upper()}
        Altyazı dili: {subtitle_language.upper()}
        
        SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir şey yazma:
        {{
            "tts_text": "{settings['content_note']}",
            "subtitle_text": "Altyazı metni ({subtitle_language.upper()})",
            "pexels_prompts": [
                {{
                    "query": "Ana konu + eylem (örn: pasta cooking, pasta boiling)",
                    "description": "Bu sahne için açıklama ({content_language.upper()})",
                    "duration": 10
                }}
            ],
            "video_style": {{
                "transitions": {{
                    "type": "fade/dissolve/cut/slide",
                    "duration": 0.5
                }},
                "filters": {{
                    "brightness": 0-100,
                    "contrast": 0-100,
                    "saturation": 0-100,
                    "sharpness": 0-100
                }},
                "text": {{
                    "font": "font_name",
                    "size": 12-72,
                    "color": "hex_color",
                    "animation": "fade/slide/zoom",
                    "position": "top/center/bottom"
                }},
                "subtitle": {{
                    "enabled": true,
                    "language": "{subtitle_language}",
                    "text": "",
                    "font": "Arial",
                    "size": 24,
                    "color": "#FFFFFF",
                    "background": "#000000",
                    "opacity": 0.8
                }},
                "audio": {{
                    "music_type": "calm/energetic/dramatic/none",
                    "volume": 0-100,
                    "fade": true/false
                }}
            }},
            "seo": {{
                "title": "{settings['title_note']}",
                "description": "{settings['desc_note']}",
                "tags": ["{settings['tags_note']}"]
            }},
            "duration": {duration_seconds}
        }}
        
        Önemli kurallar:
        1. tts_text: {content_language.upper()} dilinde, akıcı ve doğal bir anlatım olmalı
           - TTS metni 30-40 saniye arasında okunacak uzunlukta olmalı
           - Konu hakkında detaylı ve kapsamlı bilgi içermeli
           - En az 4-5 cümle içermeli
        2. subtitle_text: {subtitle_language.upper()} dilinde, tts_text'in çevirisi olmalı
        3. pexels_prompts: 
           - En az {scene_count} adet sahne olmalı
           - Her sahne 5-15 saniye arasında olmalı
           - Sahnelerin toplam süresi {duration_seconds} saniyeyi geçmemeli
           - Her sahnenin arama terimi (query) şu formatta olmalı:
             * Sadece tek kelime kullan (örn: "pasta", "kebap", "dolma")
             * Konuyla doğrudan ilgili tek kelimelik terimler kullan
             * Eylem veya detay ekleme, sadece ana konuyu belirten tek kelime yeterli
             * Daha genel ve bilgi verici videolar için uygun terimler kullan
             * Çok spesifik veya nadir bulunan içerikler yerine yaygın ve kolay bulunabilir içerikler tercih et
           - Örnek arama terimleri:
             * Yemek tarifi için: "pasta", "kebap", "dolma", "baklava"
             * Doğa için: "kuş", "orman", "deniz", "dağ"
        4. video_style: Konuya uygun video stili
        5. seo: {content_language.upper()} dilinde, SEO dostu başlık ve açıklama
        6. duration değeri tam olarak {duration_seconds} olmalı
        7. SADECE JSON yanıtı ver, başka hiçbir şey yazma
        8. Tüm sayıları rakam olarak değil, yazı olarak yaz. Örneğin "1881" yerine "bin sekiz yüz seksen bir" şeklinde.
        """
        
        # OpenAI API'yi çağır
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": settings["system_prompt"]
            }, {
                "role": "user",
                "content": prompt
            }],
            temperature=0.7
        )
        
        # API yanıtını al
        api_response = response.choices[0].message.content
        
        # JSON formatını düzelt
        fixed_json = fix_json_format(api_response)
        
        # JSON yanıtını parse et
        content = json.loads(fixed_json)
        
        # Zorunlu alanları kontrol et
        required_fields = ["tts_text", "subtitle_text", "pexels_prompts", "video_style", "seo", "duration"]
        for field in required_fields:
            if field not in content:
                raise ValueError(f"Eksik alan: {field}")
                
        # pexels_prompts formatını kontrol et
        if not isinstance(content["pexels_prompts"], list):
            raise ValueError("pexels_prompts bir liste olmalı")
            
        if len(content["pexels_prompts"]) != scene_count:
            raise ValueError(f"pexels_prompts tam olarak {scene_count} öğe içermeli")
            
        for prompt in content["pexels_prompts"]:
            required_prompt_fields = ["query", "description", "duration"]
            for field in required_prompt_fields:
                if field not in prompt:
                    raise ValueError(f"Eksik prompt alanı: {field}")
                    
        # video_style formatını kontrol et
        video_style_fields = ["transitions", "filters", "text", "subtitle", "audio"]
        for field in video_style_fields:
            if field not in content["video_style"]:
                raise ValueError(f"Eksik video_style alanı: {field}")
                
        # SEO alanlarını kontrol et
        seo_fields = ["title", "description", "tags"]
        for field in seo_fields:
            if field not in content["seo"]:
                raise ValueError(f"Eksik SEO alanı: {field}")
                
        # Altyazı metnini video_style'a ekle
        content["video_style"]["subtitle"]["text"] = content["subtitle_text"]
                
        # Başarılı mesajı
        print_success(f"İçerik başarıyla oluşturuldu: {content['seo']['title']}")
        return content
        
    except json.JSONDecodeError as e:
        print_error(f"JSON parse hatası: {str(e)}")
        print_error(f"API yanıtı: {response.choices[0].message.content if hasattr(response, 'choices') and response.choices else 'Yanıt yok'}")
    except openai.APIError as e:
        print_error(f"OpenAI API hatası: {str(e)}")
    except openai.AuthenticationError as e:
        print_error(f"OpenAI API kimlik doğrulama hatası: {str(e)}")
    except openai.RateLimitError as e:
        print_error(f"OpenAI API kullanım limiti aşıldı: {str(e)}")
    except Exception as e:
        print_error(f"İçerik üretme hatası: {str(e)}")
        import traceback
        print_error(f"Hata ayrıntıları: {traceback.format_exc()}")
        
    return None

if __name__ == "__main__":
    # Test
    test_topic = "Kediler hakkında ilginç bilgiler"
    test_duration = 60  # 1 dakika
    
    content = generate_youtube_content(test_topic, test_duration)
    if content:
        print("\nTest başarılı!")
        print(f"TTS Metni:\n{content['tts_text']}\n")
        print(f"Pexels Arama Terimleri:\n{content['pexels_prompts']}\n")
        print(f"Video Stili:\n{json.dumps(content['video_style'], indent=2, ensure_ascii=False)}")
        print(f"SEO Bilgileri:\n{json.dumps(content['seo'], indent=2, ensure_ascii=False)}")
    else:
        print("\nTest başarısız!")
