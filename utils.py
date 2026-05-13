import aiohttp
import asyncio
import ssl
import qrcode
import io
import time

async def check_website(url: str, timeout: int = 10):
    try:
        start = time.time()
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
            async with session.get(url, allow_redirects=True) as response:
                response_time = round((time.time() - start) * 1000, 2)
                if 200 <= response.status < 400:
                    return {'status': 'up', 'time': response_time, 'code': response.status}
                else:
                    return {'status': 'down', 'time': response_time, 'code': response.status}
    except asyncio.TimeoutError:
        return {'status': 'down', 'time': 0, 'error': 'Timeout'}
    except Exception as e:
        return {'status': 'down', 'time': 0, 'error': str(e)}

def generate_qr(upi_id: str, amount: float):
    try:
        upi_uri = f"upi://pay?pa={upi_id}&pn=UptimeBot&am={amount}&cu=INR"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(upi_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        bio.name = 'qr.png'
        return bio
    except:
        return None

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

class Scheduler:
    def __init__(self, db, bot):
        self.scheduler = AsyncIOScheduler()
        self.db = db
        self.bot = bot
        from models import Monitor
        self.Monitor = Monitor(db)
    
    def start(self):
        self.scheduler.add_job(self.check_all, 'interval', seconds=60, id='monitor_checker')
        self.scheduler.start()
    
    async def check_all(self):
        try:
            monitors = await self.Monitor.get_all_monitors()
            for m in monitors:
                try:
                    if m.get('last_checked'):
                        diff = (datetime.now() - m['last_checked']).total_seconds()
                        if diff < m['check_interval'] * 60:
                            continue
                    
                    result = await check_website(m['url'])
                    old = m['status']
                    new = result['status']
                    
                    await self.Monitor.update_status(m['monitor_id'], new, result.get('time', 0))
                    
                    if old != new:
                        emoji = "🟢" if new == 'up' else "🔴"
                        await self.bot.send_message(
                            m['user_id'],
                            f"{emoji} {m['name']}\n{new.upper()}\n{m['url']}"
                        )
                    
                    await asyncio.sleep(0.1)
                except:
                    continue
        except:
            pass
