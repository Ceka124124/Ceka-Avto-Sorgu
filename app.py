import telebot
from telebot import types
import requests
import json
import logging
import re
import string
import random
from datetime import datetime, timedelta
from functools import wraps
import time

# -----------------------------------------------------------------------------
# YAPILANDIRMA VE SABİTLER
# -----------------------------------------------------------------------------

# DİKKAT: Bu botun çalışması için geçerli bir token ve API URL'si gereklidir.
# Güvenlik nedeniyle, bu token ve URL'ler gerçek ortamda güvenli tutulmalıdır.
BOT_TOKEN = "7730127052:AAFceL7gnuUMrWEYm7N0hLcTDkKqphAR7Pw"
EXTERNAL_REGISTER_URL = 'http://deuslra.alwaysdata.net/api.php'
ADMIN_ID = [7489387402, 8023969164, 7492280255]

bot = telebot.TeleBot(BOT_TOKEN)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Kullanıcı verileri ve istatistikler
user_data = {}
statistics = {
    'total_registrations': 0,
    'successful_registrations': 0,
    'failed_registrations': 0,
    'random_accounts': 0,
    'custom_accounts': 0,
    'premium_accounts': 0,
    'normal_accounts': 0
}

# Emoji ve stil sabitleri
EMOJI = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'loading': '⏳',
    'info': 'ℹ️',
    'robot': '🤖',
    'user': '👤',
    'email': '📧',
    'password': '🔐',
    'premium': '💎',
    'calendar': '📅',
    'clock': '⏰',
    'random': '🎲',
    'custom': '✏️',
    'stats': '📊',
    'list': '📋',
    'settings': '⚙️',
    'refresh': '🔄',
    'back': '⬅️',
    'cancel': '🚫',
    'check': '✔️',
    'star': '⭐'
}

# Kullanıcı adı önekleri ve domain'ler
USERNAME_PREFIXES = ['user', 'member', 'account', 'pro', 'elite', 'alpha', 'beta', 'prime', 'vip', 'guest']
EMAIL_DOMAINS = ['mocker.free', 'tempmail.com', 'quickmail.net', 'fakemail.org']

# -----------------------------------------------------------------------------
# DEKORATÖRLER
# -----------------------------------------------------------------------------

def admin_only(func):
    """Sadece admin kullanıcıların erişimini sağlar."""
    @wraps(func)
    def wrapper(message_or_call, *args, **kwargs):
        if isinstance(message_or_call, types.CallbackQuery):
            user_id = message_or_call.from_user.id
            chat_id = message_or_call.message.chat.id
        else:
            user_id = message_or_call.from_user.id
            chat_id = message_or_call.chat.id
        
        if user_id not in ADMIN_ID:
            # Sadece mesaj komutlarında yanıt ver, callback'te sessiz kal
            if not isinstance(message_or_call, types.CallbackQuery):
                 bot.send_message(
                    chat_id,
                    f"{EMOJI['error']} *Erişim Engellendi*\n\n"
                    "Bu bot sadece yetkili yöneticiler için tasarlanmıştır.",
                    parse_mode='Markdown'
                )
            return
        return func(message_or_call, *args, **kwargs)
    return wrapper

def log_action(action_type):
    """İşlemleri loglar."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logging.info(f"Action: {action_type} - Function: {func.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

# -----------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# -----------------------------------------------------------------------------

def escape_markdown(text):
    """Markdown özel karakterlerini kaçış yapar."""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', str(text))

def format_datetime(dt_str):
    """Tarih formatını güzelleştirir."""
    try:
        dt = datetime.strptime(dt_str, '%d.%m.%y %H:%M')
        return dt.strftime('%d %B %Y, %H:%M')
    except:
        return dt_str

def calculate_time_remaining(end_date_str):
    """Kalan süreyi hesaplar."""
    try:
        end_date = datetime.strptime(end_date_str, '%d.%m.%y %H:%M')
        now = datetime.now()
        remaining = end_date - now
        
        if remaining.total_seconds() <= 0:
            return "Süresi dolmuş"
        
        days = remaining.days
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        if days > 0:
            return f"{days} gün, {hours} saat"
        elif hours > 0:
            return f"{hours} saat, {minutes} dakika"
        else:
            return f"{minutes} dakika"
    except:
        return "Hesaplanamadı"

def check_email_format(email):
    """Gelişmiş e-posta formatı kontrolü."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_date_format(date_str):
    """DD.MM.YY HH:MM formatını kontrol eder."""
    try:
        dt = datetime.strptime(date_str, '%d.%m.%y %H:%M')
        # Geçmişte bir tarih girilmediğinden emin ol
        if dt < datetime.now() - timedelta(minutes=1): 
            return False, "Tarih geçmişte olamaz"
        return True, None
    except ValueError:
        return False, "Geçersiz format"

