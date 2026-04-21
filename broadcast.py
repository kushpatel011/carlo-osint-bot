import time
from telebot import types

def register_broadcast_handler(bot, ADMIN_IDS, db_mongo, USERS_COL):
    
    @bot.message_handler(commands=['broadcast'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def handle_broadcast(message):
        # 1. Command parts split karna
        command_parts = message.text.split(maxsplit=1)
        
        if len(command_parts) < 2:
            return bot.reply_to(message, "❌ <b>ᴜsᴀɢᴇ:</b>\n<code>/broadcast Your Message Here</code>", parse_mode="HTML")
        
        broadcast_text = command_parts[1]
        admin_chat_id = message.chat.id # Current admin ki ID report ke liye
        
        # 2. Database se users nikalna
        # Sirf _id uthao performance ke liye
        users = list(db_mongo[USERS_COL].find({}, {"_id": 1}))
        total = len(users)
        success = 0
        blocked = 0
        
        # Initial status message
        status_msg = bot.send_message(admin_chat_id, f"🚀 <b>ʙʀᴏᴀᴅᴄᴀsᴛ sᴛᴀʀᴛᴇᴅ...</b>\n👤 ᴛᴀʀɢᴇᴛ: {total}", parse_mode="HTML")

        # 3. Broadcasting Loop
        for index, user in enumerate(users):
            uid = user.get("_id")
            if not uid: continue
            
            try:
                bot.send_message(uid, broadcast_text)
                success += 1
            except Exception:
                blocked += 1
            
            # Flood wait protection (Har 25 messages ke baad 1 sec gap)
            if (index + 1) % 25 == 0:
                time.sleep(1)

        # 4. Final Report
        report = (
            "✅ <b>ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏɴᴇ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 ᴛᴏᴛᴀʟ: {total}\n"
            f"🎉 sᴜᴄᴄᴇss: {success}\n"
            f"🚫 ғᴀɪʟᴇᴅ: {blocked}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        # Edit karte waqt sender ki chat_id use karein
        bot.edit_message_text(report, admin_chat_id, status_msg.message_id, parse_mode="HTML")
    
