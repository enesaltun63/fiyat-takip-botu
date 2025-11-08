from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import threading
import time

app = Flask(__name__)

URL = "https://www.epey.com/robot-supurge/karsilastir/918677-986565/roborock-s8-maxv-ultra_roborock-saros-10/farklari/"
SELECTOR = "span.urunfiyati"

# Fiyat geçmişi (bellekte sakla)
fiyat_gecmisi = []
son_fiyat = None

def fiyat_al():
    """BeautifulSoup ile fiyat çekme"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        session = requests.Session()
        response = session.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Fiyat elementini bul
        fiyat_elementi = soup.select_one(SELECTOR)
        
        if fiyat_elementi:
            fiyat = fiyat_elementi.get_text(strip=True)
            return fiyat
        else:
            return None
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        return None

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

if __name__ == '__main__':
    # Arka plan thread'ini başlat
    thread = threading.Thread(target=arka_plan_kontrol, daemon=True)
    thread.start()
    
    # Flask uygulamasını başlat
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
