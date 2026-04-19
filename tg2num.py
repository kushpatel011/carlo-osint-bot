import requests
import telebot
from telebot import types

# API URL (Static)
TG2NUM_API_URL = "https://cyber-osint-tg-num.vercel.app/api/tginfo"

def setup_tg2num_handlers(bot, db_mongo, USERS_COL, get_user, user_states, api_key):
    # 'api_key' variable main file (number_to_info.py) se pass hoga

    @bot.message_handler(func=lambda m: m.text == "🆔 ᴛɢ ᴛᴏ ɴᴜᴍʙᴇʀ")
    def start_tg_lookup(message):
        uid = message.from_user.id
        user_states[uid] = "waiting_tg_id"
        
        prompt = (
            "<b>🆔 ᴛᴇʟᴇɢʀᴀᴍ ɪᴅ ʟᴏᴏᴋᴜᴘ</b>\n"
            "──────────────────────────────\n"
            "📥 <b>ɪɴᴘᴜᴛ ʀᴇǫᴜɪʀᴇᴅ:</b>\n"
            "ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴛᴇʟᴇɢʀᴀᴍ ᴜɪᴅ.\n\n"
            "📝 <b>ᴇxᴀᴍᴘʟᴇ:</b> <code>8215315611</code>\n"
            "🛡️ <b>sᴛᴀᴛᴜs:</b> ᴀᴡᴀɪᴛɪɴɢ ɪᴅ...\n"
            "──────────────────────────────"
        )
        bot.send_message(message.chat.id, prompt, parse_mode="HTML")

    def process_tg_lookup(message, target_id):
        uid = str(message.from_user.id)
        u = get_user(uid)
        channel_link = "https://t.me/+SMMZP8shgK01NWZl"
    # --- ADMIN / OWNER PROTECTION FILTER ---
        # Yahan apni aur apne team ki Telegram IDs daal dein (Numerical form mein)
        PROTECTED_TIDS = ["7582998902", "7066124462"] 
        if str(target_id) in PROTECTED_TIDS:
            return bot.reply_to(
                message, 
                "<b>🛡️ Privacy Protection!</b>\n\nThis User ID is <b>Hidden by Owner</b>. Records cannot be retrieved.", 
                parse_mode="HTML"
        )    
        # Credit Check
        if u['credits'] <= 0 and not u['is_vip']:
            return bot.reply_to(message, "⚠️ <b>Insufficient Credits!</b>", parse_mode="HTML")

        wait = bot.send_message(message.chat.id, "🛰️ <b>Scanning Telegram Database...</b>", parse_mode="HTML")

        try:
            # API Call using the passed variable 'api_key'
            params = {
                "key": api_key,
                "id": target_id
            }
            response = requests.get(TG2NUM_API_URL, params=params, timeout=15)
            res = response.json()

            if res.get("result") == True:
                # Deduct Credits
                if not u['is_vip']:
                    db_mongo[USERS_COL].update_one({"_id": uid}, {"$inc": {"credits": -1}})
                
                phone = res.get("number", "N/A")
                country = res.get("country", "N/A")
                c_code = res.get("country_code", "")
                
                output = (
                    "<b>✅ ᴅᴀᴛᴀ ᴇxᴛʀᴀᴄᴛᴇᴅ!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 <b>ᴛɢ ɪᴅ:</b> <code>{target_id}</code>\n"
                    f"📱 <b>ɴᴜᴍʙᴇʀ:</b> <code>{c_code}{phone}</code>\n"
                    f"📍 <b>ᴄᴏᴜɴᴛʀʏ:</b> <code>{country}</code>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"✨ <b>Powered by: <a href='{channel_link}'>Carlo Dark World</a></b>"
                )
                bot.edit_message_text(output, message.chat.id, wait.message_id, parse_mode="HTML", disable_web_page_preview=True)
            else:
                bot.edit_message_text("❌ <b>No records found for this ID.</b>", message.chat.id, wait.message_id, parse_mode="HTML")

        except Exception as e:
            print(f"TG2NUM Error: {e}")
            bot.edit_message_text("⚠️ <b>API System Busy.</b>", message.chat.id, wait.message_id, parse_mode="HTML")

    return process_tg_lookup