def generate_random_username(style='default'):
    """Gelişmiş rastgele kullanıcı adı oluşturur."""
    if style == 'premium':
        prefix = random.choice(['elite', 'prime', 'vip', 'pro'])
        number = random.randint(100, 999)
        suffix = random.choice(['_x', '_pro', '_vip', ''])
        return f"{prefix}{number}{suffix}"
    else:
        prefix = random.choice(USERNAME_PREFIXES)
        number = random.randint(1000, 9999)
        return f"{prefix}{number}"

def generate_random_email(style='default'):
    """Gelişmiş rastgele e-posta adresi oluşturur."""
    username_length = 10 if style == 'premium' else 8
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))
    domain = random.choice(EMAIL_DOMAINS)
    return f"{username}@{domain}"

def generate_random_password(length=12, strong=True):
    """Gelişmiş rastgele şifre oluşturur."""
    if strong:
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choices(characters, k=length))
        # En az 1 büyük, 1 küçük, 1 rakam, 1 özel karakter garantisi
        if not any(c.isupper() for c in password):
            password = password[:-1] + random.choice(string.ascii_uppercase)
        if not any(c.islower() for c in password):
            password = password[:-2] + random.choice(string.ascii_lowercase) + password[-1]
        if not any(c.isdigit() for c in password):
            password = password[:-3] + random.choice(string.digits) + password[-2:]
        if not any(c in "!@#$%^&*" for c in password):
            password = random.choice("!@#$%^&*") + password[1:]
        return password
    else:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def parse_time_duration(time_str):
    """Gelişmiş zaman parse işlemi. Sadece pozitif süreleri kabul eder."""
    time_str = time_str.lower().strip()
    
    # "1g", "2h", "3w" gibi kısa formatlar
    short_pattern = r'^(\d+)([hdwmy])$'
    short_match = re.match(short_pattern, time_str)
    
    if short_match:
        amount = int(short_match.group(1))
        unit = short_match.group(2)
        
        unit_map = {
            'h': 'saat',
            'd': 'gün',
            'w': 'hafta',
            'm': 'ay',
            'y': 'yıl'
        }
        time_str = f"{amount} {unit_map.get(unit, 'gün')}"
    
    parts = time_str.split()
    if len(parts) != 2:
        return None, "Geçersiz format. '10 gün' veya '10d' gibi olmalı."
    
    try:
        amount = int(parts[0])
        if amount <= 0:
            return None, "Miktar pozitif olmalı"
    except ValueError:
        return None, "Geçersiz sayı"
    
    unit = parts[1]
    now = datetime.now()
    
    unit_map = {
        'saat': timedelta(hours=1),
        'gün': timedelta(days=1),
        'gun': timedelta(days=1),
        'hafta': timedelta(weeks=1),
        'ay': timedelta(days=30), # Ortalama 30 gün
        'yıl': timedelta(days=365), # Ortalama 365 gün
        'yil': timedelta(days=365)
    }
    
    if unit not in unit_map:
        return None, f"Geçersiz birim: {unit}. Kabul edilenler: saat, gün, hafta, ay, yıl"
    
    future_date = now + (unit_map[unit] * amount)
    return future_date.strftime('%d.%m.%y %H:%M'), None

