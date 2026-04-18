import telebot
from datetime import datetime

# --- UTILS: DC & AGE ESTIMATION ---
def get_dc_info(user_id):
    # Rough estimation based on ID ranges (Common in OSINT)
    if user_id < 500000000: return "DC1 (Miami)"
    elif user_id < 1000000000: return "DC2 (Amsterdam)"
    elif user_id < 2000000000: return "DC4 (Netherlands)"
    else: return "DC5 (Singapore)"

def estimate_age(user_id):
    if user_id < 100000000: return "Very Old (2013-2015)"
    elif user_id < 500000000: return "Old (2016-2018)"
    elif user_id < 1500000000: return "Mid-Range (2019-2021)"
    else: return "Recent (2022-2026)"

# --- MAIN INFO HANDLER ---

@bot.message_handler(func=lambda m: m.forward_from is not None or m.forward_sender_name is not None)
def handle_forward(message):
    if message.forward_from:
        send_user_info(message.chat.id, message.forward_from)
    else:
        bot.reply_to(message, "⚠️ <b>Restricted Account!</b>\nIs user ne apni privacy settings mein forwarding link hide kar rakha hai.", parse_mode="HTML")

@bot.message_handler(commands=['whois', 'info', 'id'])
def handle_info_query(message):
    text = message.text.split()
    if len(text) < 2:
        return send_user_info(message.chat.id, message.from_user)

    target = text[1].replace("@", "")
    try:
        user = bot.get_chat(target)
        send_user_info(message.chat.id, user)
    except Exception:
        bot.reply_to(message, "❌ <b>User not found!</b>", parse_mode="HTML")

def send_user_info(chat_id, user):
    try:
        uid = user.id
        # Database check (Optional)
        db_user = USERS_COL.find_one({"_id": str(uid)}) or {}
        
        # Metadata
        dc = get_dc_info(uid)
        age = estimate_age(uid)
        username = f"@{user.username}" if user.username else "<code>None</code>"
        status = "👑 VIP" if db_user.get("is_vip") else "👤 Free User"
        balance = db_user.get("credits", 0)

        res = (
            f"🔍 <b>DETOR OSINT - USER REPORT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
            f"👤 <b>First:</b> {user.first_name}\n"
            f"👥 <b>Last:</b> {user.last_name or 'N/A'}\n"
            f"🔗 <b>User:</b> {username}\n"
            f"🌐 <b>DC:</b> <code>{dc}</code>\n"
            f"📅 <b>Age:</b> <code>{age}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 <b>Credits:</b> <code>{balance}</code>\n"
            f"🌟 <b>Status:</b> <b>{status}</b>\n"
            f"🔗 <b>Link:</b> <a href='tg://user?id={uid}'>Permanent Link</a>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

        photos = bot.get_user_profile_photos(uid)
        if photos.total_count > 0:
            bot.send_photo(chat_id, photos.photos[0][-1].file_id, caption=res, parse_mode="HTML")
        else:
            bot.send_message(chat_id, res, parse_mode="HTML")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ <b>Error:</b> {e}", parse_mode="HTML")
