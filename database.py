from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
from config import MONGODB_URI, FREE_TIER_LIMIT, PREMIUM_TIER_LIMIT, FREE_MONITOR_DURATION, PREMIUM_MONITOR_DURATION

class Database:
    def __init__(self):
        self.client = None
        self.db = None
    
    async def connect(self):
        self.client = AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client.uptimebot
        await self.client.admin.command('ping')
        await self.init_defaults()
        print("✅ Database Connected!")
    
    async def init_defaults(self):
        if not await self.db.payment_settings.find_one({}):
            await self.db.payment_settings.insert_one({
                'payment_methods': {
                    'upi': {'enabled': True, 'id': '', 'name': 'UPI'},
                    'paypal': {'enabled': False, 'email': '', 'name': 'PayPal'},
                    'bank': {'enabled': False, 'details': {}, 'name': 'Bank Transfer'}
                },
                'plans': [
                    {'plan_id': 'monthly', 'name': '1 Month', 'price': 99, 'currency': 'INR', 'duration_days': 30, 'monitor_limit': 20, 'check_interval': 1, 'active': True},
                    {'plan_id': 'lifetime', 'name': 'Lifetime', 'price': 999, 'currency': 'INR', 'duration_days': 36500, 'monitor_limit': 50, 'check_interval': 1, 'active': True}
                ],
                'contact': {'username': '@SonuPorsa', 'url': 'https://t.me/SonuPorsa', 'text': '📞 Contact Admin'}
            })
        if not await self.db.force_join.find_one({}):
            await self.db.force_join.insert_one({'channels': [], 'enabled': False})
    
    # ========== USER ==========
    async def get_user(self, user_id):
        return await self.db.users.find_one({'user_id': user_id})
    
    async def create_user(self, user_id, username, first_name):
        if not await self.get_user(user_id):
            await self.db.users.insert_one({
                'user_id': user_id, 'username': username, 'first_name': first_name,
                'is_premium': False, 'premium_expiry': None,
                'custom_monitor_limit': 0, 'custom_check_interval': 0,
                'monitor_count': 0, 'referral_code': f"REF{user_id}",
                'is_banned': False, 'joined_at': datetime.now()
            })
    
    async def get_monitor_limit(self, user_id):
        user = await self.get_user(user_id)
        if not user or user.get('is_banned'): return 0
        if user.get('custom_monitor_limit', 0) > 0: return user['custom_monitor_limit']
        if user.get('is_premium') and user.get('premium_expiry') and user['premium_expiry'] > datetime.now():
            return PREMIUM_TIER_LIMIT
        return FREE_TIER_LIMIT
    
    async def get_monitor_duration(self, user_id):
        user = await self.get_user(user_id)
        if user.get('custom_check_interval', 0) > 0: return user['custom_check_interval']
        if user and user.get('is_premium') and user.get('premium_expiry') and user['premium_expiry'] > datetime.now():
            return PREMIUM_MONITOR_DURATION
        return FREE_MONITOR_DURATION
    
    async def set_premium(self, user_id, days, plan="Admin", limit=0, interval=0):
        data = {'is_premium': True, 'premium_expiry': datetime.now() + timedelta(days=days), 'premium_plan': plan}
        if limit > 0: data['custom_monitor_limit'] = limit
        if interval > 0: data['custom_check_interval'] = interval
        await self.db.users.update_one({'user_id': user_id}, {'$set': data})
    
    async def remove_premium(self, user_id):
        await self.db.users.update_one({'user_id': user_id}, {'$set': {'is_premium': False, 'custom_monitor_limit': 0, 'custom_check_interval': 0}})
    
    async def inc_monitors(self, user_id): await self.db.users.update_one({'user_id': user_id}, {'$inc': {'monitor_count': 1}})
    async def dec_monitors(self, user_id): await self.db.users.update_one({'user_id': user_id}, {'$inc': {'monitor_count': -1}})
    async def ban_user(self, user_id, ban=True): await self.db.users.update_one({'user_id': user_id}, {'$set': {'is_banned': ban}})
    async def get_all_users(self): return await self.db.users.find({}).to_list(None)
    
    async def get_stats(self):
        total = await self.db.users.count_documents({})
        premium = await self.db.users.count_documents({'is_premium': True, 'premium_expiry': {'$gt': datetime.now()}})
        banned = await self.db.users.count_documents({'is_banned': True})
        return {'total_users': total, 'premium_users': premium, 'free_users': total - premium, 'banned_users': banned}
    
    # ========== MONITOR ==========
    async def create_monitor(self, user_id, url, name, interval):
        m = {'monitor_id': f"MON{uuid.uuid4().hex[:6].upper()}", 'user_id': user_id, 'url': url, 'name': name, 'status': 'unknown', 'check_interval': interval, 'uptime_percentage': 100.0, 'total_checks': 0, 'successful_checks': 0, 'failed_checks': 0, 'is_active': True, 'created_at': datetime.now()}
        await self.db.monitors.insert_one(m)
        return m
    
    async def check_duplicate(self, user_id, url): return await self.db.monitors.find_one({'user_id': user_id, 'url': url, 'is_active': True})
    async def get_monitor(self, mid): return await self.db.monitors.find_one({'monitor_id': mid})
    async def get_user_monitors(self, user_id): return await self.db.monitors.find({'user_id': user_id, 'is_active': True}).to_list(None)
    async def get_all_active_monitors(self): return await self.db.monitors.find({'is_active': True}).to_list(None)
    
    async def update_monitor_status(self, mid, status, time=0):
        m = await self.get_monitor(mid)
        if not m: return
        total = m['total_checks'] + 1
        success = m['successful_checks'] + (1 if status == 'up' else 0)
        failed = m['failed_checks'] + (1 if status != 'up' else 0)
        uptime = (success / total * 100) if total > 0 else 100
        await self.db.monitors.update_one({'monitor_id': mid}, {'$set': {'status': status, 'uptime_percentage': round(uptime, 2), 'total_checks': total, 'successful_checks': success, 'failed_checks': failed, 'last_checked': datetime.now()}})
    
    async def delete_monitor(self, mid): await self.db.monitors.delete_one({'monitor_id': mid})
    async def toggle_monitor(self, mid, active): await self.db.monitors.update_one({'monitor_id': mid}, {'$set': {'is_active': active}})
    
    async def generate_file(self, user_id=None):
        query = {} if user_id is None else {'user_id': user_id}
        monitors = await self.db.monitors.find(query).to_list(None)
        text = "="*40 + "\nMONITORS REPORT\n" + "="*40 + "\n\n"
        for m in monitors: text += f"Name: {m.get('name')}\nURL: {m['url']}\nStatus: {m['status']}\nUptime: {m['uptime_percentage']}%\nUser: {m['user_id']}\n{'-'*30}\n"
        return text
    
    # ========== CONTACT ==========
    async def get_contact(self):
        s = await self.db.payment_settings.find_one({})
        return s.get('contact', {'username': '@SonuPorsa', 'url': 'https://t.me/SonuPorsa', 'text': '📞 Contact'}) if s else {}
    
    async def update_contact(self, data):
        for k, v in data.items(): await self.db.payment_settings.update_one({}, {'$set': {f'contact.{k}': v}})
    
    # ========== PAYMENTS ==========
    async def get_settings(self): return await self.db.payment_settings.find_one({})
    async def get_plans(self):
        s = await self.get_settings()
        return [p for p in s['plans'] if p.get('active', True)] if s else []
    
    async def get_plan(self, pid):
        s = await self.get_settings()
        for p in s['plans']:
            if p['plan_id'] == pid: return p
        return None
    
    async def add_plan(self, data):
        data['plan_id'] = str(uuid.uuid4())[:8]
        data.setdefault('active', True)
        await self.db.payment_settings.update_one({}, {'$push': {'plans': data}})
        return data
    
    async def update_plan(self, pid, data):
        for k, v in data.items(): await self.db.payment_settings.update_one({'plans.plan_id': pid}, {'$set': {f'plans.$.{k}': v}})
    
    async def delete_plan(self, pid): await self.db.payment_settings.update_one({}, {'$pull': {'plans': {'plan_id': pid}}})
    
    async def update_payment_method(self, method, data):
        for k, v in data.items(): await self.db.payment_settings.update_one({}, {'$set': {f'payment_methods.{method}.{k}': v}})
    
    async def create_payment(self, user_id, plan_id, amount, currency, method):
        p = {'payment_id': f"PAY{uuid.uuid4().hex[:6].upper()}", 'user_id': user_id, 'plan_id': plan_id, 'amount': amount, 'currency': currency, 'method': method, 'status': 'pending', 'screenshot_id': None, 'created_at': datetime.now()}
        await self.db.payments.insert_one(p)
        return p
    
    async def get_payment(self, pid): return await self.db.payments.find_one({'payment_id': pid})
    async def get_pending_payments(self): return await self.db.payments.find({'status': 'pending'}).to_list(None)
    
    async def verify_payment(self, pid, aid):
        await self.db.payments.update_one({'payment_id': pid}, {'$set': {'status': 'verified', 'verified_by': aid, 'verified_at': datetime.now()}})
    
    async def reject_payment(self, pid, aid, reason):
        await self.db.payments.update_one({'payment_id': pid}, {'$set': {'status': 'rejected', 'verified_by': aid, 'reason': reason}})
    
    async def save_screenshot(self, pid, fid):
        await self.db.payments.update_one({'payment_id': pid}, {'$set': {'screenshot_id': fid}})
    
    # ========== FORCE JOIN ==========
    async def get_fj_settings(self): return await self.db.force_join.find_one({})
    
    async def add_fj_channel(self, data):
        if await self.db.force_join.find_one({'channels.id': data['id']}): return False
        await self.db.force_join.update_one({}, {'$push': {'channels': data}})
        return True
    
    async def remove_fj_channel(self, cid): await self.db.force_join.update_one({}, {'$pull': {'channels': {'id': cid}}})
    async def toggle_fj(self, enabled): await self.db.force_join.update_one({}, {'$set': {'enabled': enabled}})
