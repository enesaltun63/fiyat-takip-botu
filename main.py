from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import threading
import time

app = Flask(__name__)

URL = "https://www.epey.com/robot-supurge/karsilastir/918677-986565/roborock-s8-maxv-ultra_roborock-saros-10/farklari/"

# Scraper API ayarları
SCRAPER_API_KEY = "74da8d5818894ee4b48725b819b48f53"
SCRAPER_API_URL = "http://api.scraperapi.com"

# Telegram ayarları (Environment Variables'dan gelecek)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Fiyat geçmişi
fiyat_gecmisi = []
son_fiyat = None

def telegram_mesaj_gonder(mesaj):
    """Telegram'a mesaj gönder"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram ayarları yapılmamış!")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': mesaj,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Telegram mesajı gönderildi!")
            return True
        else:
            print(f"❌ Telegram hatası: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram mesaj hatası: {e}")
        return False

def fiyat_al():
    """Scraper API ile fiyat çekme"""
    try:
        print(f"🔄 Fiyat çekiliyor (Scraper API)...")
        
        # Scraper API parametreleri
        params = {
            'api_key': SCRAPER_API_KEY,
            'url': URL,
            'render': 'false',
            'country_code': 'tr'
        }
        
        # Scraper API üzerinden istek gönder
        response = requests.get(SCRAPER_API_URL, params=params, timeout=60)
        
        print(f"📡 Status Code: {response.status_code}")
        print(f"📦 Content Length: {len(response.content)} bytes")
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code} hatası")
            return None
        
        soup = BeautifulSoup(response.content, 'lxml')
        print(f"🔍 BeautifulSoup parse tamamlandı")
        
        # Tüm fiyatları bul
        fiyat_elementleri = soup.find_all('span', class_='urun_fiyat')
        print(f"📊 Bulunan fiyat sayısı: {len(fiyat_elementleri)}")
        
        if fiyat_elementleri:
            # İlk (en üstteki) fiyatı al
            ilk_element = fiyat_elementleri[0]
            
            # Sadece fiyat kısmını al (TL içeren ilk text)
            fiyat_text = ilk_element.get_text(strip=True)
            print(f"🔎 Ham fiyat text: {fiyat_text[:50]}...")
            
            # "Ücretsiz Kargo" gibi ek metinleri temizle
            fiyat = fiyat_text.split('TL')[0].strip() + ' TL'
            
            print(f"✅ En üstteki fiyat bulundu: {fiyat}")
            return fiyat
        else:
            print("❌ span.urun_fiyat elementi bulunamadı")
            
            # Debug: Sayfada ne var?
            tum_spanlar = soup.find_all('span', limit=5)
            print(f"📋 İlk 5 span elementi:")
            for i, span in enumerate(tum_spanlar, 1):
                print(f"  {i}. class={span.get('class')} text={span.get_text(strip=True)[:30]}")
            
            return None
            
    except Exception as e:
        print(f"❌ Hata tipi: {type(e).__name__}")
        print(f"❌ Hata mesajı: {str(e)[:200]}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()[:500]}")
        return None

def arka_plan_kontrol():
    """Arka planda sürekli fiyat kontrolü"""
    global son_fiyat
    
    # Bot başladığında bildirim gönder
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        telegram_mesaj_gonder("🤖 <b>Fiyat Takip Botu Başladı!</b>\n\n📍 Ürün takibe alındı.\n⏰ Her 45 dakikada kontrol edilecek.")
    
    while True:
        try:
            yeni_fiyat = fiyat_al()
            
            if yeni_fiyat:
                zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if son_fiyat and yeni_fiyat != son_fiyat:
                    print(f"⚠️ Fiyat değişti! {son_fiyat} → {yeni_fiyat}")
                    
                    # Telegram bildirimi gönder
                    mesaj = f"""
🔔 <b>FİYAT DEĞİŞTİ!</b>

📦 <b>Ürün:</b> Roborock Robot Süpürge

💰 <b>Eski Fiyat:</b> {son_fiyat}
💰 <b>Yeni Fiyat:</b> {yeni_fiyat}

🔗 <a href="{URL}">Ürüne Git</a>

⏰ {zaman}
                    """
                    telegram_mesaj_gonder(mesaj.strip())
                    
                    fiyat_gecmisi.append({
                        'zaman': zaman,
                        'fiyat': yeni_fiyat,
                        'degisim': True,
                        'eski_fiyat': son_fiyat
                    })
                else:
                    print(f"📦 Fiyat: {yeni_fiyat}")
                    fiyat_gecmisi.append({
                        'zaman': zaman,
                        'fiyat': yeni_fiyat,
                        'degisim': False
                    })
                
                son_fiyat = yeni_fiyat
                
                # Son 100 kaydı sakla
                if len(fiyat_gecmisi) > 100:
                    fiyat_gecmisi.pop(0)
                    
        except Exception as e:
            print(f"❌ Kontrol hatası: {e}")
        
        # 45 dakika bekle
        time.sleep(2700)

@app.route('/')
def home():
    telegram_aktif = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    return jsonify({
        'status': 'çalışıyor',
        'bot': 'Fiyat Takip Botu',
        'url': URL,
        'son_fiyat': son_fiyat,
        'kontrol_periyodu': '45 dakika',
        'telegram_bildirim': 'aktif' if telegram_aktif else 'pasif',
        'scraper_api': 'aktif'
    })

@app.route('/fiyat')
def get_fiyat():
    """Anlık fiyat sorgulama"""
    fiyat = fiyat_al()
    return jsonify({
        'fiyat': fiyat,
        'zaman': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'url': URL
    })

@app.route('/gecmis')
def get_gecmis():
    """Fiyat geçmişini göster"""
    return jsonify({
        'toplam_kayit': len(fiyat_gecmisi),
        'gecmis': fiyat_gecmisi[-20:]
    })

@app.route('/test-telegram')
def test_telegram():
    """Telegram bildirimini test et"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return jsonify({
            'status': 'hata',
            'mesaj': 'Telegram ayarları yapılmamış!'
        }), 400
    
    test_mesaji = f"""
🧪 <b>Test Mesajı</b>

✅ Telegram bildirimleri çalışıyor!

⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    """
    
    sonuc = telegram_mesaj_gonder(test_mesaji.strip())
    
    return jsonify({
        'status': 'başarılı' if sonuc else 'başarısız',
        'telegram_token': 'ayarlı' if TELEGRAM_BOT_TOKEN else 'yok',
        'chat_id': 'ayarlı' if TELEGRAM_CHAT_ID else 'yok'
    })

@app.route('/health')
def health():
    """Render için health check"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    # Arka plan thread'ini başlat
    thread = threading.Thread(target=arka_plan_kontrol, daemon=True)
    thread.start()
    
    # Flask uygulamasını başlat
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
