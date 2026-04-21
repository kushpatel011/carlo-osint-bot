import telebot
import requests
import json
import os
import time
import threading
from telebot import types
from datetime import datetime
import payment_plugin
from broadcast import register_broadcast_handler
import user_info
import refer_manager
import tg2num
from vehicle_lookup import setup_vehicle_handlers
import stats
import pymongo
from pymongo import MongoClient
import pytz
from admin_cmd import register_admin_handlers

# IST Timezone define karein
IST = pytz.timezone('Asia/Kolkata')

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [7582998902, 7066124462]
OWNER_USERNAME = "@ModexOwner"
CHANNEL_LINK = "https://t.me/+SMMZP8shgK01NWZl"
CHANNEL_ID = -1003398914206
API_BASE_URL = os.getenv("API_BASE_URL")
TG_KEY = os.getenv("TG_KEY")
VEHICLE_API_KEY = os.getenv("VEHICLE_API_KEY")
# MongoDB Setup
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("⚠️ WARNING: MONGO_URI not found in Environment Variables!")
else:
    print("✅ MONGO_URI detected, connecting to database...")

client = MongoClient(MONGO_URI)
db_mongo = client['detor_osint_bot']
# Collections (Centralized Variables)
USERS_COL = "users"
COUPONS_COL = "coupons"
PLANS_COL = "plans"
HIST_COL = "history"
SETTING_COL = "settings" # Fixed: Missing variable added

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}
# --- TIMEOUT FUNCTION ---
def state_timeout(bot, uid, chat_id):
    # 60 seconds wait karega
    import time
    time.sleep(60)
    
    # Check karega ki kya user abhi bhi usi state mein hai
    if user_states.get(uid) == "waiting_number":
        user_states[uid] = None
        timeout_msg = (
            "<b>⏰ ᴛɪᴍᴇᴏᴜᴛ ᴘʀᴏᴛᴏᴄᴏʟ!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ɴᴜᴍʙᴇʀ ᴛᴏ ɪɴғᴏ session has expired.\n\n"
            "ᴘʟᴇᴀsᴇ ᴛᴀᴘ <b>ɴᴜᴍʙᴇʀ ᴛᴏ ɪɴғᴏ</b> ᴀɢᴀɪɴ ᴛᴏ ʀᴇsᴛᴀʀᴛ.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        try:
            bot.send_message(chat_id, timeout_msg, parse_mode="HTML")
        except: pass
# Plugin Linking
print("🔗 Linking Plugin...")
payment_plugin.setup_payment_handlers(bot, ADMIN_IDS)
print("🔗 Plugin Linked!")
user_info.register_info_handlers(bot)
# Stats handlers register karein
stats.setup_stats_handlers(bot, db_mongo, ADMIN_IDS)
# --- ADMIN COMMANDS LOADING ---
register_admin_handlers(bot, ADMIN_IDS, db_mongo, USERS_COL, COUPONS_COL, SETTING_COL)
print("✅ Admin Handlers Linked!")
register_broadcast_handler(bot, ADMIN_IDS, db_mongo, USERS_COL)

def load_db(collection_name):
    col = db_mongo[collection_name]
    data = {}
    try:
        for item in col.find():
            uid = str(item.pop('_id')) 
            data[uid] = item
    except Exception as e:
        print(f"❌ Database Load Error ({collection_name}): {e}")
    return data

def save_db(collection_name, uid, data_to_save):
    col = db_mongo[collection_name]
    try:
        # Create a copy to avoid modifying original dict in-place
        temp_data = data_to_save.copy()
        if '_id' in temp_data:
            temp_data.pop('_id')
        
        col.update_one({'_id': str(uid)}, {'$set': temp_data}, upsert=True)
    except Exception as e:
        print(f"❌ Database Save Error ({collection_name}): {e}")

def get_user(uid, name="Unknown"):
    suid = str(uid)
    if not suid.isdigit(): return None 

    col = db_mongo[USERS_COL]
    user = col.find_one({'_id': suid})
    
    if not user:
        # MongoDB se "global" settings fetch karein
        settings = db_mongo[SETTING_COL].find_one({"_id": "global"}) or {}
        # Agar settings me value nahi milti toh default 3 rakhein
        default_reg_credits = settings.get("default_reg_credit", 3)
        
        new_user = {
            "name": name, 
            "credits": default_reg_credits, 
            "is_vip": False, 
            "total_search": 0, 
            "last_bonus": 0,
            "refer_count": 0,
            "referred_by": None
        }
        save_db(USERS_COL, suid, new_user)
        return new_user
    else:
        # Name Sync Logic
        if name != "Unknown" and user.get("name") == "Unknown":
            col.update_one({'_id': suid}, {'$set': {'name': name}})
            user['name'] = name
            
    return user
    
def is_subscribed(uid):
    try:
        member = bot.get_chat_member(CHANNEL_ID, uid)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except:
        return False

def force_join_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ ᴠᴇʀɪғʏ ᴊᴏɪɴ", callback_data="check_subscription"))
    return markup

# --- LINKING (Yeh margin se chipka hona chahiye, bina kisi space ke) ---
print("🔗 Linking Refer Manager Plugin...")
refer_manager.setup_refer_handlers(bot, get_user)
print("✅ Plugin Linked Successfully!")
# --- TG TO NUMBER HANDLER LINKING ---
# Isse process_tg_lookup variable ban jayega jo handle_text mein kaam aayega
process_tg_lookup = tg2num.setup_tg2num_handlers(bot, db_mongo, USERS_COL, get_user, user_states, TG_KEY)# --- MONGODB DATABASE HANDLERS ---
# ----- VEHICLE NUMBER TO INFO KINKING ---
process_vehicle_lookup = setup_vehicle_handlers(bot, db_mongo, USERS_COL, get_user, user_states, VEHICLE_API_KEY)
# --- KEYBOARDS ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🆔 ᴛɢ ᴛᴏ ɴᴜᴍʙᴇʀ", "🚘 ᴠᴇʜɪᴄʟᴇ ɪɴғᴏ")
    markup.row("🔍 ɴᴜᴍʙᴇʀ ᴛᴏ ɪɴғᴏ", "👤 ᴍʏ ɪᴅ")
    markup.row("🎁 ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ", "💰 ᴅᴀɪʟʏ ʙᴏɴᴜs")
    markup.row("👨‍💻 ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ")
    if uid in ADMIN_IDS: markup.row("🛠 ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ")
    return markup

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    args = message.text.split()
    
    # 1. Pehle check karo user DB mein hai ya nahi (Pura naya hai ya nahi)
    user_exists = db_mongo[USERS_COL].find_one({'_id': uid})

    # 2. Referral Logic: Agar user naya hai aur link se aaya hai
    # Isko SABSE PEHLE rakhna hai, taaki join check se pehle refer count ho jaye
    if not user_exists and len(args) > 1:
        referrer_id = args[1]
        refer_manager.handle_referral(bot, db_mongo, USERS_COL, uid, referrer_id)

    # 3. Ab user fetch/register karo (Agar refer manager ne nahi kiya toh ye karega)
    u = get_user(message.from_user.id, message.from_user.first_name)
    user_states[message.from_user.id] = None

    # 4. --- 🛡️ FORCE JOIN CHECK (Referral ke BAAD) ---
    if not is_subscribed(uid):
        msg = (
            "<b>❌ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴏғғɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ.\n\n"
            "ᴊᴏɪɴ ᴋᴀʀɴᴇ ᴋᴇ ʙᴀᴀᴅ <b>ᴠᴇʀɪғʏ</b> ʙᴜᴛᴛᴏɴ ᴘᴀʀ ᴄʟɪᴄᴋ ᴋᴀʀᴇɪɴ."
        )
        return bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=force_join_keyboard())

        # --- Updated Professional Welcome Message ---
    welcome = (
        f"<b>WELCOME TO CARLO OSINT BOT  // V1.5</b>\n"
        f"──────────────────────────────\n"
        f"🛰️ ᴜsᴇʀ: <code>{message.from_user.first_name}</code>\n"
        f"📡 sʏsᴛᴇᴍ: <code>ᴀᴄᴛɪᴠᴇ [sᴇᴄᴜʀᴇ]</code>\n"
        f"📟 ᴜsᴇʀ ᴜɪᴅ: <code>{message.from_user.id}</code>\n"
        f"──────────────────────────────\n\n"
        f"🚀 <b>ᴄᴏʀᴇ ᴄᴀᴘᴀʙɪʟɪᴛɪᴇs (Features):</b>\n"
        f"├─ 🔍 <b>ᴀᴅᴠᴀɴᴄᴇᴅ ʟᴏᴏᴋᴜᴘ:</b> Get deep info by number.\n"
        f"├─ 👤 <b>ᴛɢ ɪᴅ ᴛᴏ ɴᴜᴍʙᴇʀ ɪɴғᴏ:</b> Convert TG ID to details.\n"
        f"├─ ⚡ <b>ʀᴇᴀʟ-ᴛɪᴍᴇ ᴅᴀᴛᴀ:</b> Ultra-fast API response.\n"
        f"├─ 🎁 <b>ʀᴇғᴇʀ & ᴇᴀʀɴ:</b> Get free credits by inviting.\n"
        f"└─ 🔐 <b>ᴘʀɪᴠᴀᴄʏ:</b> No data logs stored on server.\n\n"
        f"📂 <b>ᴏᴘᴇʀᴀᴛɪᴏɴᴀʟ ᴅɪʀᴇᴄᴛɪᴠᴇs:</b>\n"
        f"├─ Tap <b>🔍 ɴᴜᴍʙᴇʀ ᴛᴏ ɪɴғᴏ</b> to start search.\n"
        f"└─ Tap <b>👤 ᴍʏ ɪᴅ</b> to check your balance.\n\n"
        f"<b>sᴇʟᴇᴄᴛ ᴀ ᴍᴏᴅᴜʟᴇ ʙᴇʟᴏᴡ ᴛᴏ ɪɴɪᴛɪᴀᴛᴇ...</b>\n"
        f"──────────────────────────────\n"
        f"🛡️ <b>ᴏᴡɴᴇʀ:</b> {OWNER_USERNAME}"
    )

    
    video_url = "https://graph.org/file/72bb6bd41e981d66d1cdb-a1436c7780a84951af.mp4"
    try:
        bot.send_video(message.chat.id, video_url, caption=welcome, parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
    except:
        bot.send_message(message.chat.id, welcome, parse_mode="HTML", reply_markup=main_menu(message.from_user.id))


# --- BUTTON HANDLERS ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    text = message.text
    
    # --- YAHAN CHANGE KAREIN ---
    # get_user call karte waqt name pass karein taaki "Unknown" update ho jaye
    u = get_user(uid, message.from_user.first_name)
    
    # Safety: Agar ID galat hai toh yahin stop kar dein
    if not u:
        return
    # ---------------------------

    # User state fetch karein
    current_state = user_states.get(uid)
    
    # Ab iske niche aapka purana IF/ELIF logic jaisa hai waisa hi rehne dein...

    # --- 🛡️ FORCE JOIN CHECK ---
    if not is_subscribed(uid):
        msg = ("<b>❌ ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ!</b>\n━━━━━━━━━━━━━━━━━━━━\nʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴏғғɪᴄɪᴀʟ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ.")
        return bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=force_join_keyboard())

    # --- 1. STATE CHECK (Jab user input de raha ho) ---
    
    # TG ID Lookup Process
    if current_state == "waiting_tg_id":
        if text.isdigit():
            user_states[uid] = None
            return process_tg_lookup(message, text) # tg2num plugin call
        else:
            return bot.reply_to(message, "❌ <b>ɪɴᴠᴀʟɪᴅ ɪᴅ!</b>\nᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ᴛᴇʟᴇɢʀᴀᴍ ᴜɪᴅ (ɴᴜᴍʙᴇʀs ᴏɴʟʏ).", parse_mode="HTML")

    #-----VEHICHLE TO INFO----    
    elif current_state == "waiting_vehicle_num":
        user_states[uid] = None # Reset state
        process_vehicle_lookup(message, message.text.strip().upper())

    # Number Lookup Process
    elif current_state == "waiting_number":
        if text.isdigit() and len(text) == 10:
            user_states[uid] = None
            return process_lookup(message, text)
        else:
            error_msg = "<b>❌ Invalid Input!</b>\n\nᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ <b>10 ᴅɪɢɪᴛ</b> ɴᴜᴍʙᴇʀ."
            return bot.reply_to(message, error_msg, parse_mode="HTML")

    # Redeem Code Process
    elif current_state == "waiting_redeem":
        user_states[uid] = None
        return process_redeem(message, text)

    # --- 2. BUTTONS LOGIC ---
    all_buttons = ["🆔 ᴛɢ ᴛᴏ ɴᴜᴍʙᴇʀ", "🚘 ᴠᴇʜɪᴄʟᴇ ɪɴғᴏ", "🔍 ɴᴜᴍʙᴇʀ ᴛᴏ ɪɴғᴏ", "👤 ᴍʏ ɪᴅ", "💰 ᴅᴀɪʟʏ ʙᴏɴᴜs", "🎁 ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ", "👨‍💻 ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ", "🛠 ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ"]

    if text in all_buttons:
        user_states[uid] = None # Reset state on button click

    if text == "🆔 ᴛɢ ᴛᴏ ɴᴜᴍʙᴇʀ":
        user_states[uid] = "waiting_tg_id"
        prompt = (
            "<b>🆔 ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ ʟᴏᴏᴋᴜᴘ</b>\n"
            "──────────────────────────────\n"
            "📥 <b>ɪɴᴘᴜᴛ ʀᴇǫᴜɪʀᴇᴅ:</b>\n"
            "ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴛᴇʟᴇɢʀᴀᴍ ᴜsᴇʀ ɪᴅ.\n\n"
            "📝 <b>ᴇxᴀᴍᴘʟᴇ:</b> <code>8215315611</code>\n"
            "──────────────────────────────"
        )
        return bot.send_message(message.chat.id, prompt, parse_mode="HTML")

    elif text == "🚘 ᴠᴇʜɪᴄʟᴇ ɪɴғᴏ": # Naya Button
        user_states[uid] = "waiting_vehicle_num"
        bot.send_message(message.chat.id, "<b>🚘 SEND VEHICLE NUMBER:</b>\nExample: <code>MH00XX1234</code>", parse_mode="HTML")

    elif text == "🔍 ɴᴜᴍʙᴇʀ ᴛᴏ ɪɴғᴏ":
        user_states[uid] = "waiting_number"
        threading.Thread(target=state_timeout, args=(bot, uid, message.chat.id), daemon=True).start()
        
        lookup_prompt = (
            "<b>🛰️ ᴇxᴛʀᴀᴄᴛɪᴏɴ ᴘʀᴏᴛᴏᴄᴏʟ: ᴀᴄᴛɪᴠᴇ</b>\n"
            "──────────────────────────────\n"
            "📥 <b>ɪɴᴘᴜᴛ ʀᴇǫᴜɪʀᴇᴅ:</b>\n"
            "ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ɴᴜᴍʙᴇʀ.\n\n"
            "📝 <b>ғᴏʀᴍᴀᴛ:</b> <code>10 DIGITS ONLY</code>\n"
            "⏳ <b>ᴇxᴘɪʀᴇs ɪɴ:</b> <code>60 SECONDS</code>\n"
            "🛡️ <b>sᴛᴀᴛᴜs:</b> ᴀᴡᴀɪᴛɪɴɢ ᴅᴀᴛᴀ...\n"
            "──────────────────────────────\n"
            "⚠️ <i>Do not include +91 or any spaces.</i>"
        )
        return bot.send_message(message.chat.id, lookup_prompt, parse_mode="HTML")
    
    elif text == "👤 ᴍʏ ɪᴅ":
        user_states[uid] = None # State reset
        u = get_user(uid)
        
        # --- Data Extraction ---
        full_name = message.from_user.full_name
        role = "👑 ᴏᴡɴᴇʀ" if uid in ADMIN_IDS else ("💎 ᴠɪᴘ" if u.get('is_vip') else "👤 ᴜsᴇʀ")
        credits = u.get('credits', 0)
        total_search = u.get('total_search', 0)
        ref_count = u.get('refer_count', 0)
        # Maan lete hain har 5 refer par 2 credit milte hain (aapke purane logic ke hisab se)
        earned_credits = (ref_count // 5) * 2 
        
        bot_username = (bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={uid}"

        # --- Professional UI Design ---
        profile_msg = (
            f"<b>─── [ 👤 ʏᴏᴜʀ ᴘʀᴏғɪʟᴇ ] ───</b>\n\n"
            f"📝 <b>ɴᴀᴍᴇ:</b> <code>{full_name}</code>\n"
            f"🆔 <b>ᴜsᴇʀ ɪᴅ:</b> <code>{uid}</code>\n"
            f"──────────────────────\n\n"
            f"<b>📊 [ sʏsᴛᴇᴍ sᴛᴀᴛᴜs ]</b>\n"
            f"├ 🔐 <b>ʀᴏʟᴇ:</b> {role}\n"
            f"├ 💳 <b>ʀᴇᴍᴀɪɴɪɴɢ:</b> <code>{credits if not u.get('is_vip') else '∞'} ᴄʀ</code>\n"
            f"└ 🔍 <b>ᴛᴏᴛᴀʟ sᴇᴀʀᴄʜᴇs:</b> <code>{total_search}</code>\n\n"
            f"<b>👥 [ ʀᴇғᴇʀʀᴀʟ ɪɴsɪɢʜᴛs ]</b>\n"
            f"├ 🤝 <b>ᴛᴏᴛᴀʟ ʀᴇғᴇʀʀᴇᴅ:</b> <code>{ref_count}</code>\n"
            f"└ 🎁 <b>ᴇᴀʀɴᴇᴅ ᴄʀᴇᴅɪᴛs:</b> <code>{earned_credits} ᴄʀ</code>\n\n"
            f"🔗 <b>ɪɴᴠɪᴛᴇ ʟɪɴᴋ:</b>\n"
            f"<code>{ref_link}</code>\n"
            f"──────────────────────"
        )

        try:
            # User ki profile photos fetch karna
            photos = bot.get_user_profile_photos(uid)
            if photos.total_count > 0:
                # Sabse latest photo ka file_id nikalna
                photo_id = photos.photos[0][-1].file_id
                bot.send_photo(message.chat.id, photo_id, caption=profile_msg, parse_mode="HTML")
            else:
                # Agar photo nahi hai toh simple message
                bot.send_message(message.chat.id, profile_msg, parse_mode="HTML")
        except Exception:
            # Privacy error ya kisi aur wajah se photo na dikhe toh
            bot.send_message(message.chat.id, profile_msg, parse_mode="HTML")
        
        return

    elif text == "💰 ᴅᴀɪʟʏ ʙᴏɴᴜs":
        return claim_bonus(message)

    elif text == "🎁 ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇ":
        user_states[uid] = "waiting_redeem"
        return bot.send_message(message.chat.id, "🎟 <b>Enter Coupon Code:</b>", parse_mode="HTML")

    elif text == "👨‍💻 ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ":
        return bot.send_message(message.chat.id, f"<b>Message me here:</b> {OWNER_USERNAME}", parse_mode="HTML")

    elif text == "🛠 ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ" and uid in ADMIN_IDS:
        return show_admin_panel(message)

    # --- 3. STATE HANDLING (Yahi par error aayega agar number galat hua) ---
    current_state = user_states.get(uid)

    if current_state == "waiting_number":
        # Check for 10 digits
        if text.isdigit() and len(text) == 10:
            user_states[uid] = None # Clear state on success
            return process_lookup(message, text)
        else:
            # Random text like "hello", "647" etc will trigger this
            error_msg = "<b>❌ Invalid Input!</b>\n\nᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ <b>10 ᴅɪɢɪᴛ</b> ɴᴜᴍʙᴇʀ.\nᴛᴏ ᴄᴀɴᴄᴇʟ, ᴛᴀᴘ ᴀɴʏ ᴏᴛʜᴇʀ ᴍᴇɴᴜ ʙᴜᴛᴛᴏɴ."
            return bot.reply_to(message, error_msg, parse_mode="HTML")

    elif current_state == "waiting_redeem":
        user_states[uid] = None
        return process_redeem(message, text)

@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    uid = message.from_user.id
    state = user_states.get(uid, "")
    
    if state.startswith("sending_ss"):
        credits = state.split("|")[1]
        user_states[uid] = None
        
        # User ko notification
        bot.reply_to(message, "⏳ <b>ᴠᴇʀɪғʏɪɴɢ...</b>\nʏᴏᴜʀ ᴘʀᴏᴏғ ʜᴀs ʙᴇᴇɴ sᴇɴᴛ ᴛᴏ ᴛʜᴇ ᴀᴅᴍɪɴ.", parse_mode="HTML")
        
        # Admin ko screenshot bhejna
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ ᴀᴘᴘʀᴏᴠᴇ", callback_data=f"p_app_{uid}_{credits}"),
            types.InlineKeyboardButton("❌ ʀᴇᴊᴇᴄᴛ", callback_data=f"p_rej_{uid}_0")
        )
        
        caption = f"💰 <b>ɴᴇᴡ ᴘᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ</b>\n👤 ᴜsᴇʀ: {message.from_user.first_name} ({uid})\n🎫 ᴘʟᴀɴ: {credits} ᴄʀᴇᴅɪᴛs"
        bot.send_photo(ADMIN_IDS, message.photo[-1].file_id, caption=caption, parse_mode="HTML", reply_markup=markup)

# --- CORE FUNCTIONS ---
def claim_bonus(message):
    uid = str(message.from_user.id)
    # MongoDB se settings fetch karna
    settings = db_mongo[SETTING_COL].find_one({"_id": "global"}) or {}
    bonus_amt = settings.get("current_bonus", 0)
    channel_link = "https://t.me/+SMMZP8shgK01NWZl"
    
    if bonus_amt <= 0:
        # Aapka wahi purana professional message style
        no_bonus_text = (
            "<b>🎁 Bonus Status: Inactive</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "There are no active bonuses available at the moment.\n\n"
            "📢 <b>Update:</b> Check our official channel for promo codes and credit giveaways.\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 <b>Channel:</b> <a href='{channel_link}'>CARLO DARK WORLD</a>"
        )
        return bot.send_message(message.chat.id, no_bonus_text, parse_mode="HTML", disable_web_page_preview=True)
    
    # User data fetch karna (Agar user naya hai toh register bhi ho jayega)
    u = get_user(uid, message.from_user.first_name)
    current_time = time.time()
    
    # 24 Hours (86400 seconds) check
    if current_time - u.get('last_bonus', 0) > 86400:
        # MongoDB update: Credits badhao aur time set karo
        db_mongo[USERS_COL].update_one(
            {"_id": uid},
            {
                "$inc": {"credits": bonus_amt}, 
                "$set": {"last_bonus": current_time}
            }
        )
        bot.reply_to(message, f"✅ <b>Success!</b> {bonus_amt} credits have been added to your balance.", parse_mode="HTML")
    else:
        # Already claimed message
        bot.reply_to(message, "❌ <b>Limit Exceeded:</b> You have already claimed your daily bonus. Please return in 24 hours.", parse_mode="HTML")

def process_redeem(message, code):
    uid = str(message.from_user.id)
    code = code.upper().strip()
    
    # 1. Atomic Update: Check and Update in one step
    # Isme hum check kar rahe hain: code exists, uses > 0, aur user ne pehle claim nahi kiya
    coupon = db_mongo[COUPONS_COL].find_one_and_update(
        {
            "_id": code, 
            "uses": {"$gt": 0}, 
            "users": {"$ne": uid}
        },
        {
            "$inc": {"uses": -1},       # Uses 1 kam karo
            "$push": {"users": uid}      # User ID list mein add karo
        },
        return_document=True
    )

    if coupon:
        # 2. Agar coupon mil gaya aur update ho gaya, toh user ko credits do
        amount = coupon.get('amount', 0)
        db_mongo[USERS_COL].update_one(
            {"_id": uid},
            {"$inc": {"credits": amount}}
        )
        bot.reply_to(message, f"✅ <b>sᴜᴄᴄᴇss!</b>\n{amount} ᴄʀᴇᴅɪᴛs ᴀᴅᴅᴇᴅ ᴛᴏ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ.", parse_mode="HTML")
    else:
        # 3. Check karo failure ka kaaran kya hai
        check_cp = db_mongo[COUPONS_COL].find_one({"_id": code})
        
        if not check_cp:
            bot.reply_to(message, "❌ <b>ɪɴᴠᴀʟɪᴅ ᴄᴏᴜᴘᴏɴ!</b>", parse_mode="HTML")
        elif uid in check_cp.get('users', []):
            bot.reply_to(message, "❌ <b>ᴀʟʀᴇᴀᴅʏ ᴄʟᴀɪᴍᴇᴅ!</b>\nYou have already used this code.", parse_mode="HTML")
        elif check_cp.get('uses', 0) <= 0:
            bot.reply_to(message, "❌ <b>ʟɪᴍɪᴛ ᴇxᴄᴇᴇᴅᴇᴅ!</b>\nThis coupon has reached its maximum usage limit.", parse_mode="HTML")

KNOWN_NUMBERS = ["9876543210"] # <--- Yahan apna confirm working number daal do
PROTECTED_NUMBERS = ["9106345424"]
def process_lookup(message, num):
    uid = str(message.from_user.id)
    u_name = message.from_user.first_name
    u = get_user(uid, u_name)
    channel_link = "https://t.me/+SMMZP8shgK01NWZl"
    #--- Crefit Checker
    if u['credits'] <= 0 and not u['is_vip']:    
        # --- Buttons Layout ---
        markup = types.InlineKeyboardMarkup()
        btn_buy = types.InlineKeyboardButton("💳 ʙᴜʏ ᴄʀᴇᴅɪᴛs", callback_data="buy_credits")
        btn_refer = types.InlineKeyboardButton("👥 ʀᴇғᴇʀ & ᴇᴀʀɴ", callback_data="refer_info")
        btn_join = types.InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url="https://t.me/+SMMZP8shgK01NWZl") # Ye button yahan bhi add kar do

        markup.row(btn_buy, btn_refer)
        markup.add(btn_join)
        
        no_credit_msg = (
        "<b>⚠️ Access Denied!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Your account has <b>0 Credits</b> remaining.\n\n"
        "<b>Refill Options:</b>\n"
        "1. 💰 Claim daily rewards via <b>Bonus</b>.\n"
        "2. 👥 <b>Refer 2 friends</b> to get 2 credits FREE!\n"
        "3. 💳 Purchase credits from owner or click buy button.\n"
        "4. 🎟️ <b>Join channel for Redeem Codes!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>Official:</b> <a href='{channel_link}'>CARLO DARK WORLD</a>"
    )
        return bot.send_message(message.chat.id, no_credit_msg, parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)

    # 2. Admin Protection
    if num in PROTECTED_NUMBERS:
        return bot.send_message(message.chat.id, "<b>⚠️ Access Denied!</b> ᴏᴡɴᴇʀ ᴋᴀ ʜɪ ғɪᴇʟᴅɪɴɢ sᴇᴛ ᴋᴀʀɴᴇ ᴋɪ sᴏᴄʜ ʀʜᴀ ʟᴀᴅʟᴇ 😂", parse_mode="HTML")
    # --- SEARCH LOGIC ---
    wait = bot.send_message(message.chat.id, "🔍 Searching...")
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        # --- STAGE 1: SILENT HEALTH CHECK ---
        # Background mein check ki server response de raha hai ya nahi
        check_num = KNOWN_NUMBERS[0]
        try:
            health_res = requests.get(f"{API_BASE_URL}{check_num}", headers=headers, timeout=20).json()
            is_server_live = health_res.get("status") in [True, "true", "True"]
        except:
            is_server_live = False

        # --- STAGE 2: ACTUAL SEARCH ---
        response = requests.get(f"{API_BASE_URL}{num}", headers=headers, timeout=20)
        res = response.json()
        
        status_val = res.get("status")
        results = res.get("results")
        is_success = status_val in [True, "true", "True", "1", 1]

        # Case 1: Success (Data Mil Gaya)
        if is_success and isinstance(results, list) and len(results) > 0:
            if not u['is_vip']: 
                u['credits'] -= 1
            u['total_search'] += 1
            save_db(USERS_COL, uid, u)

            for item in results:
                target_name = item.get('NAME', 'N/A')
                
                log_entry = {
                    "timestamp": datetime.now().strftime('%d/%m %H:%M'), 
                    "uid": uid, "u_name": u_name, "target": num, "name": target_name
                }
                save_db(HIST_COL, f"log_{int(time.time()*1000)}", log_entry)

                output = (
                    f"👤 <b>REAL NAME:</b> <code>{target_name}</code>\n"
                    f"👨 <b>FATHER NAME:</b> <code>{item.get('fname', 'N/A')}</code>\n"
                    f"👨 <b>MOTHER NAME:</b> <code>{item.get('mname', 'N/A')}</code>\n"
                    f"🆔 <b>ADHAAR ID:</b> <code>{item.get('id', 'N/A')}</code>\n"
                    f"📱 <b>PRIMARY NUMBER:</b> <code>{item.get('MOBILE', num)}</code>\n"
                    f"📞 <b>ALTERNATIVE NUMBER:</b> <code>{item.get('alt', 'N/A')}</code>\n"
                    f"📧 <b>EMAIL:</b> <code>{item.get('EMAIL', 'N/A')}</code>\n"
                    f"📍 <b>CIRCLE/SIM:</b> <code>{item.get('circle', 'N/A')}</code>\n"
                    f"🏠 <b>ADDRESS:</b> <code>{item.get('ADDRESS', 'N/A')}</code>\n\n"
                    f"✨ <b>Powered by: {OWNER_USERNAME}</b>"
                )
                bot.send_message(message.chat.id, output, parse_mode="HTML")
            
            bot.delete_message(message.chat.id, wait.message_id)
        
        # Case 2: Error ya No Record (Using Logic Gate)
        else:
            if is_server_live:
                # Agar hamara background check pass ho gaya, matlab server up hai. 
                # Ab agar user ka record nahi mila, toh ye pakka "No Records" hai.
                bot.edit_message_text("❌ <b>No records found for this number.</b>", message.chat.id, wait.message_id, parse_mode="HTML")
            else:
                # Agar background check fail ho gaya, matlab sach mein Maintenance/Server issue hai.
                error_msg = results if isinstance(results, str) else "API Error or Maintenance."
                bot.edit_message_text(f"❌ <b>API System Busy</b>\n⚠️ {error_msg}", message.chat.id, wait.message_id, parse_mode="HTML")
            
    except Exception as e:
        print(f"Error logic: {e}")
        bot.edit_message_text("⚠️ <b>Connection Error.</b>\nPlease try again later.", message.chat.id, wait.message_id, parse_mode="HTML")
        
                