def send_api_request(data):
    """Gelişmiş API isteği."""
    payload = {
        'action': 'external_register',
        'username': data['username'],
        'email': data['email'],
        'password': data['password'],
        'premium': data['premium'],
        'register_date': data['register_date']
    }
    
    try:
        response = requests.post(EXTERNAL_REGISTER_URL, data=payload, timeout=30)
        response.raise_for_status() # HTTP hataları için istisna fırlatır
        
        # İstatistikleri güncelle
        statistics['total_registrations'] += 1
        
        # API'nin her zaman JSON döndürdüğünü varsayıyoruz
        result = response.json()
        if result.get('success'):
            statistics['successful_registrations'] += 1
            if data.get('type') == 'register_random':
                statistics['random_accounts'] += 1
            else:
                statistics['custom_accounts'] += 1
            
            if data['premium'] == '1':
                statistics['premium_accounts'] += 1
            else:
                statistics['normal_accounts'] += 1
        else:
            statistics['failed_registrations'] += 1
        
        return result
    except requests.exceptions.HTTPError as e:
        statistics['failed_registrations'] += 1
        logging.error(f"API HTTP Hatası: {e} - Yanıt: {response.text[:200]}")
        return {'success': False, 'message': f"HTTP Hatası: {e.response.status_code}"}
    except requests.exceptions.RequestException as e:
        statistics['failed_registrations'] += 1
        logging.error(f"API isteği bağlantı/timeout hatası: {e}")
        return {'success': False, 'message': f"Bağlantı Hatası: {str(e)}"}
    except json.JSONDecodeError:
        statistics['failed_registrations'] += 1
        logging.error(f"JSON decode hatası. Yanıt: {response.text}")
        return {'success': False, 'message': "API geçersiz veya boş yanıt döndürdü"}

def get_account_info_message(data, result=None):
    """Hesap bilgilerini formatlı mesaj olarak döndürür."""
    premium_text = f"{EMOJI['premium']} Premium" if data.get('premium') == '1' else f"{EMOJI['star']} Normal"
    account_type = f"{EMOJI['random']} Random" if data.get('type') == 'register_random' else f"{EMOJI['custom']} Özel"
    
    # data['register_date'] alanının set edildiğinden emin ol
    register_date = data.get('register_date', 'Bilinmiyor')
    remaining = calculate_time_remaining(register_date)
    
    message = (
        f"{'═' * 30}\n"
        f"  {account_type} HESAP BİLGİLERİ\n"
        f"{'═' * 30}\n\n"
        f"{EMOJI['user']} *Kullanıcı Adı*\n"
        f"└─ `{escape_markdown(data['username'])}`\n\n"
        
        # DÜZELTME: E-posta için 'escape_markdown' kaldırıldı.
        # Kod bloğu içinde olduğu için kaçış karakterine gerek yok.
        f"{EMOJI['email']} *E-posta*\n"
        f"└─ `{data['email']}`\n\n"
        
        # DÜZELTME: Şifre için 'escape_markdown' kaldırıldı.
        f"{EMOJI['password']} *Şifre*\n"
        f"└─ `{data['password']}`\n\n"
        
        f"{premium_text}\n\n"
        f"{EMOJI['calendar']} *Bitiş Tarihi*\n"
        f"└─ `{escape_markdown(register_date)}`\n\n"
        f"{EMOJI['clock']} *Kalan Süre*\n"
        f"└─ {remaining}\n"
        f"{'═' * 30}"
    )
    
    return message


