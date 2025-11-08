from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import threading
import time

# Cloudflare bypass için
try:
    import cloudscraper
    SCRAPER = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
except ImportError:
    SCRAPER = requests.Session()

app = Flask(__name__)

# Takip edilecek URL
URL = "https://www.epey.com/robot-supurge/karsilastir/918677-986565/roborock-s8-maxv-ultra_roborock-saros-10/farklari/"

# Telegram ayarları (Environment Variables'dan gelecek)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Global değişkenler
fiyat_gecmisi = []
son_fiyat = None
bot_baslama_zamani = datetime.now()

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
            print(f"❌ Telegram hatası: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram mesaj hatası: {e}")
        return False

def fiyat_al():
    """Web scraping ile fiyat çekme"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/',
            'Upgrade-Insecure-Requests': '1'
        }
        
        print(f"🔄 Fiyat çekiliyor... ({datetime.now().strftime('%H:%M:%S')})")
        response = SCRAPER.get(URL, headers=headers, timeout=30)
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code} hatası")
            return None
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Fiyat elementini bul
        fiyat_elementi = soup.find('span', class_='urunfiyati')
        
        if fiyat_elementi:
            fiyat = fiyat_elementi.get_text(strip=True)
            print(f"✅ Fiyat bulundu: {fiyat}")
            return fiyat
        else:
            print("❌ Fiyat elementi bulunamadı")
            # Debugging için sayfanın bir kısmını yazdır
            print(f"Sayfa içeriği (ilk 500 karakter): {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ Scraping hatası: {e}")
        return None

def arka_plan_kontrol():
    """Arka planda sürekli fiyat kontrolü (5 dakikada bir)"""
    global son_fiyat
    
    # Bot başladığında bildirim gönder
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        mesaj = f"""
🤖 <b>Fiyat Takip Botu Başladı!</b>

📦 <b>Ürün:</b> Roborock Robot Süpürge
📍 Takibe alındı
⏰ Her 5 dakikada bir kontrol edilecek

🔗 <a href="{URL}">Ürün Sayfası</a>

⏱️ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        """
        telegram_mesaj_gonder(mesaj.strip())
    
    # İlk fiyatı hemen çek
    ilk_fiyat = fiyat_al()
    if ilk_fiyat:
        son_fiyat = ilk_fiyat
        fiyat_gecmisi.append({
            'zaman': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'fiyat': ilk_fiyat,
            'degisim': False,
            'ilk_kayit': True
        })
        print(f"📌 İlk fiyat kaydedildi: {ilk_fiyat}")
    
    while True:
        try:
            # 5 dakika bekle
            time.sleep(300)  # 300 saniye = 5 dakika
            
            yeni_fiyat = fiyat_al()
            
            if yeni_fiyat:
                zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Fiyat değişimini kontrol et
                if son_fiyat and yeni_fiyat != son_fiyat:
                    print(f"🔔 FİYAT DEĞİŞTİ! {son_fiyat} → {yeni_fiyat}")
                    
                    # Telegram bildirimi gönder
                    mesaj = f"""
🔔 <b>FİYAT DEĞİŞİKLİĞİ TESPİT EDİLDİ!</b>

📦 <b>Ürün:</b> Roborock Robot Süpürge

💰 <b>Eski Fiyat:</b> {son_fiyat}
💰 <b>Yeni Fiyat:</b> {yeni_fiyat}

🔗 <a href="{URL}">Hemen İncele</a>