# --- ADMIN PANEL & STEPS ---
def show_admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Credit", callback_data="adm_add"),
        types.InlineKeyboardButton("👑 Add VIP", callback_data="adm_vip"),
        types.InlineKeyboardButton("🎟 Gen Coupon", callback_data="adm_gen"),
        types.InlineKeyboardButton("📜 History", callback_data="adm_hist"),
        types.InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
        types.InlineKeyboardButton("💰 Set Bonus", callback_data="adm_bonus")
    )
    bot.send_message(message.chat.id, "🛠 <b>ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ</b>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
   # 🛡️ Sabse pehle Verification check (Check Subscription)
    if call.data == "check_subscription":
        if is_subscribed(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ Thanks for joining! Access Granted.")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            # Access milne ke baad main menu bhej rahe hain
            bot.send_message(call.message.chat.id, "🚀 **sʏsᴛᴇᴍ ʀᴇᴀᴅʏ!** Choose an option:", reply_markup=main_menu(call.from_user.id))
        else:
            bot.answer_callback_query(call.id, "⚠️ You haven't joined yet!", show_alert=True)

    # 🛠️ ADMIN PANEL CALLBACKS
    if call.data == "adm_add":
        msg = bot.send_message(call.message.chat.id, "Enter ID and Amount:")
        bot.register_next_step_handler(msg, admin_add_credit)
    elif call.data == "adm_vip":
        msg = bot.send_message(call.message.chat.id, "Enter User ID for VIP:")
        bot.register_next_step_handler(msg, admin_add_vip)
    elif call.data == "adm_gen":
        msg = bot.send_message(call.message.chat.id, "Format: CODE AMOUNT USERS")
        bot.register_next_step_handler(msg, admin_gen_coupon)
    elif call.data == "adm_bonus":
        msg = bot.send_message(call.message.chat.id, "Enter Bonus Amount:")
        bot.register_next_step_handler(msg, admin_set_bonus)
    elif call.data == "adm_hist":
        # MongoDB se latest 10 logs uthana (Latest first)
        hist_data = list(db_mongo[HIST_COL].find().sort("timestamp", -1).limit(10))
        
        if not hist_data: 
            return bot.send_message(call.message.chat.id, "❌ <b>Empty History.</b>", parse_mode="HTML")
            
        res = "📜 <b>LATEST SEARCH LOGS</b>\n━━━━━━━━━━━━━━\n"
        
        # Sahi Indentation yahan hai:
        for log in hist_data:
            # Data fields extract karna
            uid = log.get('uid', 'N/A')
            u_name = log.get('u_name', 'Unknown')
            target = log.get('target', 'N/A')
            name = log.get('name', 'N/A')
            
            # Database se saved time uthao, default current IST
            ts = log.get('timestamp', datetime.now(IST).strftime('%d/%m %H:%M'))
            
            # Professional Formatting
            user_lnk = f"<a href='tg://user?id={uid}'>{u_name}</a>"
            res += (
                f"🕒 <code>{ts}</code>\n"
                f"👤 {user_lnk}\n"
                f"➔ 🔍 <code>{target}</code> ({name})\n\n"
            )
        
        bot.send_message(call.message.chat.id, res + "━━━━━━━━━━━━━━", parse_mode="HTML")

    elif call.data == "adm_stats":
        # MongoDB counts fetch karna
        total_users = db_mongo[USERS_COL].count_documents({})
        vip_users = db_mongo[USERS_COL].count_documents({"is_vip": True})
        
        # Total searches calculate karna
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_search"}}}]
        search_result = list(db_mongo[USERS_COL].aggregate(pipeline))
        total_queries = search_result[0]['total'] if search_result else 0
        
        # Coupon count
        total_coupons = db_mongo[COUPONS_COL].count_documents({})
        
        # stats format
        stats_msg = (
            "📊 <b>CARLO SYSTEM STATS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Total Users:</b> <code>{total_users}</code>\n"
            f"👑 <b>VIP Members:</b> <code>{vip_users}</code>\n"
            f"🔍 <b>Total Queries:</b> <code>{total_queries}</code>\n"
            f"🎟 <b>Active Coupons:</b> <code>{total_coupons}</code>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>Status:</b> <code>Online</code>"
        )
        bot.send_message(call.message.chat.id, stats_msg, parse_mode="HTML")

def admin_add_credit(message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            return bot.reply_to(message, "⚠️ <b>Format:</b> <code>[User_ID] [Amount]</code>", parse_mode="HTML")
            
        tid, amt = parts[0], parts[1]
        
        # Validation: ID numerical honi chahiye aur Amount number hona chahiye
        if not tid.isdigit():
            return bot.reply_to(message, "❌ <b>Error:</b> Invalid User ID format.")
        if not amt.replace("-", "").isdigit():
            return bot.reply_to(message, "❌ <b>Error:</b> Amount must be a number.")

        # Database matching (ID as string)
        user = db_mongo[USERS_COL].find_one({"_id": str(tid)})
        if not user:
            return bot.reply_to(message, f"❌ <b>Error:</b> User <code>{tid}</code> database mein nahi hai.", parse_mode="HTML")

        # Credit Update
        db_mongo[USERS_COL].update_one({"_id": str(tid)}, {"$inc": {"credits": int(amt)}})
        bot.reply_to(message, f"✅ <b>{amt}</b> Credits added to <code>{tid}</code>.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "❌ Error processing request.")

def admin_add_vip(message):
    try:
        tid = message.text.strip()
        
        # Validation
        if not tid.isdigit():
            return bot.reply_to(message, "❌ <b>Error:</b> Please provide a valid numerical User ID.")

        user = db_mongo[USERS_COL].find_one({"_id": str(tid)})
        if not user:
            return bot.reply_to(message, f"❌ <b>Error:</b> Users <code>{tid}</code> not found.", parse_mode="HTML")

        db_mongo[USERS_COL].update_one({"_id": str(tid)}, {"$set": {"is_vip": True}})
        bot.reply_to(message, f"👑 <code>{tid}</code> is now a **VIP Member**!", parse_mode="HTML")
    except Exception as e:
       return bot.reply_to(message, "❌ Unexpected error.")

def admin_gen_coupon(message):
    try:
        # User input: "GIFT 100 5" (No command here)
        parts = message.text.split()
        
        # Check for 3 parts: code, amount, uses
        if len(parts) != 3:
            return bot.reply_to(message, "⚠️ <b>Invalid Format!</b>\nᴘʟᴇᴀsᴇ sᴇɴᴅ: <code>CODE AMT USES</code>\nExample: <code>OFFER50 50 10</code>", parse_mode="HTML")
            
        code = parts[0].upper()
        amt = parts[1]
        uses = parts[2]
        
        # Validation
        if not amt.isdigit() or not uses.isdigit():
            return bot.reply_to(message, "❌ <b>Error:</b> Amount and Users must be numbers.", parse_mode="HTML")

        # MongoDB Update
        db_mongo[COUPONS_COL].update_one(
            {"_id": code},
            {"$set": {
                "amount": int(amt), 
                "uses": int(uses), 
                "users": [] 
            }},
            upsert=True
        )
        
        # State clear karna mat bhulna
        user_states[message.from_user.id] = None
        
        res = (
            f"🎟 <b>ᴄᴏᴜᴘᴏɴ ɢᴇɴᴇʀᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎫 <b>ᴄᴏᴅᴇ:</b> <code>{code}</code>\n"
            f"💰 <b>ᴠᴀʟᴜᴇ:</b> <code>{amt} Credits</code>\n"
            f"👥 <b>ᴜsᴀɢᴇ ʟɪᴍɪᴛ:</b> <code>{uses} Users</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(message.chat.id, res, parse_mode="HTML")

    except Exception as e:
        print(f"Coupon Error: {e}")
        return bot.reply_to(message, "❌ <b>Format Error!</b> Use: <code>CODE AMT USES</code>", parse_mode="HTML")

def admin_set_bonus(message):
    val = message.text.strip()
    
    # Strictly check if the message is only digits
    if val.isdigit():
        db_mongo[SETTING_COL].update_one(
            {"_id": "global"}, 
            {"$set": {"current_bonus": int(val)}}, 
            upsert=True
        )
        bot.reply_to(message, f"💰 <b>Daily Bonus<b> updated to: <b>{val}</b> Credits", parse_mode="HTML")
    else:
       return bot.reply_to(message, "❌ <b>Error:</b> Please send a valid number for bonus.")

if __name__ == "__main__":
    print("🚀 Bot is flying...")
    bot.infinity_polling()
    
