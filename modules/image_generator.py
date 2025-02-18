import openai
import requests
from typing import Optional, Tuple
from config import (
    OPENAI_API_KEY, 
    print_error, 
    print_warning,
    print_success,
    DALLE_SETTINGS
)

openai.api_key = OPENAI_API_KEY

def validate_dalle_settings(model: str, size: str, quality: str) -> Tuple[str, str, str]:
    """
    DALL-E ayarlarını doğrula
    
    Args:
        model (str): DALL-E modeli ("dall-e-2" veya "dall-e-3")
        size (str): Görsel boyutu (örn: "1024x1024")
        quality (str): Görsel kalitesi ("standard" veya "hd")
        
    Returns:
        Tuple[str, str, str]: (model, size, quality)
    """
    # Model kontrolü
    if model not in DALLE_SETTINGS:
        print_warning(f"Geçersiz model: {model}. Varsayılan: dall-e-2 kullanılacak.")
        model = "dall-e-2"
    
    # Boyut kontrolü
    if size not in DALLE_SETTINGS[model]["sizes"]:
        print_warning(f"Geçersiz boyut: {size}. Varsayılan: 1024x1024 kullanılacak.")
        size = "1024x1024"
    
    # Kalite kontrolü
    if quality not in DALLE_SETTINGS[model]["quality"]:
        print_warning(f"Geçersiz kalite: {quality}. Varsayılan: standard kullanılacak.")
        quality = "standard"
    
    return model, size, quality

def generate_image(
    prompt: str, 
    output_file: str, 
    model: str = "dall-e-2",
    size: str = "1024x1024",
    quality: str = "standard"
) -> Optional[Tuple[str, str]]:
    """
    DALL·E kullanarak görsel oluştur
    
    Args:
        prompt (str): DALL-E promptu
        output_file (str): Çıktı dosyası yolu
        model (str): DALL-E modeli ("dall-e-2" veya "dall-e-3")
        size (str): Görsel boyutu (örn: "1024x1024")
        quality (str): Görsel kalitesi ("standard" veya "hd")
        
    Returns:
        Optional[Tuple[str, str]]: (Oluşturulan dosya yolu, Kullanılan prompt) veya (None, None)
    """
    # Ayarları doğrula
    model, size, quality = validate_dalle_settings(model, size, quality)
    
    try:
        # DALL·E ile görsel oluştur
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size=size,
            quality=quality,
            response_format="url"
        )
        
        if not response.data:
            print_error("API yanıt vermedi veya boş yanıt döndü")
            return None, None
            
        image_url = response.data[0].url
        
        # Görseli indir
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()  # HTTP hatalarını kontrol et
            
            # Görseli kaydet
            with open(output_file, 'wb') as handler:
                handler.write(response.content)
                
            print_success(f"Görsel başarıyla oluşturuldu: {output_file}")
            return output_file, prompt
            
        except requests.exceptions.Timeout:
            print_error("Görsel indirme zaman aşımına uğradı")
        except requests.exceptions.RequestException as e:
            print_error(f"Görsel indirme hatası: {str(e)}")
        except IOError as e:
            print_error(f"Dosya kaydetme hatası: {str(e)}")
            
        return None, None
        
    except openai.BadRequestError as e:
        print_error(f"Geçersiz istek: {str(e)}")
    except openai.AuthenticationError:
        print_error("API anahtarı geçersiz veya eksik")
    except openai.RateLimitError:
        print_error("API kullanım limiti aşıldı. Lütfen daha sonra tekrar deneyin.")
    except Exception as e:
        print_error(f"Beklenmeyen hata: {str(e)}")
        
    return None, None

if __name__ == "__main__":
    # Test için
    test_prompt = "Bir grup işçi karıncanın yaprak parçalarını taşıdığı doğal bir ortam"
    test_file = "test_image.jpg"
    
    result = generate_image(
        prompt=test_prompt,
        output_file=test_file,
        model="dall-e-3",
        size="1024x1024",
        quality="hd"
    )
    if result[0]:
        print(f"\nTest başarılı! Görsel oluşturuldu: {test_file}")
        print(f"Kullanılan prompt:\n{result[1]}")
    else:
        print("\nTest başarısız!")
