import openai
from typing import Optional, Dict, List
from config import OPENAI_API_KEY, print_error, print_warning

openai.api_key = OPENAI_API_KEY

def parse_seo_response(response: str) -> Optional[Dict[str, str]]:
    """
    API yanıtını başlık, açıklama ve etiketlere ayır
    
    Args:
        response (str): API'den gelen yanıt
        
    Returns:
        Optional[Dict[str, str]]: Ayrıştırılmış SEO içeriği veya None
    """
    try:
        parts = {}
        current_key = None
        current_content = []
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Başlık:'):
                if current_key:
                    parts[current_key] = '\n'.join(current_content).strip()
                current_key = 'title'
                current_content = [line.replace('Başlık:', '').strip()]
            elif line.startswith('Açıklama:'):
                if current_key:
                    parts[current_key] = '\n'.join(current_content).strip()
                current_key = 'description'
                current_content = [line.replace('Açıklama:', '').strip()]
            elif line.startswith('Etiketler:'):
                if current_key:
                    parts[current_key] = '\n'.join(current_content).strip()
                current_key = 'tags'
                current_content = [line.replace('Etiketler:', '').strip()]
            else:
                current_content.append(line)
                
        if current_key:
            parts[current_key] = '\n'.join(current_content).strip()
            
        # Etiketleri liste haline getir
        if 'tags' in parts:
            parts['tags'] = [tag.strip() for tag in parts['tags'].split(',')]
            
        required_keys = {'title', 'description', 'tags'}
        if not all(key in parts for key in required_keys):
            print_warning("Eksik SEO bilgileri var. Tüm alanlar doldurulmalı.")
            return None
            
        return parts
        
    except Exception as e:
        print_error(f"SEO yanıtı ayrıştırma hatası: {str(e)}")
        return None

def generate_seo(topic: str, max_length: int = 500) -> Optional[Dict[str, str]]:
    """
    YouTube videosu için SEO içeriği oluştur
    
    Args:
        topic (str): Video konusu
        max_length (int): Maksimum token sayısı
        
    Returns:
        Optional[Dict[str, str]]: SEO içeriği veya None (hata durumunda)
    """
    # System prompt tanımla
    system_prompt = "Sen bir YouTube SEO uzmanısın. Verilen konu için YouTube videoları için SEO dostu başlık, açıklama ve etiketler oluşturuyorsun."
    
    prompt = f"""
    '{topic}' konulu bir YouTube videosu için SEO içeriği oluştur.
    
    Lütfen aşağıdaki formatta yanıt ver:
    
    Başlık:
    - 60 karakterden kısa
    - Dikkat çekici
    - Anahtar kelime içeren
    - Tıklanma oranı yüksek
    
    Açıklama:
    - İlk 2-3 cümle en önemli bilgileri içermeli
    - Anahtar kelimeleri doğal şekilde kullan
    - Video içeriğini özetle
    - İzleyiciyi harekete geçirecek çağrı ekle
    
    Etiketler:
    - En önemli anahtar kelimelerden başla
    - Hem tekil hem çoğul formları kullan
    - Benzer ve ilişkili terimleri ekle
    - Virgülle ayır
    """
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system", 
                "content": system_prompt
            }, {
                "role": "user", 
                "content": prompt
            }],
            temperature=0.7
        )
        
        if not response.choices:
            print_error("API yanıt vermedi veya boş yanıt döndü")
            return None
            
        content = response.choices[0].message.content.strip()
        return parse_seo_response(content)
        
    except openai.BadRequestError as e:
        print_error(f"Geçersiz istek: {str(e)}")
    except openai.AuthenticationError:
        print_error("API anahtarı geçersiz veya eksik")
    except openai.RateLimitError:
        print_error("API kullanım limiti aşıldı. Lütfen daha sonra tekrar deneyin.")
    except Exception as e:
        print_error(f"SEO içeriği oluşturma hatası: {str(e)}")
        
    return None

def validate_seo_content(seo_data: Dict[str, str]) -> bool:
    """
    SEO içeriğinin geçerliliğini kontrol et
    
    Args:
        seo_data (Dict[str, str]): Kontrol edilecek SEO içeriği
        
    Returns:
        bool: Geçerli ise True, değilse False
    """
    try:
        # Başlık kontrolü
        if len(seo_data['title']) > 60:
            print_warning(f"Başlık çok uzun: {len(seo_data['title'])} karakter")
            return False
            
        # Açıklama kontrolü
        if len(seo_data['description']) > 5000:
            print_warning(f"Açıklama çok uzun: {len(seo_data['description'])} karakter")
            return False
            
        # Etiket kontrolü
        if not isinstance(seo_data['tags'], list):
            print_warning("Etiketler liste formatında değil")
            return False
            
        if len(seo_data['tags']) < 3:
            print_warning("Çok az etiket var")
            return False
            
        return True
        
    except Exception as e:
        print_error(f"SEO içeriği doğrulama hatası: {str(e)}")
        return False

if __name__ == "__main__":
    # Test için
    test_topic = "Python Programlama"
    seo_content = generate_seo(test_topic)
    
    if seo_content and validate_seo_content(seo_content):
        print("\nOluşturulan SEO İçeriği:")
        print("-" * 50)
        print(f"Başlık: {seo_content['title']}")
        print(f"\nAçıklama:\n{seo_content['description']}")
        print(f"\nEtiketler:\n{', '.join(seo_content['tags'])}")
        print("-" * 50)
