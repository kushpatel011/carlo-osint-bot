import requests
import telebot
from telebot import types

# API Configuration
VEHICLE_API_URL = "https://cyber-vechile2-number.vercel.app/api/vehicleinfo"

def setup_vehicle_handlers(bot, db_mongo, USERS_COL, get_user, user_states, api_key):
    
    def process_vehicle_lookup(message, vehicle_num):
        uid = str(message.from_user.id)
        u = get_user(uid)
        channel_link = "https://t.me/+SMMZP8shgK01NWZl"
        
        if not u:
            return bot.send_message(message.chat.id, "❌ User not found. Please /start.")

        # 1. 💳 CREDIT CHECK
        if u['credits'] <= 0 and not u['is_vip']:
            markup = types.InlineKeyboardMarkup()
            btn_buy = types.InlineKeyboardButton("💳 ʙᴜʏ ᴄʀᴇᴅɪᴛs", callback_data="buy_credits")
            btn_refer = types.InlineKeyboardButton("👥 ʀᴇғᴇʀ & ᴇᴀʀɴ", callback_data="refer_info")
            btn_join = types.InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=channel_link)
            markup.row(btn_buy, btn_refer)
            markup.add(btn_join)

            insufficient_msg = (
                "<b>⚠️ ɪɴsᴜғғɪᴄɪᴇɴᴛ ʙᴀʟᴀɴᴄᴇ!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ʜᴀs <b>0 ᴄʀᴇᴅɪᴛs</b> ʀᴇᴍᴀɪɴɪɴɢ.\n\n"
                "<b>ʜᴏᴡ ᴛᴏ ɢᴇᴛ ᴍᴏʀᴇ?</b>\n"
                "1️⃣ <b>ʀᴇғᴇʀ:</b> ɪɴᴠɪᴛᴇ ғʀɪᴇɴᴅs ᴛᴏ ᴇᴀʀɴ ᴄʀᴇᴅɪᴛs.\n"
                "2️⃣ <b>ᴘᴜʀᴄʜᴀsᴇ:</b> ʙᴜʏ ɪɴsᴛᴀɴᴛ ᴄʀᴇᴅɪᴛs ᴠɪᴀ ᴜᴘɪ.\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📡 <b>ᴏғғɪᴄɪᴀʟ:</b> <a href='{channel_link}'>ᴄᴀʀʟᴏ ᴅᴀʀᴋ ᴡᴏʀʟᴅ</a>"
            )
            return bot.send_message(message.chat.id, insufficient_msg, parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)

        # 2. 🛰️ SEND WAIT MESSAGE (Ye line zaroori hai)
        wait = bot.send_message(message.chat.id, f"🔍 <b>sᴄᴀɴɴɪɴɢ:</b> <code>{vehicle_num}</code>...", parse_mode="HTML")

        try:
            # API Call
            params = {"key": api_key, "rc": vehicle_num}
            response = requests.get(VEHICLE_API_URL, params=params, timeout=20)
            res = response.json()

            if res.get("status") == True:
                # Deduct Credits for non-VIPs
                if not u['is_vip']:
                    db_mongo[USERS_COL].update_one({"_id": uid}, {"$inc": {"credits": -1}})
                
                # --- DATA EXTRACTION ---
                results = res.get("results", {})
                owner = results.get("Ownership Details", {})
                vehicle = results.get("Vehicle Details", {})
                dates = results.get("Important Dates & Validity", {})
                insurance = results.get("Insurance Information", {})
                card = results.get("Basic Card Info", {})

                # 📝 Formatting Final Output
                output = (
                    "<b>🚘 ᴠᴇʜɪᴄʟᴇ ᴏsɪɴᴛ ʀᴇᴘᴏʀᴛ</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 <b>ᴏᴡɴᴇʀ:</b> <code>{owner.get('Owner Name', 'N/A')}</code>\n"
                    f"🔢 <b>ʀᴇɢ ɴᴏ:</b> <code>{vehicle_num}</code>\n"
                    f"🏢 <b>ʀᴛᴏ:</b> <code>{owner.get('Registered RTO', 'N/A')}</code>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏍️ <b>ᴍᴀᴋᴇʀ:</b> <code>{vehicle.get('Model Name', 'N/A')}</code>\n"
                    f"🚲 <b>ᴍᴏᴅᴇʟ:</b> <code>{vehicle.get('Maker Model', 'N/A')}</code>\n"
                    f"⛽ <b>ғᴜᴇʟ:</b> <code>{vehicle.get('Fuel Type', 'N/A')}</code>\n"
                    f"⏳ <b>ᴀɢᴇ:</b> <code>{dates.get('Vehicle Age', 'N/A')}</code>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"🛡️ <b>ɪɴsᴜʀᴀɴᴄᴇ:</b> <code>{insurance.get('Insurance Company', 'N/A')}</code>\n"
                    f"📅 <b>ᴇxᴘɪʀʏ:</b> <code>{dates.get('Insurance Upto', 'N/A')}</code>\n"
                    f"🏥 <b>ғɪᴛɴᴇss:</b> <code>{dates.get('Fitness Upto', 'N/A')}</code>\n"
                    f"📍 <b>ᴀᴅᴅʀᴇss:</b> <code>{card.get('Address', 'N/A')}</code>\n"
                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"✨ <b>ᴘᴏᴡᴇʀᴇᴅ ʙʏ: <a href='{channel_link}'>ᴅᴇᴛᴏʀ ʟᴀʙ</a></b>"
                )
                bot.edit_message_text(output, message.chat.id, wait.message_id, parse_mode="HTML", disable_web_page_preview=True)
            
            else:
                bot.edit_message_text(f"❌ <b>ɴᴏ ᴅᴀᴛᴀ ғᴏᴜɴᴅ!</b>\nVehicle <code>{vehicle_num}</code> not found.", message.chat.id, wait.message_id, parse_mode="HTML")

        except Exception as e:
            print(f"Vehicle API Error: {e}")
            bot.edit_message_text("⚠️ <b>ᴀᴘɪ sʏsᴛᴇᴍ ᴇʀʀᴏʀ.</b> Try again later.", message.chat.id, wait.message_id, parse_mode="HTML")

    # --- BUTTON HANDLER ---
    @bot.message_handler(func=lambda m: m.text == "🚘 ᴠᴇʜɪᴄʟᴇ ɪɴғᴏ")
    def start_vehicle_lookup(message):
        uid = message.from_user.id
        user_states[uid] = "waiting_vehicle_num"
        bot.send_message(message.chat.id, "<b>📥 ᴠᴇʜɪᴄʟᴇ ʟᴏᴏᴋᴜᴘ</b>\nᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜᴇ ᴠᴇʜɪᴄʟᴇ ɴᴜᴍʙᴇʀ.\n\nExample: <code>MH12AB1234</code>", parse_mode="HTML")

    return process_vehicle_lookup
    