def send_registration_confirmation(message, data):
    """Kayıt bilgilerini gösterir ve son onayı ister."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    confirmation_message = (
        f"{EMOJI['check']} *Kayıt Onayı*\n"
        f"{'═' * 35}\n\n"
        f"Aşağıdaki bilgilerle hesap oluşturulacak. Onaylıyor musunuz?\n\n"
        f"{get_account_info_message(data)}\n"
        f"{'═' * 35}"
    )
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(f"{EMOJI['check']} Onayla ve Kaydet", callback_data='final_register_confirm'),
        types.InlineKeyboardButton(f"{EMOJI['cancel']} İptal", callback_data='final_register_cancel')
    )
    
    bot.send_message(chat_id, confirmation_message, reply_markup=keyboard, parse_mode='Markdown')
# -----------------------------------------------------------------------------
# TELEGRAM BOT KOMUTLARI
# -----------------------------------------------------------------------------

@bot.message_handler(commands=['start'])
@admin_only
@log_action('start')
def send_welcome(message):
    """Hoş geldin mesajı ve ana menü."""
    welcome_text = (
        f"{EMOJI['robot']} *Gelişmiş Kayıt Yönetim Sistemi*\n"
        f"{'═' * 35}\n\n"
        f"Merhaba *{escape_markdown(message.from_user.first_name)}*!\n\n"
        f"Bu bot ile hızlı ve kolay hesap kaydı yapabilirsiniz.\n\n"
        f"*Özellikler:*\n"
        f"{EMOJI['random']} Random hesap oluşturma\n"
        f"{EMOJI['custom']} Özel hesap oluşturma\n"
        f"{EMOJI['stats']} İstatistik görüntüleme\n\n"
        f"Başlamak için aşağıdaki menüyü kullanın:"
    )
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(f"{EMOJI['random']} Random Hesap", callback_data='menu_register_random'),
        types.InlineKeyboardButton(f"{EMOJI['custom']} Özel Hesap", callback_data='menu_register_custom'),
        types.InlineKeyboardButton(f"{EMOJI['stats']} İstatistikler", callback_data='menu_stats'),
        types.InlineKeyboardButton(f"{EMOJI['settings']} Ayarlar", callback_data='menu_settings')
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
@admin_only
def send_help(message):
    """Yardım mesajı."""
    help_text = (
        f"{EMOJI['info']} *Komutlar ve Kullanım*\n"
        f"{'═' * 35}\n\n"
        f"*Temel Komutlar:*\n"
        f"`/start` - Ana menüyü açar\n"
        f"`/register` - Hızlı kayıt başlatır\n"
        f"`/stats` - İstatistikleri gösterir\n"
        f"`/cancel` - İşlemi iptal eder\n"
        f"`/help` - Bu yardım mesajı\n\n"
        f"*Süre Formatları:*\n"
        f"• `10 gün` veya `10d`\n"
        f"• `2 hafta` veya `2w`\n"
        f"• `1 ay` veya `1m`\n"
        f"• `1 yıl` veya `1y`\n"
        f"• `3 saat` veya `3h`\n\n"
        f"*Tarih Formatı:*\n"
        f"• `GG.AA.YY SS:DD`\n"
        f"• Örnek: `25.12.25 14:30`\n\n"
        f"*İpuçları:*\n"
        f"• Random hesap daha hızlıdır\n"
        f"• Güçlü şifreler otomatik oluşturulur\n"
        f"• Premium hesaplar özel özellikler içerir"
    )
    
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
@admin_only
@log_action('stats')
def show_statistics(message):
    """İstatistikleri gösterir."""
    success_rate = 0
    if statistics['total_registrations'] > 0:
        success_rate = (statistics['successful_registrations'] / statistics['total_registrations']) * 100
    
    stats_text = (
        f"{EMOJI['stats']} *Sistem İstatistikleri*\n"
        f"{'═' * 35}\n\n"
        f"*Genel:*\n"
        f"Toplam Kayıt: `{statistics['total_registrations']}`\n"
        f"Başarılı: `{statistics['successful_registrations']}` {EMOJI['success']}\n"
        f"Başarısız: `{statistics['failed_registrations']}` {EMOJI['error']}\n"
        f"Başarı Oranı: `{success_rate:.1f}%`\n\n"
        f"*Hesap Tipleri:*\n"
        f"Random: `{statistics['random_accounts']}` {EMOJI['random']}\n"
        f"Özel: `{statistics['custom_accounts']}` {EMOJI['custom']}\n\n"
        f"*Üyelik Tipleri:*\n"
        f"Premium: `{statistics['premium_accounts']}` {EMOJI['premium']}\n"
        f"Normal: `{statistics['normal_accounts']}` {EMOJI['star']}\n"
        f"{'═' * 35}"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(f"{EMOJI['refresh']} Yenile", callback_data='menu_stats'),
        types.InlineKeyboardButton(f"{EMOJI['back']} Ana Menü", callback_data='main_menu')
    )
    
    bot.send_message(message.chat.id, stats_text, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['cancel'])
@admin_only
def cancel_registration(message):
    """Kayıt işlemini iptal eder."""
    if message.from_user.id in user_data:
        # Devam eden adımı iptal et
        try:
            bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
        except Exception as e:
            logging.warning(f"Adım işleyici temizlenemedi: {e}")
            
        del user_data[message.from_user.id]
        bot.send_message(
            message.chat.id,
            f"{EMOJI['cancel']} İşlem iptal edildi.\n\n"
            "Yeni işlem için /start komutunu kullanın.",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        bot.send_message(
            message.chat.id,
            f"{EMOJI['info']} Devam eden bir işlem yok."
        )

@bot.message_handler(commands=['register'])
@admin_only
@log_action('register')
def register_start(message):
    """Hızlı kayıt başlatır."""
    user_data[message.from_user.id] = {}
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            f"{EMOJI['random']} Random Hesap (Hızlı)", 
            callback_data='register_random'
        ),
        types.InlineKeyboardButton(
            f"{EMOJI['custom']} Özel Hesap (Detaylı)", 
            callback_data='register_custom'
        )
    )
    
    register_text = (
        f"{EMOJI['list']} *Kayıt Tipi Seçin*\n"
        f"{'═' * 35}\n\n"
        f"{EMOJI['random']} *Random Hesap*\n"
        f"• Otomatik kullanıcı adı/e-posta/şifre\n"
        f"• Sadece süre belirlemeniz yeterli\n\n"
        f"{EMOJI['custom']} *Özel Hesap*\n"
        f"• Tamamen özel kullanıcı bilgileri\n"
        f"• Tam kontrol\n\n"
        f"İptal için: /cancel"
    )
    
    bot.send_message(message.chat.id, register_text, reply_markup=keyboard, parse_mode='Markdown')

# -----------------------------------------------------------------------------
# CALLBACK HANDLERS - MENÜ
# -----------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
@admin_only
def show_main_menu(call):
    """Ana menüyü gösterir."""
    welcome_text = (
        f"{EMOJI['robot']} *Ana Menü*\n"
        f"{'═' * 35}\n\n"
        f"Yapmak istediğiniz işlemi seçin:"
    )
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(f"{EMOJI['random']} Random Hesap", callback_data='menu_register_random'),
        types.InlineKeyboardButton(f"{EMOJI['custom']} Özel Hesap", callback_data='menu_register_custom'),
        types.InlineKeyboardButton(f"{EMOJI['stats']} İstatistikler", callback_data='menu_stats'),
        types.InlineKeyboardButton(f"{EMOJI['settings']} Ayarlar", callback_data='menu_settings')
    )
    
    bot.edit_message_text(
        welcome_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
@admin_only
def handle_menu(call):
    """Menü seçimlerini yönetir."""
    action = call.data.replace('menu_', '')
    
    if action == 'register_random':
        # register_start fonksiyonundaki inline butonları tetikler
        call.data = 'register_random'
        choose_register_flow(call)
    elif action == 'register_custom':
        # register_start fonksiyonundaki inline butonları tetikler
        call.data = 'register_custom'
        choose_register_flow(call)
    elif action == 'stats':
        show_statistics_callback(call)
    elif action == 'settings':
        show_settings(call)

def show_statistics_callback(call):
    """İstatistikleri callback olarak gösterir."""
    success_rate = 0
    if statistics['total_registrations'] > 0:
        success_rate = (statistics['successful_registrations'] / statistics['total_registrations']) * 100
    
    stats_text = (
        f"{EMOJI['stats']} *Sistem İstatistikleri*\n"
        f"{'═' * 35}\n\n"
        f"*Genel:*\n"
        f"Toplam Kayıt: `{statistics['total_registrations']}`\n"
        f"Başarılı: `{statistics['successful_registrations']}` {EMOJI['success']}\n"
        f"Başarısız: `{statistics['failed_registrations']}` {EMOJI['error']}\n"
        f"Başarı Oranı: `{success_rate:.1f}%`\n\n"
        f"*Hesap Tipleri:*\n"
        f"Random: `{statistics['random_accounts']}` {EMOJI['random']}\n"
        f"Özel: `{statistics['custom_accounts']}` {EMOJI['custom']}\n\n"
        f"*Üyelik Tipleri:*\n"
        f"Premium: `{statistics['premium_accounts']}` {EMOJI['premium']}\n"
        f"Normal: `{statistics['normal_accounts']}` {EMOJI['star']}\n"
        f"{'═' * 35}"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(f"{EMOJI['refresh']} Yenile", callback_data='menu_stats'),
        types.InlineKeyboardButton(f"{EMOJI['back']} Ana Menü", callback_data='main_menu')
    )
    
    bot.edit_message_text(
        stats_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

def show_settings(call):
    """Ayarlar menüsünü gösterir."""
    settings_text = (
        f"{EMOJI['settings']} *Ayarlar*\n"
        f"{'═' * 35}\n\n"
        f"*Bot Bilgileri:*\n"
        f"Versiyon: `2.0 Advanced`\n"
        f"Admin Sayısı: `{len(ADMIN_ID)}`\n"
        f"Aktif Oturum: `{len(user_data)}`\n\n"
        f"*Özellikler:*\n"
        f"• Gelişmiş kayıt sistemi\n"
        f"• İstatistik takibi\n"
        f"• Otomatik şifre oluşturma\n"
        f"• Detaylı loglama\n\n"
        f"*Yapılandırma:*\n"
        f"• Full Başarılı Deuslra Checker"
    )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(f"{EMOJI['back']} Ana Menü", callback_data='main_menu'))
    
    bot.edit_message_text(
        settings_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

# -----------------------------------------------------------------------------
# CALLBACK HANDLERS - KAYIT AKIŞI BAŞLANGIÇ
# -----------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data in ['register_random', 'register_custom'])
@admin_only
def choose_register_flow(call):
    """Random veya Özel hesap kayıt akışını başlatır."""
    user_id = call.from_user.id
    
    # Mevcut adım işleyicilerini temizle
    try:
        bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
    except Exception:
        pass
        
    if call.data == 'register_random':
        user_data[user_id] = {'type': 'register_random'}
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(f"{EMOJI['premium']} Premium Hesap", callback_data='random_premium_select'),
            types.InlineKeyboardButton(f"{EMOJI['star']} Normal Hesap", callback_data='random_normal_select'),
            types.InlineKeyboardButton(f"{EMOJI['back']} Geri", callback_data='main_menu')
        )
        
        bot.edit_message_text(
            f"{EMOJI['random']} *Random Hesap Oluşturma*\n"
            f"{'═' * 35}\n\n"
            f"Lütfen oluşturulacak hesabın *üyelik tipini* seçin:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif call.data == 'register_custom':
        user_data[user_id] = {'type': 'register_custom', 'step': 'ask_username'}
        
        bot.edit_message_text(
            f"{EMOJI['custom']} *Özel Hesap Oluşturma*\n"
            f"{'═' * 35}\n\n"
            f"{EMOJI['user']} Lütfen *kullanıcı adını* girin:\n"
            f"(İptal için /cancel)",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(call.message, get_custom_username)
        bot.answer_callback_query(call.id)

# -----------------------------------------------------------------------------
# RANDOM HESAP AKIŞI HANDLERS
# -----------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data.startswith('random_'))
@admin_only
def select_random_account_type(call):
    """Random hesap için Premium/Normal seçimi sonrası süre sorar."""
    user_id = call.from_user.id
    
    if user_id not in user_data or user_data[user_id].get('type') != 'register_random':
        bot.answer_callback_query(call.id, f"{EMOJI['error']} İşlem zaman aşımına uğradı.")
        return show_main_menu(call)
    
    is_premium = '1' if 'premium' in call.data else '0'
    user_data[user_id]['premium'] = is_premium
    user_data[user_id]['step'] = 'ask_duration'
    
    bot.edit_message_text(
        f"{EMOJI['clock']} *Süre Belirleme*\n"
        f"{'═' * 35}\n\n"
        f"Lütfen hesabın ne kadar süre geçerli olacağını belirtin.\n\n"
        f"*Örnekler:*\n"
        f"• `30 gün` veya `30d`\n"
        f"• `1 yıl` veya `1y`\n"
        f"• `24 saat` veya `24h`\n\n"
        f"(İptal için /cancel)",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, process_random_duration)
    bot.answer_callback_query(call.id)

@admin_only
def process_random_duration(message):
    """Random hesap için süreyi işler ve kaydı tamamlar."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if message.text == '/cancel':
        return cancel_registration(message)
    
    if user_id not in user_data or user_data[user_id].get('type') != 'register_random':
        return bot.send_message(chat_id, f"{EMOJI['error']} Geçersiz işlem akışı. Lütfen /start ile başlayın.")
    
    future_date_str, error = parse_time_duration(message.text)
    
    if error:
        msg = bot.send_message(
            chat_id,
            f"{EMOJI['error']} *Geçersiz Süre Formatı!*\n"
            f"Hata: {error}\n\n"
            f"Lütfen süreyi doğru formatta tekrar girin:",
            parse_mode='Markdown'
        )
        return bot.register_next_step_handler(msg, process_random_duration)
    
    # Hesap Bilgilerini Oluştur
    premium_style = 'premium' if user_data[user_id]['premium'] == '1' else 'default'
    
    user_data[user_id]['username'] = generate_random_username(style=premium_style)
    user_data[user_id]['email'] = generate_random_email(style=premium_style)
    user_data[user_id]['password'] = generate_random_password(strong=True)
    user_data[user_id]['register_date'] = future_date_str
    
    # Onay Adımı
    send_registration_confirmation(message, user_data[user_id])

