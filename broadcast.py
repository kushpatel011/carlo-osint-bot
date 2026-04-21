import time
from telebot import types

def register_broadcast_handler(bot, ADMIN_IDS, db_mongo, USERS_COL):
    
    @bot.message_handler(commands=['broadcast'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def handle_broadcast(message):
        # Command se text alag karna
        command_parts = message.text.split(maxsplit=1)
        
        if len(command_parts) < 2:
            return bot.reply_to(message, "❌ <b>ᴜsᴀɢᴇ:</b>\n<code>/broadcast Your Message Here</code>", parse_mode="HTML")
        
        broadcast_text = command_parts[1]
        
        # --- Start Sending Logic ---
        users = list(db_mongo[USERS_COL].find())
        valid_ids = [u['_id'] for u in users if str(u.get('_id', '')).isdigit()]
        
        total = len(valid_ids)
        success = 0
        blocked = 0
        
        status = bot.send_message(ADMIN_IDS, f"🚀 <b>ʙʀᴏᴀᴅᴄᴀsᴛ sᴛᴀʀᴛᴇᴅ...</b>\n👤 ᴛᴀʀɢᴇᴛ: {total}", parse_mode="HTML")

        for uid in valid_ids:
            try:
                bot.send_message(uid, broadcast_text)
                success += 1
            except Exception:
                blocked += 1
            
            # Flood wait protection
            if (success + blocked) % 25 == 0:
                time.sleep(1)

        report = (
            "✅ <b>ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏɴᴇ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 ᴛᴏᴛᴀʟ: {total}\n"
            f"🎉 sᴜᴄᴄᴇss: {success}\n"
            f"🚫 ғᴀɪʟᴇᴅ: {blocked}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        bot.edit_message_text(report, ADMIN_IDS, status.message_id, parse_mode="HTML")
        
