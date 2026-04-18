import telebot

# --- CONFIGURATION ---
# Yahan us account ki ID dalo jispar Userbot chal raha hai
# Taaki Main bot sirf usi ke messages ko trust kare
USERBOT_OWNER_ID = 8281664372  # Ise apni Userbot account ID se replace karna

# Ye dictionary yaad rakhegi ki data kis group ya user ne manga tha
pending_requests = {}

# --- UTILS: DC & AGE ESTIMATION ---
def get_dc_info(user_id):
    if user_id < 500000000: return "DC1 (Miami)"
    elif user_id < 1000000000: return "DC2 (Amsterdam)"
    elif user_id < 2000000000: return "DC4 (Netherlands)"
    else: return "DC5 (Singapore)"

def estimate_age(user_id):
    if user_id < 100000000: return "Very Old (2013-2015)"
    elif user_id < 500000000: return "Old (2016-2018)"
    elif user_id < 1500000000: return "Mid-Range (2019-2021)"
    else: return "Recent (2022-2026)"

def send_user_info(bot, chat_id, user):
    try:
        uid = user.id
        dc = get_dc_info(uid)
        age = estimate_age(uid)
        username = f"@{user.username}" if user.username else "<code>None</code>"
        
        # Proper user link formation
        user_link = f'<a href="tg://user?id={uid}">Permanent Link</a>'

        res = (
            f"👤 <b>USER INFORMATION REPORT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
            f"👤 <b>First Name:</b> {user.first_name}\n"
            f"👥 <b>Last Name:</b> {user.last_name or 'N/A'}\n"
            f"🔗 <b>Username:</b> {username}\n"
            f"🌐 <b>Data Center:</b> <code>{dc}</code>\n"
            f"📅 <b>Est. Age:</b> <code>{age}</code>\n"
            f"📍 <b>Profile:</b> {user_link}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

        photos = bot.get_user_profile_photos(uid)
        if photos.total_count > 0:
            bot.send_photo(chat_id, photos.photos[0][-1].file_id, caption=res, parse_mode="HTML")
        else:
            bot.send_message(chat_id, res, parse_mode="HTML")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")

# --- MAIN HANDLERS ---
def register_info_handlers(bot):
    
    @bot.message_handler(func=lambda m: m.forward_from is not None or m.forward_sender_name is not None)
    def handle_forward(message):
        if message.forward_from:
            send_user_info(bot, message.chat.id, message.forward_from)
        else:
            bot.reply_to(message, "⚠️ <b>Restricted!</b>\nUser has hidden forward links.", parse_mode="HTML")

    @bot.message_handler(commands=['whois', 'info', 'id'])
    def handle_info_query(message):
        text = message.text.split()
        if len(text) < 2:
            return send_user_info(bot, message.chat.id, message.from_user)
        
        target = text[1].replace("@", "")
        
        # Agar sirf number hai (ID), toh usko int mein convert karna zaroori hai
        if target.isdigit():
            target = int(target)
            
        try:
            # 1. Pehle Main Bot khud local API check karega
            user = bot.get_chat(target)
            send_user_info(bot, message.chat.id, user)
            
        except Exception as e:
            # 2. Agar bot ko user nahi mila, toh wo Userbot ko kaam par lagayega
            if isinstance(target, str):
                bot.reply_to(message, "📡 <b>Local Cache Miss!</b>\nSending request to Global Userbot...", parse_mode="HTML")
                
                # Yaad rakhne ke liye ki info kahan bhejni hai
                pending_requests[target.lower()] = message.chat.id
                
                # Userbot ke private chat mein usko command bhejega
                bot.send_message(USERBOT_OWNER_ID, f".fetch @{target}")
            else:
                bot.reply_to(message, "❌ <b>User not found globally and ID format is incorrect.</b>", parse_mode="HTML")

    # 3. Ye function Userbot se aane wale Result ko catch karega
    @bot.message_handler(func=lambda m: m.chat.id == USERBOT_OWNER_ID)
    def catch_userbot_reply(message):
        # Jab Userbot data bhejega, toh wo is function mein aayega
        # Agar Rose ka reply hai toh wo result aage bhej dega
        if pending_requests:
            # Last pending request uthao
            target, original_chat_id = list(pending_requests.items())[-1]
            
            final_report = f"🔍 <b>EXTERNAL GLOBAL REPORT:</b>\n\n{message.text}"
            
            # Jisne manga tha usko bhej do
            bot.send_message(original_chat_id, final_report, parse_mode="HTML")
            
            # List se delete kar do
            del pending_requests[target]
