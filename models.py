from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid
from config import FREE_TIER_LIMIT, PREMIUM_TIER_LIMIT, FREE_MONITOR_DURATION, PREMIUM_MONITOR_DURATION

class User:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.users
    
    async def get_user(self, user_id: int):
        return await self.collection.find_one({'user_id': user_id})
    
    async def create_user(self, user_id: int, username: str, first_name: str):
        existing = await self.get_user(user_id)
        if existing:
            return existing
        user = {
            'user_id': user_id, 'username': username, 'first_name': first_name,
            'is_premium': False, 'premium_expiry': None, 'premium_plan': None,
            'monitor_count': 0, 'referral_code': f"REF{user_id}",
            'referred_by': None, 'referral_earnings': 0,
            'joined_at': datetime.now(), 'last_active': datetime.now(), 'is_banned': False
        }
        await self.collection.insert_one(user)
        return user
    
    async def get_monitor_limit(self, user_id: int) -> int:
        user = await self.get_user(user_id)
        if not user or user.get('is_banned'): return 0
        if user.get('is_premium') and user.get('premium_expiry') and user['premium_expiry'] > datetime.now():
            return PREMIUM_TIER_LIMIT
        return FREE_TIER_LIMIT
    
    async def get_monitor_duration(self, user_id: int) -> int:
        user = await self.get_user(user_id)
        if user and user.get('is_premium') and user.get('premium_expiry') and user['premium_expiry'] > datetime.now():
            return PREMIUM_MONITOR_DURATION
        return FREE_MONITOR_DURATION
    
    async def set_premium(self, user_id: int, days: int, plan: str):
        await self.collection.update_one({'user_id': user_id}, {'$set': {
            'is_premium': True, 'premium_plan': plan,
            'premium_expiry': datetime.now() + timedelta(days=days)
        }})
    
    async def inc_monitors(self, user_id: int):
        await self.collection.update_one({'user_id': user_id}, {'$inc': {'monitor_count': 1}})
    
    async def dec_monitors(self, user_id: int):
        await self.collection.update_one({'user_id': user_id}, {'$inc': {'monitor_count': -1}})
    
    async def ban_user(self, user_id: int, ban: bool = True):
        await self.collection.update_one({'user_id': user_id}, {'$set': {'is_banned': ban}})
    
    async def get_all_users(self):
        return await self.collection.find({}).sort('joined_at', -1).to_list(None)
    
    async def get_stats(self):
        total = await self.collection.count_documents({})
        premium = await self.collection.count_documents({'is_premium': True, 'premium_expiry': {'$gt': datetime.now()}})
        banned = await self.collection.count_documents({'is_banned': True})
        return {'total_users': total, 'premium_users': premium, 'free_users': total - premium, 'banned_users': banned}

class Monitor:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.monitors
    
    async def create_monitor(self, user_id: int, url: str, name: str, interval: int):
        m = {
            'monitor_id': f"MON{uuid.uuid4().hex[:6].upper()}", 'user_id': user_id,
            'url': url, 'name': name, 'status': 'unknown',
            'check_interval': interval, 'uptime_percentage': 100.0,
            'total_checks': 0, 'successful_checks': 0, 'failed_checks': 0,
            'is_active': True, 'created_at': datetime.now(), 'last_checked': None
        }
        await self.collection.insert_one(m)
        return m
    
    async def check_duplicate(self, user_id: int, url: str):
        return await self.collection.find_one({'user_id': user_id, 'url': url, 'is_active': True})
    
    async def get_monitor(self, monitor_id: str):
        return await self.collection.find_one({'monitor_id': monitor_id})
    
    async def get_user_monitors(self, user_id: int):
        return await self.collection.find({'user_id': user_id, 'is_active': True}).sort('created_at', -1).to_list(None)
    
    async def get_all_monitors(self):
        return await self.collection.find({'is_active': True}).to_list(None)
    
    async def update_status(self, monitor_id: str, status: str, response_time: float = 0):
        m = await self.get_monitor(monitor_id)
        if not m: return
        total = m['total_checks'] + 1
        success = m['successful_checks'] + (1 if status == 'up' else 0)
        failed = m['failed_checks'] + (1 if status != 'up' else 0)
        uptime = (success / total * 100) if total > 0 else 100
        await self.collection.update_one({'monitor_id': monitor_id}, {'$set': {
            'status': status, 'uptime_percentage': round(uptime, 2),
            'total_checks': total, 'successful_checks': success,
            'failed_checks': failed, 'last_checked': datetime.now(),
            'last_response_time': response_time
        }})
    
    async def delete_monitor(self, monitor_id: str):
        await self.collection.delete_one({'monitor_id': monitor_id})
    
    async def toggle_monitor(self, monitor_id: str, active: bool):
        await self.collection.update_one({'monitor_id': monitor_id}, {'$set': {'is_active': active}})
    
    async def generate_file(self, user_id: int = None):
        query = {} if user_id is None else {'user_id': user_id}
        monitors = await self.collection.find(query).to_list(None)
        text = "=" * 40 + "\nMONITORS REPORT\n" + "=" * 40 + "\n\n"
        for m in monitors:
            text += f"Name: {m.get('name', 'N/A')}\nURL: {m['url']}\nStatus: {m['status']}\nUptime: {m['uptime_percentage']}%\nUser: {m['user_id']}\n{'-'*30}\n"
        return text