# -----------------------------------------------------------------------------
# ÖZEL HESAP AKIŞI HANDLERS
# -----------------------------------------------------------------------------

@admin_only
def get_custom_username(message):
    """Özel hesap için kullanıcı adını alır."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if message.text == '/cancel':
        return cancel_registration(message)
        
    if user_id not in user_data or user_data[user_id].get('type') != 'register_custom':
        return bot.send_message(chat_id, f"{EMOJI['error']} Geçersiz işlem akışı. Lütfen /start ile başlayın.")

    user_data[user_id]['username'] = message.text
    user_data[user_id]['step'] = 'ask_email'
    
    msg = bot.send_message(
        chat_id,
        f"{EMOJI['email']} Lütfen *e-posta adresini* girin:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, get_custom_email)

@admin_only
def get_custom_email(message):
    """Özel hesap için e-posta adresini alır."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if message.text == '/cancel':
        return cancel_registration(message)
        
    if user_id not in user_data or user_data[user_id].get('type') != 'register_custom':
        return bot.send_message(chat_id, f"{EMOJI['error']} Geçersiz işlem akışı. Lütfen /start ile başlayın.")
    
    if not check_email_format(message.text):
        msg = bot.send_message(
            chat_id,
            f"{EMOJI['error']} Geçersiz e-posta formatı. Lütfen tekrar girin:",
            parse_mode='Markdown'
        )
        return bot.register_next_step_handler(msg, get_custom_email)

    user_data[user_id]['email'] = message.text
    user_data[user_id]['step'] = 'ask_password'
    
    msg = bot.send_message(
        chat_id,
        f"{EMOJI['password']} Lütfen *şifreyi* girin:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, get_custom_password)

@admin_only
def get_custom_password(message):
    """Özel hesap için şifreyi alır."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if message.text == '/cancel':
        return cancel_registration(message)
        
    if user_id not in user_data or user_data[user_id].get('type') != 'register_custom':
        return bot.send_message(chat_id, f"{EMOJI['error']} Geçersiz işlem akışı. Lütfen /start ile başlayın.")

    user_data[user_id]['password'] = message.text
    user_data[user_id]['step'] = 'ask_premium'
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(f"{EMOJI['premium']} Premium", callback_data='custom_premium_select'),
        types.InlineKeyboardButton(f"{EMOJI['star']} Normal", callback_data='custom_normal_select')
    )
    
    bot.send_message(
        chat_id,
        f"{EMOJI['premium']} Lütfen *üyelik tipini* seçin:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    # Bir sonraki adım callback ile işlenecek

@bot.callback_query_handler(func=lambda call: call.data.startswith('custom_'))
@admin_only
def select_custom_account_type(call):
    """Özel hesap için Premium/Normal seçimi sonrası bitiş tarihi sorar."""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if user_id not in user_data or user_data[user_id].get('type') != 'register_custom':
        bot.answer_callback_query(call.id, f"{EMOJI['error']} İşlem zaman aşımına uğradı.")
        return show_main_menu(call)
    
    is_premium = '1' if 'premium' in call.data else '0'
    user_data[user_id]['premium'] = is_premium
    user_data[user_id]['step'] = 'ask_date'
    
    bot.edit_message_text(
        f"{EMOJI['calendar']} *Bitiş Tarihi Belirleme*\n"
        f"{'═' * 35}\n\n"
        f"Lütfen hesabın *bitiş tarihini* (örn: `25.12.25 14:30`) veya *süresini* (örn: `1 yıl`) girin:\n\n"
        f"(İptal için /cancel)",
        chat_id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, process_custom_date)
    bot.answer_callback_query(call.id)


@admin_only
def process_custom_date(message):
    """Özel hesap için bitiş tarihini/süresini işler ve kaydı tamamlar."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if message.text == '/cancel':
        return cancel_registration(message)
        
    if user_id not in user_data or user_data[user_id].get('type') != 'register_custom':
        return bot.send_message(chat_id, f"{EMOJI['error']} Geçersiz işlem akışı. Lütfen /start ile başlayın.")
    
    input_text = message.text.strip()
    future_date_str = None
    error = "Geçersiz format"
    
    # 1. Tam tarih formatını kontrol et (GG.AA.YY SS:DD)
    valid_date, date_error = validate_date_format(input_text)
    
    if valid_date:
        future_date_str = input_text
    else:
        # 2. Süre formatını dene (1 yıl, 10d, vb.)
        future_date_str, duration_error = parse_time_duration(input_text)
        if not future_date_str:
             error = f"Geçersiz tarih ({date_error}) veya süre ({duration_error}) formatı."
        
    if not future_date_str:
        msg = bot.send_message(
            chat_id,
            f"{EMOJI['error']} *Geçersiz Tarih/Süre Formatı!*\n"
            f"Hata: {error}\n\n"
            f"Lütfen doğru formatta (GG.AA.YY SS:DD veya süre) tekrar girin:",
            parse_mode='Markdown'
        )
        return bot.register_next_step_handler(msg, process_custom_date)
    
    user_data[user_id]['register_date'] = future_date_str
    
    # Onay Adımı
    send_registration_confirmation(message, user_data[user_id])


# -----------------------------------------------------------------------------
# CALLBACK HANDLERS - FİNAL ONAY VE API ÇAĞRISI
# -----------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: call.data.startswith('final_register_'))
@admin_only
@log_action('final_confirmation')
def final_register_action(call):
    """Kayıt işlemini onaylar veya iptal eder."""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if user_id not in user_data:
        bot.answer_callback_query(call.id, f"{EMOJI['error']} İşlem zaman aşımına uğradı veya iptal edildi.")
        return show_main_menu(call)
    
    if call.data == 'final_register_cancel':
        del user_data[user_id]
        bot.edit_message_text(
            f"{EMOJI['cancel']} Kayıt işlemi iptal edildi.",
            chat_id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return
        
    elif call.data == 'final_register_confirm':
        data_to_register = user_data.pop(user_id) # Veriyi al ve user_data'dan sil
        
        bot.edit_message_text(
            f"{EMOJI['loading']} *Kayıt Başlatılıyor...*\n\n"
            f"Lütfen bekleyin, bilgiler harici API'ye gönderiliyor.",
            chat_id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        
        # API isteğini gönder
        api_result = send_api_request(data_to_register)
        
        final_message = ""
        if api_result.get('success'):
            final_message = (
                f"{EMOJI['success']} *Kayıt Başarılı!* {EMOJI['check']}\n"
                f"{'═' * 35}\n\n"
                f"Hesap başarıyla kaydedildi:\n\n"
                f"{get_account_info_message(data_to_register)}\n\n"
                f"*API Mesajı:* `{escape_markdown(api_result.get('message', 'Başarılı'))}`"
            )
        else:
            final_message = (
                f"{EMOJI['error']} *Kayıt Başarısız Oldu!* {EMOJI['warning']}\n"
                f"{'═' * 35}\n\n"
                f"Hesap kaydedilemedi. Lütfen bilgileri ve API durumunu kontrol edin.\n\n"
                f"*Hata Mesajı:* `{escape_markdown(api_result.get('message', 'Bilinmeyen Hata'))}`\n\n"
                f"*Denenen Bilgiler:*\n"
                f"{EMOJI['user']} `{escape_markdown(data_to_register['username'])}`\n"
                f"{EMOJI['email']} `{escape_markdown(data_to_register['email'])}`"
            )

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"{EMOJI['back']} Ana Menü", callback_data='main_menu'))
        
        bot.edit_message_text(
            final_message,
            chat_id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id, f"{EMOJI['check']} İşlem tamamlandı!")


# -----------------------------------------------------------------------------
# BOTU ÇALIŞTIRMA
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    logging.info("Bot başlatılıyor...")
    while True:
        try:
            # none_stop=True: Hata olsa bile botun durmamasını sağlar
            # interval=1: Polling aralığı (saniye)
            # timeout=20: Bağlantı kesilmeden önceki maksimum bekleme süresi
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            logging.error(f"Polling Hatası: {e}")
            # Hata durumunda 5 saniye bekleyip yeniden dene
            time.sleep(5)
