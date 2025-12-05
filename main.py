#!/usr/bin/env python3
import os, io, json, datetime, logging, re, random, csv, statistics
from functools import wraps
from PIL import Image
import imagehash
import numpy as np
from collections import defaultdict
import pandas as pd
from pathlib import Path

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

# ===================== CONFIG =====================
BOT_TOKEN = "8289248912:AAHzvO7ZKMkTWJGgF2Q2s5q08S_9II6xwB8" 
ADMIN_IDS = [5641197226]  # Admin ID larini qo'ying

DATA_DIR = "data"
USERS_DIR = f"{DATA_DIR}/users"
IMAGES_DIR = f"{DATA_DIR}/images"
ANALYSES_DIR = f"{DATA_DIR}/analyses"
CONVERSATIONS_DIR = f"{DATA_DIR}/conversations"
STATS_DIR = f"{DATA_DIR}/stats"
PRODUCTS_FILE = f"{DATA_DIR}/products.json"
ADMIN_LOG_FILE = f"{DATA_DIR}/admin_log.json"

# Direktoriyalarni yaratish
for dir_path in [DATA_DIR, USERS_DIR, IMAGES_DIR, ANALYSES_DIR, 
                 CONVERSATIONS_DIR, STATS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ===================== LOG =====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== EMOJI =====================
EMOJI = {
    "welcome": "🌸", "skin": "🧴", "photo": "📸", "analysis": "🔍",
    "calendar": "📅", "heart": "💖", "sparkle": "✨", "routine": "🌙",
    "warning": "⚠️", "success": "✅", "info": "ℹ️", "flower": "🌺",
    "lipstick": "💄", "mirror": "🪞", "star": "⭐", "doctor": "👩‍⚕️",
    "water": "💧", "sun": "☀️", "moon": "🌙", "pill": "💊",
    "admin": "👑", "stats": "📊", "users": "👥", "bell": "🔔",
    "product": "🧴", "chart": "📈", "lock": "🔒", "unlock": "🔓",
    "export": "📤", "import": "📥", "trash": "🗑️", "edit": "✏️",
    "search": "🔍", "filter": "⚙️", "download": "💾", "upload": "📁"
}

# ===================== PRODUCT DATABASE =====================
DEFAULT_PRODUCTS = {
    "cleansers": [
        {"name": "CeraVe Hydrating Facial Cleanser", "brand": "CeraVe", 
         "skin_types": ["Quruq", "Hassas", "Normal"], "price": "$",
         "description": "Yumshoq tozalagich, teri pH balansini saqlaydi"},
        {"name": "La Roche-Posay Effaclar Gel", "brand": "La Roche-Posay",
         "skin_types": ["Yog'li", "Aralash", "Aknega moyil"], "price": "$$",
         "description": "Yog'li teri uchun tozalagich"},
        {"name": "Cetaphil Gentle Skin Cleanser", "brand": "Cetaphil",
         "skin_types": ["Hassas", "Quruq", "Normal"], "price": "$",
         "description": "Hassas teri uchun yumshoq tozalagich"}
    ],
    "moisturizers": [
        {"name": "Neutrogena Hydro Boost Water Gel", "brand": "Neutrogena",
         "skin_types": ["Quruq", "Aralash", "Normal"], "price": "$$",
         "description": "Suvsiz teri uchun gel krem"},
        {"name": "The Ordinary Natural Moisturizing Factors", "brand": "The Ordinary",
         "skin_types": ["Barcha turlar"], "price": "$",
         "description": "Tabiiy namlovchi omillar"},
        {"name": "Kiehl's Ultra Facial Cream", "brand": "Kiehl's",
         "skin_types": ["Quruq", "Normal"], "price": "$$$",
         "description": "24 soatlik namlovchi krem"}
    ],
    "sunscreens": [
        {"name": "La Roche-Posay Anthelios SPF 50", "brand": "La Roche-Posay",
         "skin_types": ["Barcha turlar"], "price": "$$",
         "description": "Keng spektrli quyoshdan himoya"},
        {"name": "Biore UV Aqua Rich Watery Essence SPF 50", "brand": "Biore",
         "skin_types": ["Yog'li", "Aralash"], "price": "$",
         "description": "Suvli tekstura, yog'siz"},
        {"name": "Supergoop! Unseen Sunscreen SPF 40", "brand": "Supergoop!",
         "skin_types": ["Barcha turlar"], "price": "$$$",
         "description": "Ko'rinmaydigan quyoshdan himoya"}
    ],
    "serums": [
        {"name": "The Ordinary Niacinamide 10% + Zinc 1%", "brand": "The Ordinary",
         "skin_types": ["Yog'li", "Aralash", "Aknega moyil"], "price": "$",
         "description": "Yog'li teri va dog'lar uchun"},
        {"name": "Skinceuticals C E Ferulic", "brand": "Skinceuticals",
         "skin_types": ["Barcha turlar"], "price": "$$$$",
         "description": "Antioxidant serum"},
        {"name": "Paula's Choice 2% BHA Liquid Exfoliant", "brand": "Paula's Choice",
         "skin_types": ["Yog'li", "Aralash", "Aknega moyil"], "price": "$$",
         "description": "Kimyaviy eksfoliator"}
    ]
}

# ===================== JSON HELPERS =====================
def save_json(data, filepath):
    """JSON faylga saqlash"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON: {e}")
        return False

def load_json(filepath, default=None):
    """JSON fayldan yuklash"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON: {e}")
    return default if default is not None else {}

def init_products_db():
    """Mahsulotlar bazasini ishga tushirish"""
    if not os.path.exists(PRODUCTS_FILE):
        save_json(DEFAULT_PRODUCTS, PRODUCTS_FILE)

def get_products():
    """Mahsulotlarni olish"""
    return load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)

def save_product(category, product_data):
    """Mahsulot qo'shish"""
    products = get_products()
    if category not in products:
        products[category] = []
    products[category].append(product_data)
    save_json(products, PRODUCTS_FILE)
    return True

# ===================== USER MANAGEMENT =====================
def get_user_filepath(user_id):
    return f"{USERS_DIR}/{user_id}.json"

def save_user(user_id, user_data):
    filepath = get_user_filepath(user_id)
    existing_data = load_json(filepath, {})
    existing_data.update(user_data)
    existing_data['last_active'] = datetime.datetime.now().isoformat()
    if 'created' not in existing_data:
        existing_data['created'] = datetime.datetime.now().isoformat()
    return save_json(existing_data, filepath)

def get_user(user_id):
    return load_json(get_user_filepath(user_id), {})

