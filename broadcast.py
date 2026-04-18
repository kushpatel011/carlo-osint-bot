import time
from telebot import types

# USERS_COL aur db_mongo aapki main file se aayenge
def start_broadcast(bot, admin_id, broadcast_msg, db_mongo, USERS_COL):
    # 1. Database se saare numeric IDs fetch karo
    all_users = list(db_mongo[USERS_COL].find())
    valid_users = [u['_id'] for u in all_users if str(u.get('_id', '')).isdigit()]
    
    total = len(valid_users)
    success = 0
    blocked = 0
    
    status_msg = bot.send_message(admin_id, f"🚀 ʙʀᴏᴀᴅᴄᴀsᴛ sᴛᴀʀᴛᴇᴅ...\n👤 ᴛᴀʀɢᴇᴛ ᴜsᴇʀs: {total}")

    for user_id in valid_users:
        try:
            # Broadcast message bhej rahe hain (Photo, Video ya Text handle karne ke liye copy_message best hai)
            bot.copy_message(user_id, admin_id, broadcast_msg.message_id)
            success += 1
        except Exception as e:
            # Agar user ne bot block kar diya hai
            blocked += 1
        
        # Telegram API limit se bachne ke liye chota pause (Flood wait protection)
        if (success + blocked) % 20 == 0:
            time.sleep(1)

    # Final report
    report = (
        "✅ <b>ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 ᴛᴏᴛᴀʟ ᴜsᴇʀs: {total}\n"
        f"🎉 sᴜᴄᴄᴇssғᴜʟ: {success}\n"
        f"🚫 ʙʟᴏᴄᴋᴇᴅ/ғᴀɪʟᴇᴅ: {blocked}\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    bot.edit_message_text(report, admin_id, status_msg.message_id, parse_mode="HTML")