⏰ {zaman}
                    """
                    telegram_mesaj_gonder(mesaj.strip())
                    
                    # Geçmişe kaydet
                    fiyat_gecmisi.append({
                        'zaman': zaman,
                        'fiyat': yeni_fiyat,
                        'degisim': True,
                        'eski_fiyat': son_fiyat
                    })
                else:
                    print(f"✓ Fiyat aynı: {yeni_fiyat}")
                    fiyat_gecmisi.append({
                        'zaman': zaman,
                        'fiyat': yeni_fiyat,
                        'degisim': False
                    })
                
                son_fiyat = yeni_fiyat
                
                # Son 100 kaydı sakla (bellek yönetimi)
                if len(fiyat_gecmisi) > 100:
                    fiyat_gecmisi.pop(0)
                    
        except Exception as e:
            print(f"❌ Arka plan kontrol hatası: {e}")
            time.sleep(60)  # Hata durumunda 1 dakika bekle

# Flask Routes

@app.route('/')
def home():
    """Ana sayfa - Bot durumu"""
    telegram_aktif = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    calisma_suresi = datetime.now() - bot_baslama_zamani
    
    return jsonify({
        'status': '✅ Çalışıyor',
        'bot': 'Roborock Fiyat Takip Botu',
        'url': URL,
        'son_fiyat': son_fiyat,
        'kontrol_periyodu': '5 dakika',
        'telegram_bildirim': '✅ Aktif' if telegram_aktif else '❌ Pasif',
        'toplam_kontrol': len(fiyat_gecmisi),
        'calisma_suresi': str(calisma_suresi).split('.')[0],
        'baslangic_zamani': bot_baslama_zamani.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/fiyat')
def get_fiyat():
    """Anlık fiyat sorgulama (manuel)"""
    fiyat = fiyat_al()
    return jsonify({
        'fiyat': fiyat,
        'zaman': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'url': URL,
        'durum': 'başarılı' if fiyat else 'başarısız'
    })

@app.route('/gecmis')
def get_gecmis():
    """Fiyat geçmişini göster (son 20 kayıt)"""
    return jsonify({
        'toplam_kayit': len(fiyat_gecmisi),
        'son_20_kayit': fiyat_gecmisi[-20:][::-1],  # Tersine çevir (en yeni önce)
        'son_fiyat': son_fiyat
    })

@app.route('/test-telegram')
def test_telegram():
    """Telegram bildirimini test et"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return jsonify({
            'status': '❌ Hata',
            'mesaj': 'Telegram ayarları yapılmamış!',
            'telegram_token': 'ayarlı' if TELEGRAM_BOT_TOKEN else '❌ yok',
            'chat_id': 'ayarlı' if TELEGRAM_CHAT_ID else '❌ yok'
        }), 400
    
    test_mesaji = f"""
🧪 <b>Test Mesajı</b>

✅ Telegram bildirimleri başarıyla çalışıyor!

📱 Chat ID: {TELEGRAM_CHAT_ID}
🤖 Bot aktif ve hazır

⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    """
    
    sonuc = telegram_mesaj_gonder(test_mesaji.strip())
    
    return jsonify({
        'status': '✅ Başarılı' if sonuc else '❌ Başarısız',
        'telegram_token': '✅ Ayarlı',
        'chat_id': '✅ Ayarlı',
        'mesaj': 'Test mesajı gönderildi!' if sonuc else 'Mesaj gönderilemedi!'
    })

@app.route('/health')
def health():
    """Health check endpoint (Render için gerekli)"""
    return jsonify({
        'status': 'healthy',
        'uptime': str(datetime.now() - bot_baslama_zamani).split('.')[0]
    }), 200

@app.route('/istatistik')
def istatistik():
    """Detaylı istatistikler"""
    degisim_sayisi = sum(1 for k in fiyat_gecmisi if k.get('degisim', False))
    
    return jsonify({
        'toplam_kontrol': len(fiyat_gecmisi),
        'fiyat_degisim_sayisi': degisim_sayisi,
        'son_fiyat': son_fiyat,
        'calisma_suresi': str(datetime.now() - bot_baslama_zamani).split('.')[0],
        'telegram_aktif': bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    })

# Arka plan thread'ini başlat
kontrol_thread = threading.Thread(target=arka_plan_kontrol, daemon=True)
kontrol_thread.start()

# Gunicorn için gerekli
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