def update_user(user_id, updates):
    user_data = get_user(user_id)
    user_data.update(updates)
    user_data['last_active'] = datetime.datetime.now().isoformat()
    return save_user(user_id, user_data)

def get_all_users():
    """Barcha foydalanuvchilarni olish"""
    users = []
    if os.path.exists(USERS_DIR):
        for filename in os.listdir(USERS_DIR):
            if filename.endswith('.json'):
                try:
                    user_id = int(filename.split('.')[0])
                    user_data = get_user(user_id)
                    if user_data:
                        user_data['user_id'] = user_id
                        users.append(user_data)
                except:
                    continue
    return users

# ===================== ADMIN FUNCTIONS =====================
def is_admin(user_id):
    """Adminlikni tekshirish"""
    return user_id in ADMIN_IDS

def log_admin_action(admin_id, action, details=""):
    """Admin harakatlarini log qilish"""
    log_file = ADMIN_LOG_FILE
    logs = load_json(log_file, [])
    
    log_entry = {
        'admin_id': admin_id,
        'action': action,
        'details': details,
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    logs.append(log_entry)
    if len(logs) > 1000:  # Faqat so'nggi 1000 ta harakat
        logs = logs[-1000:]
    
    save_json(logs, log_file)
    return True

def get_admin_stats():
    """Admin statistikasi"""
    stats = {
        'total_users': 0,
        'active_today': 0,
        'total_analyses': 0,
        'skin_type_distribution': defaultdict(int),
        'avg_score': 0,
        'users_by_gender': defaultdict(int)
    }
    
    users = get_all_users()
    stats['total_users'] = len(users)
    
    today = datetime.datetime.now().date()
    analyses_count = 0
    total_score = 0
    score_count = 0
    
    for user in users:
        # Bugun faol bo'lganlar
        last_active = user.get('last_active', '')
        if last_active:
            try:
                last_active_date = datetime.datetime.fromisoformat(last_active).date()
                if last_active_date == today:
                    stats['active_today'] += 1
            except:
                pass
        
        # Jins bo'yicha
        gender = user.get('gender', 'aniqlanmadi')
        stats['users_by_gender'][gender] += 1
        
        # Teri turi bo'yicha
        skin_type = user.get('skin_type', 'aniqlanmadi')
        stats['skin_type_distribution'][skin_type] += 1
        
        # Tahlillar soni
        analyses = get_user_analyses(user['user_id'])
        analyses_count += len(analyses)
        
        # O'rtacha ball
        for analysis in analyses:
            total_score += analysis.get('analysis', {}).get('score', 0)
            score_count += 1
    
    stats['total_analyses'] = analyses_count
    if score_count > 0:
        stats['avg_score'] = round(total_score / score_count, 2)
    
    return stats

def export_users_csv():
    """Foydalanuvchilarni CSV ga eksport qilish"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{STATS_DIR}/users_export_{timestamp}.csv"
        
        users = get_all_users()
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['user_id', 'username', 'first_name', 'last_name', 
                         'age', 'gender', 'skin_type', 'created', 'last_active',
                         'analyses_count']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for user in users:
                user_id = user.get('user_id')
                analyses_count = len(get_user_analyses(user_id))
                
                writer.writerow({
                    'user_id': user_id,
                    'username': user.get('username', ''),
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'age': user.get('age', ''),
                    'gender': user.get('gender', ''),
                    'skin_type': user.get('skin_type', ''),
                    'created': user.get('created', ''),
                    'last_active': user.get('last_active', ''),
                    'analyses_count': analyses_count
                })
        
        return filename
    except Exception as e:
        logger.error(f"Export error: {e}")
        return None

# ===================== STATISTICS FUNCTIONS =====================
def update_global_stats():
    """Global statistikani yangilash"""
    try:
        stats_file = f"{STATS_DIR}/global_stats.json"
        stats = get_admin_stats()
        
        # Kunlik statistikani saqlash
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        daily_file = f"{STATS_DIR}/daily/{today}.json"
        os.makedirs(os.path.dirname(daily_file), exist_ok=True)
        save_json(stats, daily_file)
        
        # Umumiy statistikani yangilash
        all_stats = load_json(stats_file, {})
        all_stats['last_updated'] = datetime.datetime.now().isoformat()
        all_stats['total_users_history'] = all_stats.get('total_users_history', [])
        all_stats['total_users_history'].append({
            'date': today,
            'count': stats['total_users']
        })
        
        # Faqat so'nggi 90 kun
        if len(all_stats['total_users_history']) > 90:
            all_stats['total_users_history'] = all_stats['total_users_history'][-90:]
        
        save_json(all_stats, stats_file)
        return True
    except Exception as e:
        logger.error(f"Stats update error: {e}")
        return False

def get_skin_statistics():
    """Teri holati bo'yicha statistikalar"""
    stats = {
        'skin_types': defaultdict(int),
        'concerns': defaultdict(int),
        'score_distribution': defaultdict(int),
        'age_groups': defaultdict(int)
    }
    
    users = get_all_users()
    
    for user in users:
        # Teri turi
        skin_type = user.get('skin_type', 'aniqlanmadi')
        stats['skin_types'][skin_type] += 1
        
        # Yosh guruhlari
        age = user.get('age', 0)
        if age:
            if age < 18:
                stats['age_groups']['<18'] += 1
            elif age < 25:
                stats['age_groups']['18-24'] += 1
            elif age < 35:
                stats['age_groups']['25-34'] += 1
            elif age < 45:
                stats['age_groups']['35-44'] += 1
            else:
                stats['age_groups']['45+'] += 1
        
        # Foydalanuvchining tahlillari
        analyses = get_user_analyses(user.get('user_id'))
        for analysis_data in analyses:
            analysis = analysis_data.get('analysis', {})
            if analysis:
                # Ballar taqsimoti
                score = analysis.get('score', 0)
                score_group = (score // 10) * 10
                stats['score_distribution'][f"{score_group}-{score_group+9}"] += 1
                
                # Muammolar
                concerns = analysis.get('skin_concerns', '')
                if concerns:
                    stats['concerns'][concerns] += 1
    
    return stats

# ===================== REAL AI INTEGRATION (Mock) =====================
class SkinAI:
    """Real AI integratsiyasi uchun mock klass"""
    
    def __init__(self):
        self.model_loaded = False
        self.load_model()
    
    def load_model(self):
        """Modelni yuklash (mock)"""
        logger.info("AI model loaded (mock)")
        self.model_loaded = True
        self.skin_labels = ["Normal", "Quruq", "Yog'li", "Aralash", "Hassas", "Aknega moyil"]
        self.concern_labels = ["Akne", "Qorayish", "Chiziqlar", "Qurshash", "Quruqlik", "Tomirlar"]
        
    def analyze_image(self, img_path):
        """Rasmni tahlil qilish"""
        try:
            img = Image.open(img_path)
            
            # Haqiqiy AI model qo'shishingiz mumkin
            # Hozircha mock tahlil
            img_array = np.array(img)
            height, width, channels = img_array.shape
            
            # Rasm xususiyatlaridan "tahlil" qilish
            brightness = np.mean(img_array)
            contrast = np.std(img_array)
            
            # Tasodifiy natijalar (real loyihada AI model natijalari)
            random.seed(int(brightness + contrast))
            
            # Teri turini aniqlash
            skin_type_idx = random.randint(0, len(self.skin_labels)-1)
            skin_type = self.skin_labels[skin_type_idx]
            
            # Muammolarni aniqlash
            concerns_idx = random.randint(0, len(self.concern_labels)-1)
            concerns = self.concern_labels[concerns_idx]
            
            # Ball (0-100)
            score = 50 + random.randint(0, 50)
            
            # Tafsilotli tahlil
            analysis_details = {
                'brightness_level': round(brightness, 2),
                'contrast_level': round(contrast, 2),
                'image_resolution': f"{width}x{height}",
                'detected_features': random.randint(3, 8),
                'confidence_score': round(random.uniform(0.7, 0.95), 2)
            }
            
            # Tavsiyalar
            recommendations = self.get_recommendations(skin_type, concerns, score)
            
            return {
                'score': score,
                'skin_type': skin_type,
                'skin_concerns': concerns,
                'analysis_details': analysis_details,
                'recommendations': recommendations,
                'ai_model': 'DermAI v1.0',
                'confidence': analysis_details['confidence_score'],
                'timestamp': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return self.get_fallback_analysis()
    
    def get_recommendations(self, skin_type, concerns, score):
        """Shaxsiylashtirilgan tavsiyalar"""
        # Asosiy parvarish
        routines = {
            'morning': [
                "Yumshoq tozalagich",
                "Vitamin C serum",
                "Namlovchi krem SPF 30+"
            ],
            'evening': [
                "Makyajni tozalagich",
                "AHA/BHA yoki Retinol",
                "Namlovchi tungi krem"
            ]
        }
        
        # Teri turiga qoshimcha
        if skin_type == "Quruq":
            routines['morning'].append("Hyaluronic acid serum")
            routines['evening'].append("Yog'li krem")
        elif skin_type == "Yog'li":
            routines['morning'].append("Niacinamide serum")
            routines['evening'].append("Yog'siz gel krem")
        
        # Mahsulot tavsiyalari
        products = get_products()
        product_recommendations = []
        
        for category, product_list in products.items():
            for product in product_list:
                if skin_type in product['skin_types'] or "Barcha turlar" in product['skin_types']:
                    product_recommendations.append({
                        'category': category,
                        'name': product['name'],
                        'brand': product['brand'],
                        'description': product['description']
                    })
                    break  # Har bir kategoriyadan bitta
        
        return {
            'daily_routine': routines,
            'product_recommendations': product_recommendations[:3],  # Faqat 3 ta
            'weekly_tips': [
                "Haftada 1-2 marta yumshoq skrab",
                "Namlovchi niqob",
                "Ko'z atrofi parvarishi"
            ],
            'lifestyle_advice': [
                "Kuniga 8 stakan suv",
                "Sog'l ovqatlanish",
                "Etarli uyqu (7-8 soat)"
            ]
        }
    
    def get_fallback_analysis(self):
        """AI xatosida standart tahlil"""
        return {
            'score': 65,
            'skin_type': 'Normal',
            'skin_concerns': 'Rasm sifati past',
            'analysis_details': {'error': 'AI tahlil qila olmadi'},
            'recommendations': {
                'daily_routine': {
                    'morning': ['Tozalagich', 'Namlovchi krem SPF 30'],
                    'evening': ['Tozalagich', 'Tungi krem']
                }
            },
            'ai_model': 'Fallback',
            'confidence': 0.5,
            'timestamp': datetime.datetime.now().isoformat()
        }

# AI modelni ishga tushirish
skin_ai = SkinAI()

# ===================== CONVERSATIONS & ANALYSES =====================
def log_conversation(user_id, message_type, content, file_id=None):
    conv_file = f"{CONVERSATIONS_DIR}/{user_id}.json"
    conversations = load_json(conv_file, [])
    
    conversation = {
        'timestamp': datetime.datetime.now().isoformat(),
        'type': message_type,
        'content': content,
        'file_id': file_id
    }
    
    conversations.append(conversation)
    if len(conversations) > 100:
        conversations = conversations[-100:]
    
    save_json(conversations, conv_file)
    return True

def save_image(img_bytes, user_id, file_id=None):
    try:
        user_img_dir = f"{IMAGES_DIR}/{user_id}"
        os.makedirs(user_img_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.jpg"
        filepath = f"{user_img_dir}/{filename}"
        
        with open(filepath, "wb") as f:
            f.write(img_bytes)
        
        # Hash hisoblash
        try:
            img = Image.open(filepath)
            h = imagehash.phash(img)
            img_hash = str(h)
        except Exception as e:
            logger.error(f"Image hash error: {e}")
            img_hash = "unknown"
        
        # Rasm ma'lumotlarini saqlash
        image_info = {
            'filename': filename,
            'path': filepath,
            'hash': img_hash,
            'file_id': file_id,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        images_list_file = f"{user_img_dir}/_list.json"
        images_list = load_json(images_list_file, [])
        images_list.append(image_info)
        
        if len(images_list) > 50:
            images_list = images_list[-50:]
        
        save_json(images_list, images_list_file)
        
        return filepath, img_hash
        
    except Exception as e:
        logger.error(f"Save image error: {e}")
        return None, None

def save_analysis(user_id, image_path, analysis_data):
    try:
        analysis_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        analysis_file = f"{ANALYSES_DIR}/{user_id}_{analysis_id}.json"
        
        analysis_record = {
            'id': analysis_id,
            'user_id': user_id,
            'image_path': image_path,
            'timestamp': datetime.datetime.now().isoformat(),
            'analysis': analysis_data
        }
        
        # Yakuniy faylga saqlash
        save_json(analysis_record, analysis_file)
        
        # Foydalanuvchi tahlillari ro'yxatini yangilash
        user_analyses_file = f"{ANALYSES_DIR}/{user_id}_list.json"
        analyses_list = load_json(user_analyses_file, [])
        analyses_list.append(analysis_record)
        
        if len(analyses_list) > 100:  # Faqat oxirgi 100 ta
            analyses_list = analyses_list[-100:]
        
        save_json(analyses_list, user_analyses_file)
        
        # Statistikani yangilash
        update_global_stats()
        
        return analysis_id
    except Exception as e:
        logger.error(f"Save analysis error: {e}")
        return None

def get_user_analyses(user_id, limit=5):
    """Foydalanuvchi tahlillarini olish"""
    try:
        user_analyses_file = f"{ANALYSES_DIR}/{user_id}_list.json"
        analyses_list = load_json(user_analyses_file, [])
        
        # Agar fayl bo'lmasa, eski formatda qidirish
        if not analyses_list:
            analyses_list = []
            if os.path.exists(ANALYSES_DIR):
                for filename in os.listdir(ANALYSES_DIR):
                    if filename.startswith(f"{user_id}_") and filename.endswith('.json'):
                        try:
                            analysis_data = load_json(f"{ANALYSES_DIR}/{filename}")
                            if analysis_data:
                                analyses_list.append(analysis_data)
                        except:
                            continue
        
        # Oxirgi limit tani olish
        return analyses_list[-limit:] if analyses_list else []
    except Exception as e:
        logger.error(f"Get user analyses error: {e}")
        return []

# ===================== DECORATORS =====================
def user_tracker(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        user_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language_code': user.language_code,
            'last_active': datetime.datetime.now().isoformat()
        }
        
        existing_data = get_user(user.id)
        if not existing_data or 'created' not in existing_data:
            user_data['created'] = datetime.datetime.now().isoformat()
        
        existing_data.update(user_data)
        save_user(user.id, existing_data)
        
        if update.message:
            if update.message.text:
                log_conversation(user.id, "text", update.message.text, None)
            elif update.message.photo:
                log_conversation(user.id, "photo", "photo_uploaded",
                               update.message.photo[-1].file_id if update.message.photo else None)
        
        return await func(update, context)
    return wrapper

def admin_only(func):
    """Faqat adminlar uchun"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text(
                f"{EMOJI['lock']} *Ruxsat etilmagan!*\n"
                f"Bu funksiya faqat adminlar uchun.",
                parse_mode='Markdown'
            )
            return
        
        log_admin_action(user_id, f"admin_command_{func.__name__}")
        return await func(update, context)
    return wrapper

# ===================== MESSAGE FORMATTING =====================
# def format_welcome_message():
#     return f"""{EMOJI['welcome']} *DermAI Beauty Assistant* {EMOJI['lipstick']}

# 💖 *Xush kelibsiz, go'zal!* 💖

# {EMOJI['sparkle']} *Yangi AI funksiyalar:*
# • Haqiqiy AI tahlil
# • Shaxsiy mahsulot tavsiyalari
# • Kunlik eslatmalar
# • Statistikangizni kuzatish

# {EMOJI['mirror']} *Boshlash uchun:* 
# 1. Ism, yosh va teri turini yuboring
# 2. Yuzingizning aniq rasmni yuboring
# 3. AI tahlilini oling

def format_welcome_message(user_name=None):
    """Xush kelibshi xabarini formatlash"""
    # Agar user_name berilsa, shu ismni ishlatamiz
    # Agar yo'q bo'lsa, Telegramdan ismni olamiz yoki "go'zal" deb qo'yamiz
    if user_name:
        greeting = f"💖 *Xush kelibsiz, {user_name}!* 💖"
    else:
        greeting = "💖 *Xush kelibsiz, Qadirdon!* 💖"
    
    return f"""{EMOJI['welcome']} *DermAI Beauty Assistant* {EMOJI['lipstick']}

{greeting}

{EMOJI['sparkle']} *Yangi AI funksiyalar:*
• Haqiqiy AI tahlil
• Shaxsiy mahsulot tavsiyalari
• Kunlik eslatmalar
• Statistikangizni kuzatish

{EMOJI['mirror']} *Boshlash uchun:* 
1. Ism, yosh va teri turini yuboring
2. Yuzingizning aniq rasmni yuboring
3. AI tahlilini oling

🌸 *Sizning go'zalligingiz bizning mas'uliyatimiz!* 🌸


{EMOJI['warning']} *Bot test rejimida ishlamoqda Tushunganingiz uchun raxmat!!!* {EMOJI['warning']}



"""

def format_ai_analysis_result(analysis):
    score = analysis['score']
    
    if score >= 80:
        rating = f"{EMOJI['star']} {EMOJI['star']} {EMOJI['star']} ALO"
        color = "🟢"
    elif score >= 60:
        rating = f"{EMOJI['star']} {EMOJI['star']} YAXSHI"
        color = "🟡"
    else:
        rating = f"{EMOJI['star']} E'TIBOR KERAK"
        color = "🔴"
    
    # Mahsulot tavsiyalari
    product_text = ""
    if 'recommendations' in analysis and 'product_recommendations' in analysis['recommendations']:
        product_text = f"\n{EMOJI['product']} *TAVSIYA ETILGAN MAHSULOTLAR:*\n"
        for i, product in enumerate(analysis['recommendations']['product_recommendations'][:3], 1):
            product_text += f"{i}. *{product['brand']}* - {product['name']}\n"
    
    return f"""{EMOJI['analysis']} *AI TERI TAHLILINGIZ* {EMOJI['mirror']}

{color} *Umumiy holat:* {score}% ({rating})
{EMOJI['success']} *Ishonch darajasi:* {analysis.get('confidence', 0)*100:.1f}%

{EMOJI['skin']} *Terining turi:* {analysis['skin_type']}
{EMOJI['warning']} *Asosiy muammo:* {analysis['skin_concerns']}

{EMOJI['routine']} *🌞 ERTALABKI DASTUR:*
{chr(10).join(['• ' + item for item in analysis['recommendations']['daily_routine']['morning']])}

{EMOJI['routine']} *🌙 KECHKI DASTUR:*
{chr(10).join(['• ' + item for item in analysis['recommendations']['daily_routine']['evening']])}

{product_text}
{EMOJI['info']} *AI Model:* {analysis.get('ai_model', 'DermAI')}"""

# ===================== REMINDER SYSTEM =====================
class ReminderSystem:
    """Kunlik eslatmalar tizimi"""
    
    def __init__(self):
        self.reminders_file = f"{DATA_DIR}/reminders.json"
        self.load_reminders()
    
    def load_reminders(self):
        self.reminders = load_json(self.reminders_file, {})
    
    def save_reminders(self):
        save_json(self.reminders, self.reminders_file)
    
    def add_reminder(self, user_id, reminder_type, time, message):
        """Eslatma qo'shish"""
        if str(user_id) not in self.reminders:
            self.reminders[str(user_id)] = []
        
        reminder = {
            'id': datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            'type': reminder_type,  # daily, weekly, custom
            'time': time,  # "09:00" format
            'message': message,
            'active': True,
            'created': datetime.datetime.now().isoformat()
        }
        
        self.reminders[str(user_id)].append(reminder)
        self.save_reminders()
        return reminder['id']
    
    def get_user_reminders(self, user_id):
        """Foydalanuvchi eslatmalari"""
        return self.reminders.get(str(user_id), [])
    
    def delete_reminder(self, user_id, reminder_id):
        """Eslatmani o'chirish"""
        if str(user_id) in self.reminders:
            self.reminders[str(user_id)] = [
                r for r in self.reminders[str(user_id)] if r['id'] != reminder_id
            ]
            self.save_reminders()
            return True
        return False

reminder_system = ReminderSystem()

# ===================== HANDLERS =====================
@user_tracker
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = format_welcome_message()
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['photo']} AI Tahlil", callback_data="ai_analyze")],
        [InlineKeyboardButton(f"{EMOJI['bell']} Eslatmalar", callback_data="reminders"),
         InlineKeyboardButton(f"{EMOJI['stats']} Statistika", callback_data="my_stats")],
        [InlineKeyboardButton(f"{EMOJI['product']} Mahsulotlar", callback_data="products")]
    ]
    
    # Agar admin bo'lsa
    if is_admin(update.effective_user.id):
        keyboard.append([InlineKeyboardButton(f"{EMOJI['admin']} Admin Panel", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_msg,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@user_tracker
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    pattern = r'^([^,]+),\s*(\d+),\s*(.+)$'
    match = re.match(pattern, text)
    
    if match:
        name, age, skin_info = match.groups()
        
        skin_keywords = {
            'quruq': 'Quruq',
            "yog'li": "Yog'li",
            'yogli': "Yog'li",
            'aralash': 'Aralash',
            'hassas': 'Hassas',
            'normal': 'Normal',
            'akne': 'Aknega moyil'
        }
        
        skin_type = 'Normal'
        for key, value in skin_keywords.items():
            if key in skin_info.lower():
                skin_type = value
                break
        
        # Saqlash
        update_user(user_id, {
            'first_name': name.strip(),
            'age': int(age),
            'skin_type': skin_type
        })
        
        # Gender ni ham saqlash (agar kerak bo'lsa)
        update_user(user_id, {'gender': 'aniqlanmadi'})
        
        response = f"""{EMOJI['success']} *Ma'lumotlar saqlandi!* {EMOJI['heart']}

👩 *Ism:* {name}
🎂 *Yosh:* {age}
🧴 *Terining turi:* {skin_type}

{EMOJI['photo']} Endi AI tahlili uchun yuzingizning *yorug' va aniq* rasmni yuboring."""
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    elif text.lower() == '/history':
        await history_command(update, context)
    elif text.lower() == '/products':
        await products_command(update, context)
    elif text.lower() == '/reminders':
        await reminders_command(update, context)
    elif text.lower() == '/admin' and is_admin(user_id):
        await admin_panel(update, context)
    else:
        await update.message.reply_text(
            f"{EMOJI['info']} Format: *Ism, Yosh, Teri turi*\n"
            "Masalan: *Dilnoza, 24, Yog'li*\n\n"
            f"Yoki quyidagi buyruqlardan foydalaning:\n"
            f"/history - Tahlillar tarixi\n"
            f"/products - Mahsulotlar\n"
            f"/reminders - Eslatmalar",
            parse_mode='Markdown'
        )

@user_tracker
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data.get('first_name'):
        await update.message.reply_text(
            f"{EMOJI['warning']} Avval ism, yosh va teri turingizni yuboring!\n"
            f"Format: *Ism, Yosh, Teri turi*",
            parse_mode='Markdown'
        )
        return
    
    # Rasmni yuklash
    photo = update.message.photo[-1]
    file = await photo.get_file()
    bio = io.BytesIO()
    await file.download_to_memory(bio)
    img_bytes = bio.getvalue()
    
    # Saqlash
    path, img_hash = save_image(img_bytes, user_id, file.file_id)
    
    if not path:
        await update.message.reply_text(f"{EMOJI['warning']} Rasm saqlanmadi.")
        return
    
    # AI tahlili
    loading_msg = await update.message.reply_text(
        f"{EMOJI['analysis']} *AI tahlil qilmoqda...*\n"
        f"{EMOJI['sparkle']} Iltimos, kuting...",
        parse_mode='Markdown'
    )
    
    analysis = skin_ai.analyze_image(path)
    
    # Saqlash
    analysis_id = save_analysis(user_id, path, analysis)
    
    if not analysis_id:
        await update.message.reply_text(f"{EMOJI['warning']} Tahlil saqlanmadi.")
        return
    
    # Natija
    result_message = format_ai_analysis_result(analysis)
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['bell']} Kunlik eslatma", callback_data=f"set_reminder_{analysis_id}"),
         InlineKeyboardButton(f"{EMOJI['product']} Batafsil", callback_data=f"details_{analysis_id}")],
        [InlineKeyboardButton(f"{EMOJI['photo']} Yangi tahlil", callback_data="new_analysis")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Loading xabarini o'chirish
    try:
        await loading_msg.delete()
    except:
        pass
    
    await update.message.reply_text(
        result_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@user_tracker
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    analyses = get_user_analyses(user_id, limit=5)
    
    if not analyses:
        await update.message.reply_text(
            f"{EMOJI['info']} Hozircha tahlillar yo'q. Rasm yuboring!",
            parse_mode='Markdown'
        )
        return
    
    history_text = f"{EMOJI['calendar']} *SO'NGI 5 TA AI TAHLILINGIZ*\n\n"
    
    for i, analysis in enumerate(reversed(analyses), 1):
        timestamp = analysis.get('timestamp', '')
        if timestamp:
            try:
                timestamp_dt = datetime.datetime.fromisoformat(timestamp)
                date = timestamp_dt.strftime("%d.%m.%Y %H:%M")
            except:
                date = timestamp[:16]
        else:
            date = "Noma'lum"
        
        analysis_data = analysis.get('analysis', {})
        history_text += f"*{i}. {date}*\n"
        history_text += f"   {EMOJI['star']} *Ball:* {analysis_data.get('score', 'N/A')}%\n"
        history_text += f"   {EMOJI['skin']} *Turi:* {analysis_data.get('skin_type', 'N/A')}\n\n"
    
    keyboard = [[InlineKeyboardButton(f"{EMOJI['photo']} Yangi tahlil", callback_data="new_analysis")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        history_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ===================== ADMIN HANDLERS =====================
@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin paneli"""
    stats = get_admin_stats()
    
    admin_text = f"""{EMOJI['admin']} *ADMIN PANELI* {EMOJI['admin']}

📊 *Statistika:*
• {EMOJI['users']} Jami foydalanuvchilar: {stats['total_users']}
• {EMOJI['chart']} Bugun faol: {stats['active_today']}
• {EMOJI['analysis']} Jami tahlillar: {stats['total_analyses']}
• {EMOJI['star']} O'rtacha ball: {stats['avg_score']}

⚙️ *Admin funksiyalari:*"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJI['users']} Barcha foydalanuvchilar", callback_data="admin_users")],
        [InlineKeyboardButton(f"{EMOJI['chart']} Statistika", callback_data="admin_stats_detailed")],
        [InlineKeyboardButton(f"{EMOJI['export']} Eksport", callback_data="admin_export")],
        [InlineKeyboardButton(f"{EMOJI['bell']} Xabarlar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(f"{EMOJI['product']} Mahsulotlar", callback_data="admin_products")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        admin_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@admin_only
async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha foydalanuvchilar ro'yxati"""
    users = get_all_users()
    
    if not users:
        await update.message.reply_text(f"{EMOJI['info']} Hozircha foydalanuvchilar yo'q.")
        return
    
    # Pagination
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 1
    per_page = 10
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    users_text = f"""{EMOJI['users']} *FOYDALANUVCHILAR ({len(users)})* {EMOJI['users']}

Sahifa: {page}/{(len(users) + per_page - 1) // per_page}\n\n"""
    
    for i, user in enumerate(users[start_idx:end_idx], start_idx + 1):
        user_id = user.get('user_id', 'N/A')
        username = f"@{user.get('username', '')}" if user.get('username') else "No username"
        name = user.get('first_name', 'No name')
        last_active = user.get('last_active', '')[:16] if user.get('last_active') else 'N/A'
        
        users_text += f"""*{i}. {name}* ({username})
🆔 {user_id}
📅 So'nggi faollik: {last_active}
🧴 Teri turi: {user.get('skin_type', 'N/A')}
---
"""
    
    keyboard = []
    if page > 1:
        keyboard.append(InlineKeyboardButton(f"⬅️ Oldingi", callback_data=f"admin_users_{page-1}"))
    if end_idx < len(users):
        keyboard.append(InlineKeyboardButton(f"Keyingi ➡️", callback_data=f"admin_users_{page+1}"))
    
    if keyboard:
        reply_markup = InlineKeyboardMarkup([keyboard])
    else:
        reply_markup = None
    
    await update.message.reply_text(
        users_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@admin_only
async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Batafsil statistika"""
    stats = get_admin_stats()
    skin_stats = get_skin_statistics()
    
    stats_text = f"""{EMOJI['chart']} *BATAFSIL STATISTIKA* {EMOJI['chart']}

{EMOJI['users']} *Foydalanuvchilar:*
• Jami: {stats['total_users']}
• Bugun faol: {stats['active_today']}
• Tahlillar: {stats['total_analyses']}
• O'rtacha ball: {stats['avg_score']}

{EMOJI['skin']} *Teri turlari:*
"""
    
    for skin_type, count in stats['skin_type_distribution'].items():
        if skin_type != 'aniqlanmadi' and stats['total_users'] > 0:
            percentage = (count / stats['total_users'] * 100)
            stats_text += f"• {skin_type}: {count} ({percentage:.1f}%)\n"
    
    if skin_stats['age_groups']:
        stats_text += f"\n{EMOJI['calendar']} *Yosh guruhlari:*\n"
        for age_group, count in skin_stats['age_groups'].items():
            stats_text += f"• {age_group}: {count}\n"
    
    # CSV eksport tugmasi
    keyboard = [[InlineKeyboardButton(f"{EMOJI['export']} CSV eksport", callback_data="admin_export_csv")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

@admin_only
async def admin_broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xabar yuborish"""
    if not context.args:
        await update.message.reply_text(
            f"{EMOJI['info']} Format: /broadcast <xabar matni>\n"
            f"Yoki /broadcast_image <rasm caption>"
        )
        return
    
    message_text = ' '.join(context.args)
    users = get_all_users()
    
    await update.message.reply_text(
        f"{EMOJI['bell']} {len(users)} foydalanuvchiga xabar yuborilmoqda..."
    )
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            user_id = user.get('user_id')
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *Admin xabarı:*\n\n{message_text}",
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Broadcast error to {user_id}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"{EMOJI['success']} Xabar yuborildi!\n"
        f"✅ Muvaffaqiyatli: {success_count}\n"
        f"❌ Xato: {fail_count}"
    )
    
    log_admin_action(update.effective_user.id, "broadcast", 
                    f"Sent to {success_count} users, failed: {fail_count}")

# ===================== PRODUCT HANDLERS =====================
async def products_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mahsulotlar ro'yxati"""
    products = get_products()
    
    products_text = f"""{EMOJI['product']} *MAHSULOT TAVSIYALARI* {EMOJI['product']}

Har bir teri turi uchun maxsus tanlangan mahsulotlar:"""
    
    keyboard = []
    
    for category in products.keys():
        category_name = category.capitalize()
        keyboard.append([InlineKeyboardButton(
            f"{EMOJI['product']} {category_name}", 
            callback_data=f"products_{category}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        products_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ===================== REMINDER HANDLERS =====================
@user_tracker
async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi eslatmalari"""
    user_id = update.effective_user.id
    user_reminders = reminder_system.get_user_reminders(user_id)
    
    if not user_reminders:
        await update.message.reply_text(
            f"{EMOJI['bell']} Hozircha eslatmalaringiz yo'q.\n"
            f"Tahlil qilganingizdan so'ng kunlik eslatma sozashingiz mumkin.",
            parse_mode='Markdown'
        )
        return
    
    reminders_text = f"{EMOJI['bell']} *ESLATMALARINGIZ*\n\n"
    
    for i, reminder in enumerate(user_reminders, 1):
        if reminder.get('active', True):
            reminders_text += f"*{i}. {reminder['type'].capitalize()} eslatma*\n"
            reminders_text += f"   🕐 Vaqt: {reminder['time']}\n"
            reminders_text += f"   📝 {reminder['message'][:50]}...\n"
            reminders_text += f"   [ID: {reminder['id']}]\n\n"
    
    keyboard = [
        [InlineKeyboardButton(f"➕ Yangi eslatma", callback_data="add_reminder")],
        [InlineKeyboardButton(f"🗑️ Eslatmani o'chirish", callback_data="delete_reminder")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        reminders_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ===================== CALLBACK HANDLER =====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    message = query.message
    
    try:
        # AI tahlil
        if data == "ai_analyze":
            user_data = get_user(user_id)
            if user_data.get('first_name'):
                await message.reply_text(
                    f"{EMOJI['photo']} Endi AI tahlili uchun yuzingizning rasmni yuboring."
                )
            else:
                await message.reply_text(
                    f"{EMOJI['info']} Avval ism, yosh va teri turingizni yuboring.\n"
                    f"Format: *Ism, Yosh, Teri turi*",
                    parse_mode='Markdown'
                )
        
        # Yangi tahlil
        elif data == "new_analysis":
            await message.reply_text(
                f"{EMOJI['photo']} Yuzingizning yangi rasmni yuboring."
            )
        
        # Admin panel
        elif data == "admin_panel":
            if is_admin(user_id):
                stats = get_admin_stats()
                admin_text = f"""{EMOJI['admin']} *ADMIN PANELI* {EMOJI['admin']}

📊 *Statistika:*
• {EMOJI['users']} Jami foydalanuvchilar: {stats['total_users']}
• {EMOJI['chart']} Bugun faol: {stats['active_today']}
• {EMOJI['analysis']} Jami tahlillar: {stats['total_analyses']}
• {EMOJI['star']} O'rtacha ball: {stats['avg_score']}

⚙️ *Admin funksiyalari:*"""
                
                keyboard = [
                    [InlineKeyboardButton(f"{EMOJI['users']} Foydalanuvchilar", callback_data="admin_users_1")],
                    [InlineKeyboardButton(f"{EMOJI['chart']} Statistika", callback_data="admin_stats_detailed")],
                    [InlineKeyboardButton(f"{EMOJI['export']} Eksport", callback_data="admin_export_csv")],
                    [InlineKeyboardButton(f"{EMOJI['bell']} Xabar yuborish", callback_data="admin_broadcast")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await message.edit_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await message.reply_text(f"{EMOJI['lock']} Ruxsat yo'q!")
        
        # Statistika
        elif data == "my_stats":
            analyses = get_user_analyses(user_id)
            user_data = get_user(user_id)
            
            if not analyses:
                await message.edit_text(
                    f"{EMOJI['info']} Hozircha statistika yo'q. Birinchi tahlil qiling!"
                )
                return
            
            total_score = sum(a.get('analysis', {}).get('score', 0) for a in analyses)
            avg_score = total_score / len(analyses) if analyses else 0
            
            stats_text = f"""{EMOJI['chart']} *SHAXSIY STATISTIKANGIZ* {EMOJI['chart']}

📊 *Umumiy:*
• Tahlillar soni: {len(analyses)}
• O'rtacha ball: {avg_score:.1f}%
• So'nggi tahlil: {analyses[-1].get('timestamp', '')[:10] if analyses else 'N/A'}

🧴 *Teri ma'lumotlari:*
• Teri turi: {user_data.get('skin_type', 'Aniqlanmadi')}
• Yosh: {user_data.get('age', 'Aniqlanmadi')}

{EMOJI['sparkle']} *Reyting:* {"A'lo" if avg_score >= 80 else "Yaxshi" if avg_score >= 60 else "O'rtacha"}"""
            
            keyboard = [[InlineKeyboardButton(f"{EMOJI['photo']} Yangi tahlil", callback_data="new_analysis")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.edit_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Mahsulotlar
        elif data.startswith("products_"):
            category = data[9:]
            products = get_products()
            
            if category in products:
                products_text = f"{EMOJI['product']} *{category.upper()}*\n\n"
                
                for i, product in enumerate(products[category], 1):
                    products_text += f"""*{i}. {product['name']}*
🏷️ *Brand:* {product['brand']}
💰 *Narx:* {product['price']}
📝 {product['description']}
---
"""
                
                keyboard = [[InlineKeyboardButton(f"⬅️ Orqaga", callback_data="products_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await message.edit_text(products_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Mahsulotlar orqaga
        elif data == "products_back":
            products = get_products()
            products_text = f"""{EMOJI['product']} *MAHSULOT TAVSIYALARI* {EMOJI['product']}

Har bir teri turi uchun maxsus tanlangan mahsulotlar:"""
            
            keyboard = []
            for category in products.keys():
                category_name = category.capitalize()
                keyboard.append([InlineKeyboardButton(
                    f"{EMOJI['product']} {category_name}", 
                    callback_data=f"products_{category}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.edit_text(products_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Eslatmalar
        elif data == "reminders":
            user_reminders = reminder_system.get_user_reminders(user_id)
            
            if not user_reminders:
                reminders_text = f"{EMOJI['bell']} *ESLATMALARINGIZ*\n\nHozircha eslatmalaringiz yo'q."
                keyboard = [[InlineKeyboardButton(f"➕ Yangi eslatma", callback_data="add_reminder")]]
            else:
                reminders_text = f"{EMOJI['bell']} *ESLATMALARINGIZ*\n\n"
                for i, reminder in enumerate(user_reminders, 1):
                    if reminder.get('active', True):
                        reminders_text += f"*{i}. {reminder['type'].capitalize()} eslatma*\n"
                        reminders_text += f"   🕐 Vaqt: {reminder['time']}\n"
                        reminders_text += f"   📝 {reminder['message'][:50]}...\n\n"
                
                keyboard = [
                    [InlineKeyboardButton(f"➕ Yangi eslatma", callback_data="add_reminder")],
                    [InlineKeyboardButton(f"🗑️ O'chirish", callback_data="delete_reminder")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.edit_text(reminders_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Admin funksiyalari
        elif data.startswith("admin_"):
            if is_admin(user_id):
                if data.startswith("admin_users_"):
                    page = int(data.split('_')[2]) if len(data.split('_')) > 2 else 1
                    users = get_all_users()
                    
                    if not users:
                        await message.edit_text(f"{EMOJI['info']} Hozircha foydalanuvchilar yo'q.")
                        return
                    
                    per_page = 10
                    start_idx = (page - 1) * per_page
                    end_idx = start_idx + per_page
                    
                    users_text = f"""{EMOJI['users']} *FOYDALANUVCHILAR ({len(users)})* {EMOJI['users']}

Sahifa: {page}/{(len(users) + per_page - 1) // per_page}\n\n"""
                    
                    for i, user in enumerate(users[start_idx:end_idx], start_idx + 1):
                        user_id = user.get('user_id', 'N/A')
                        username = f"@{user.get('username', '')}" if user.get('username') else "No username"
                        name = user.get('first_name', 'No name')
                        
                        users_text += f"""*{i}. {name}* ({username})
🆔 {user_id}
🧴 Teri turi: {user.get('skin_type', 'N/A')}
---
"""
                    
                    keyboard = []
                    if page > 1:
                        keyboard.append(InlineKeyboardButton(f"⬅️ Oldingi", callback_data=f"admin_users_{page-1}"))
                    if end_idx < len(users):
                        if keyboard:
                            keyboard.append(InlineKeyboardButton(f"Keyingi ➡️", callback_data=f"admin_users_{page+1}"))
                        else:
                            keyboard = [InlineKeyboardButton(f"Keyingi ➡️", callback_data=f"admin_users_{page+1}")]
                    
                    keyboard.append([InlineKeyboardButton(f"⬅️ Admin panel", callback_data="admin_panel")])
                    
                    reply_markup = InlineKeyboardMarkup([keyboard] if isinstance(keyboard[0], list) else [keyboard])
                    await message.edit_text(users_text, reply_markup=reply_markup, parse_mode='Markdown')
                
                elif data == "admin_stats_detailed":
                    stats = get_admin_stats()
                    skin_stats = get_skin_statistics()
                    
                    stats_text = f"""{EMOJI['chart']} *BATAFSIL STATISTIKA* {EMOJI['chart']}

{EMOJI['users']} *Foydalanuvchilar:*
• Jami: {stats['total_users']}
• Bugun faol: {stats['active_today']}
• Tahlillar: {stats['total_analyses']}
• O'rtacha ball: {stats['avg_score']}

{EMOJI['skin']} *Teri turlari:*
"""
                    
                    for skin_type, count in stats['skin_type_distribution'].items():
                        if skin_type != 'aniqlanmadi' and stats['total_users'] > 0:
                            percentage = (count / stats['total_users'] * 100)
                            stats_text += f"• {skin_type}: {count} ({percentage:.1f}%)\n"
                    
                    keyboard = [
                        [InlineKeyboardButton(f"{EMOJI['export']} CSV eksport", callback_data="admin_export_csv")],
                        [InlineKeyboardButton(f"⬅️ Admin panel", callback_data="admin_panel")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await message.edit_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
                
                elif data == "admin_export_csv":
                    filename = export_users_csv()
                    if filename:
                        await message.reply_text(
                            f"{EMOJI['success']} CSV fayl yaratildi:\n`{filename}`",
                            parse_mode='Markdown'
                        )
                    else:
                        await message.reply_text(f"{EMOJI['warning']} Xatolik yuz berdi!")
                
                elif data == "admin_broadcast":
                    await message.reply_text(
                        f"{EMOJI['info']} Xabar yuborish uchun:\n`/broadcast <xabar matni>`",
                        parse_mode='Markdown'
                    )
            else:
                await message.reply_text(f"{EMOJI['lock']} Ruxsat yo'q!")
        
        else:
            await message.reply_text(
                f"{EMOJI['info']} Funksiya ishga tushirildi. /start ni bosib qayta boshlashingiz mumkin."
            )
    
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await message.reply_text(
            f"{EMOJI['warning']} Xatolik yuz berdi. Iltimos, /start ni bosing."
        )

# ===================== SCHEDULED TASKS =====================
async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Kunlik eslatmalarni yuborish"""
    try:
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        
        for user_id_str in reminder_system.reminders:
            try:
                user_id = int(user_id_str)
                reminders = reminder_system.get_user_reminders(user_id)
                
                for reminder in reminders:
                    if (reminder.get('active', True) and 
                        reminder.get('time') == current_time and
                        reminder.get('type') == 'daily'):
                        
                        try:
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=f"{EMOJI['bell']} *KUNLIK ESLATMA*\n\n{reminder['message']}",
                                parse_mode='Markdown'
                            )
                            logger.info(f"Sent reminder to {user_id}")
                        except Exception as e:
                            logger.error(f"Reminder send error to {user_id}: {e}")
                            
            except Exception as e:
                logger.error(f"Reminder processing error: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Daily reminders error: {e}")

async def update_daily_stats(context: ContextTypes.DEFAULT_TYPE):
    """Kunlik statistikani yangilash"""
    update_global_stats()
    logger.info("Daily stats updated")

# ===================== ERROR HANDLER =====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    
    try:
        error_msg = f"{EMOJI['warning']} Xatolik yuz berdi. Iltimos, /start ni bosib qayta boshlang."
        
        if update and update.effective_user:
            if update.callback_query:
                await update.callback_query.message.reply_text(error_msg)
            elif update.message:
                await update.message.reply_text(error_msg)
    except:
        pass

# ===================== BOT START =====================
def main():
    """Asosiy funksiya"""
    # Mahsulotlar bazasini ishga tushirish
    init_products_db()
    
    # Botni yaratish
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Xatolarni qayta ishlash
    app.add_error_handler(error_handler)
    
    # Komanda handlarlari
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("products", products_command))
    app.add_handler(CommandHandler("reminders", reminders_command))
    
    # Admin komandalari
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("admin_users", admin_users_command))
    app.add_handler(CommandHandler("admin_stats", admin_stats_command))
    app.add_handler(CommandHandler("broadcast", admin_broadcast_command))
    
    # Callback query handlari
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Xabar handlarlari
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Rejalashtirilgan vazifalar
    job_queue = app.job_queue
    if job_queue:
        # Kunlik eslatmalar (har soat)
        job_queue.run_repeating(
            send_daily_reminders,
            interval=3600,  # Har soat
            first=datetime.time(hour=0, minute=0)
        )
        
        # Kunlik statistika (har kuni kechasi)
        job_queue.run_daily(
            update_daily_stats,
            time=datetime.time(hour=23, minute=59)
        )
    
    print(f"{EMOJI['flower']} DermAI Pro Bot ishga tushdi! {EMOJI['lipstick']}")
    print(f"{EMOJI['admin']} Admin IDs: {ADMIN_IDS}")
    print(f"📁 Ma'lumotlar: {DATA_DIR}/")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()