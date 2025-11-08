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

URL = "https://www.epey.com/robot-supurge/karsilastir/918677-986565/roborock-s8-maxv-ultra_roborock-saros-10/farklari/"
SELECTOR = "span.urunfiyati"

# Fiyat geçmişi (bellekte sakla)
fiyat_gecmisi = []
son_fiyat = None

def fiyat_al():
    """Cloudscraper ile fiyat çekme (Cloudflare bypass)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9',
            'Referer': 'https://www.google.com/'
        }
        
        print(f"🔄 Fiyat çekiliyor...")
        
        # Cloudscraper ile istek at
        response = SCRAPER.get(URL, headers=headers, timeout=30)
        
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code} hatası")
            return None
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # span.urunfiyati bul
        fiyat_elementi = soup.find('span', class_='urunfiyati')
        
        if fiyat_elementi:
            fiyat = fiyat_elementi.get_text(strip=True)
            print(f"✅ Fiyat bulundu: {fiyat}")
            return fiyat
        else:
            print("❌ Fiyat elementi bulunamadı")
            return None
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        return None
```

**Kaydet (Save)**

---

## 🚀 ADIM 3: Yeniden Deploy Et

**Render dashboard'da:**

1. Sağ üstte **"Manual Deploy"** butonunu bul
2. Dropdown'dan **"Deploy latest commit"** seç
3. **Bekle** - 2-3 dakika sürer

**Ekranda göreceksin:**
```
==> Building...
==> Installing dependencies from requirements.txt
==> Successfully installed cloudscraper-1.2.71
==> Starting service...
```

---

## 📊 ADIM 4: Logları Kontrol Et

Deploy bitince:

1. **"Logs"** sekmesine tıkla
2. **5 dakika bekle** (ilk fiyat kontrolü için)
3. Şöyle bir şey göreceksin:

**✅ BAŞARILI:**
```
🔄 Fiyat çekiliyor...
📡 Status Code: 200
✅ Fiyat bulundu: 51.485,73 TL
📦 Şu anki fiyat: 51.485,73 TL
```

**❌ BAŞARISIZ:**
```
📡 Status Code: 403
❌ HTTP 403 hatası
```

---

## 🧪 ADIM 5: Test Et

Tarayıcıda şu adresi aç:
```
https://your-app-name.onrender.com/fiyat
def arka_plan_kontrol():
    """Arka planda sürekli fiyat kontrolü"""
    global son_fiyat
    
    while True:
        try:
            yeni_fiyat = fiyat_al()
            
            if yeni_fiyat:
                zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if son_fiyat and yeni_fiyat != son_fiyat:
                    print(f"⚠️ Fiyat değişti! {son_fiyat} → {yeni_fiyat}")
                    fiyat_gecmisi.append({
                        'zaman': zaman,
                        'fiyat': yeni_fiyat,
                        'degisim': True
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
        
        # 5 dakika bekle (300 saniye)
        time.sleep(300)

@app.route('/')
def home():
    return jsonify({
        'status': 'çalışıyor',
        'bot': 'Fiyat Takip Botu',
        'url': URL,
        'son_fiyat': son_fiyat,
        'kontrol_periyodu': '5 dakika'
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
        'gecmis': fiyat_gecmisi[-20:]  # Son 20 kayıt
    })

@app.route('/health')
def health():
    """Render için health check"""
    return jsonify({'status': 'healthy'}), 200

    # Arka plan thread'ini başlat
    thread = threading.Thread(target=arka_plan_kontrol, daemon=True)
    thread.start()
    
    # Flask uygulamasını başlat
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
