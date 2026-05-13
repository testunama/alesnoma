import aiohttp, asyncio, ssl, time, qrcode, io

async def check_website(url, timeout=10):
    try:
        start = time.time()
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url, allow_redirects=True) as resp:
                t = round((time.time() - start) * 1000, 2)
                return {'status': 'up' if 200 <= resp.status < 400 else 'down', 'time': t}
    except: return {'status': 'down', 'time': 0}

def generate_qr(upi_id, amount):
    try:
        uri = f"upi://pay?pa={upi_id}&pn=UptimeBot&am={amount}&cu=INR"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        bio.name = 'qr.png'
        return bio
    except: return None

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

class Scheduler:
    def __init__(self, db, client):
        self.scheduler = AsyncIOScheduler()
        self.db = db
        self.client = client
    
    def start(self):
        self.scheduler.add_job(self.check_all, 'interval', seconds=60)
        self.scheduler.start()
    
    async def check_all(self):
        try:
            monitors = await self.db.get_all_active_monitors()
            for m in monitors:
                try:
                    if m.get('last_checked') and (datetime.now() - m['last_checked']).total_seconds() < m['check_interval'] * 60:
                        continue
                    r = await check_website(m['url'])
                    old = m['status']
                    await self.db.update_monitor_status(m['monitor_id'], r['status'], r.get('time', 0))
                    if old != r['status']:
                        try: await self.client.send_message(m['user_id'], f"{'🟢' if r['status']=='up' else '🔴'} {m['name']}\n{r['status'].upper()}")
                        except: pass
                except: continue
        except: pass
