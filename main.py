import asyncio
from playwright.async_api import async_playwright
import time

URL = "https://www.epey.com/robot-supurge/karsilastir/918677-986565/roborock-s8-maxv-ultra_roborock-saros-10/farklari/"
SELECTOR = "span.urunfiyati"

async def fiyat_kontrol():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        sayfa = await browser.new_page()
        await sayfa.goto(URL, timeout=60000)

        # Cloudflare'ı atlatmak için basit insan davranışı simülasyonu
        await sayfa.wait_for_timeout(5000)
        await sayfa.mouse.move(200, 300)
        await sayfa.mouse.wheel(0, 500)
        await sayfa.wait_for_timeout(2000)
        await sayfa.mouse.click(400, 250)
        await sayfa.wait_for_timeout(3000)

        print("📄 Sayfa başlığı:", await sayfa.title())

        try:
            fiyat = await sayfa.inner_text(SELECTOR)
            print(f"💰 Güncel fiyat: {fiyat}")
        except Exception as e:
            print("⚠️ Fiyat alınamadı:", e)
        await browser.close()

if __name__ == "__main__":
    while True:
        asyncio.run(fiyat_kontrol())
        time.sleep(600)  # 10 dakikada bir kontrol
