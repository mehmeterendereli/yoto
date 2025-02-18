import openai
import os
from typing import Optional
from config import OPENAI_API_KEY, print_error, print_success, print_warning

def generate_tts(text: str, output_file: str, voice: str = "onyx", speed: float = 1.0) -> bool:
    """
    OpenAI TTS ile ses oluştur
    
    Args:
        text (str): Sese dönüştürülecek metin
        output_file (str): Çıktı ses dosyası yolu
        voice (str): Kullanılacak ses (alloy, echo, fable, onyx, nova, shimmer)
        speed (float): Konuşma hızı (0.25 ile 4.0 arası)
        
    Returns:
        bool: Başarılı ise True, değilse False
    """
    try:
        print_warning(f"OpenAI TTS ile ses oluşturuluyor... (Ses: {voice}, Hız: {speed}x)")
        
        # Hız kontrolü
        if speed < 0.25 or speed > 4.0:
            print_warning(f"Geçersiz hız: {speed}. Varsayılan: 1.0 kullanılacak.")
            speed = 1.0
        
        # OpenAI istemcisini oluştur
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Sesi oluştur
        response = client.audio.speech.create(
            model="tts-1",  # En doğal TTS modeli
            voice=voice.lower(),  # Küçük harfe çevir
            input=text,
            speed=speed  # Konuşma hızı
        )
        
        # Ses dosyasını kaydet
        response.stream_to_file(output_file)
            
        print_success(f"Ses dosyası oluşturuldu: {output_file}")
        return True
        
    except Exception as e:
        print_error(f"OpenAI TTS hatası: {str(e)}")
        return False

if __name__ == "__main__":
    # Test için
    test_text = "Merhaba, bu bir OpenAI TTS test konuşmasıdır."
    test_file = "test_audio.mp3"
    
    if generate_tts(test_text, test_file, speed=1.5):
        print("\nTest başarılı!")
    else:
        print("\nTest başarısız!")