class PaymentSettings:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.payment_settings
    
    async def init_default(self):
        if not await self.collection.find_one({}):
            await self.collection.insert_one({
                'payment_methods': {
                    'upi': {'enabled': True, 'id': '', 'name': 'UPI'},
                    'paypal': {'enabled': False, 'email': '', 'name': 'PayPal'},
                    'crypto': {'enabled': False, 'wallets': {}, 'name': 'Crypto'},
                    'bank': {'enabled': False, 'details': {}, 'name': 'Bank Transfer'}
                },
                'plans': [
                    {'plan_id': 'monthly', 'name': '1 Month Premium', 'price': 99, 'currency': 'INR', 'duration_days': 30, 'active': True},
                    {'plan_id': '3months', 'name': '3 Months Premium', 'price': 249, 'currency': 'INR', 'duration_days': 90, 'active': True},
                    {'plan_id': 'lifetime', 'name': 'Lifetime Premium', 'price': 999, 'currency': 'INR', 'duration_days': 36500, 'active': True}
                ]
            })
    
    async def get_settings(self):
        return await self.collection.find_one({})
    
    async def get_plans(self):
        s = await self.get_settings()
        return [p for p in s['plans'] if p.get('active', True)] if s else []
    
    async def get_plan(self, plan_id: str):
        s = await self.get_settings()
        for p in s['plans']:
            if p['plan_id'] == plan_id: return p
        return None
    
    async def add_plan(self, data: dict):
        data['plan_id'] = str(uuid.uuid4())[:8]
        data.setdefault('active', True)
        await self.collection.update_one({}, {'$push': {'plans': data}})
        return data
    
    async def delete_plan(self, plan_id: str):
        await self.collection.update_one({}, {'$pull': {'plans': {'plan_id': plan_id}}})
    
    async def update_plan(self, plan_id: str, data: dict):
        for k, v in data.items():
            await self.collection.update_one({'plans.plan_id': plan_id}, {'$set': {f'plans.$.{k}': v}})
    
    async def update_method(self, method: str, data: dict):
        for k, v in data.items():
            await self.collection.update_one({}, {'$set': {f'payment_methods.{method}.{k}': v}})

class Payment:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.payments
    
    async def create(self, user_id, plan_id, amount, currency, method):
        p = {
            'payment_id': f"PAY{uuid.uuid4().hex[:6].upper()}", 'user_id': user_id,
            'plan_id': plan_id, 'amount': amount, 'currency': currency,
            'method': method, 'status': 'pending', 'screenshot_id': None,
            'created_at': datetime.now()
        }
        await self.collection.insert_one(p)
        return p
    
    async def get(self, payment_id):
        return await self.collection.find_one({'payment_id': payment_id})
    
    async def get_pending(self):
        return await self.collection.find({'status': 'pending'}).to_list(None)
    
    async def verify(self, payment_id, admin_id):
        await self.collection.update_one({'payment_id': payment_id}, {'$set': {
            'status': 'verified', 'verified_by': admin_id, 'verified_at': datetime.now()
        }})
    
    async def reject(self, payment_id, admin_id, reason):
        await self.collection.update_one({'payment_id': payment_id}, {'$set': {
            'status': 'rejected', 'verified_by': admin_id, 'reason': reason
        }})
    
    async def save_screenshot(self, payment_id, file_id):
        await self.collection.update_one({'payment_id': payment_id}, {'$set': {'screenshot_id': file_id}})

class ForceJoin:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.force_join
    
    async def init_default(self):
        if not await self.collection.find_one({}):
            await self.collection.insert_one({'channels': [], 'enabled': False})
    
    async def get_settings(self):
        return await self.collection.find_one({})
    
    async def add_channel(self, data: dict):
        exist = await self.collection.find_one({'channels.id': data['id']})
        if exist: return False
        await self.collection.update_one({}, {'$push': {'channels': data}})
        return True
    
    async def remove_channel(self, channel_id: int):
        await self.collection.update_one({}, {'$pull': {'channels': {'id': channel_id}}})
    
    async def toggle(self, enabled: bool):
        await self.collection.update_one({}, {'$set': {'enabled': enabled}})
    
    async def check_joined(self, user_id: int, context):
        s = await self.get_settings()
        if not s or not s.get('enabled'): return True, []
        not_joined = []
        for ch in s.get('channels', []):
            try:
                member = await context.bot.get_chat_member(ch['id'], user_id)
                if member.status in ['left', 'kicked', 'banned']:
                    not_joined.append(ch)
            except: continue
        return len(not_joined) == 0, not_joined
