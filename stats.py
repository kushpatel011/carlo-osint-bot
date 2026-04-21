import io
from datetime import datetime
from telebot import types

def setup_stats_handlers(bot, db_mongo, ADMIN_IDS):
    USERS_COL = db_mongo['users']
    COUPONS_COL = db_mongo['coupons']

    # --- 1. EXPORT ALL USERS ---
    @bot.message_handler(commands=['getusers'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def export_all_users(message):
        bot.reply_to(message, "⏳ ɢᴇɴᴇʀᴀᴛɪɴɢ ᴀʟʟ ᴜsᴇʀs ʟɪsᴛ...")
        users = list(USERS_COL.find())
        
        output = "📊 carlo ᴏsɪɴᴛ - ᴛᴏᴛᴀʟ ᴜsᴇʀs ʟɪsᴛ\n"
        output += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, u in enumerate(users, 1):
            name = u.get('name', 'Unknown')
            uid = u['_id']
            credits = u.get('credits', 0)
            link = f"tg://user?id={uid}"
            
            output += f"{i}. ɴᴀᴍᴇ: {name}\n"
            output += f"   ɪᴅ: {uid}\n"
            output += f"   ᴄʀᴇᴅɪᴛs: {credits}\n"
            output += f"   ᴘʀᴏғɪʟᴇ: {link}\n"
            output += "──────────────────\n"
        
        with io.BytesIO(output.encode()) as file:
            file.name = f"all_users_{datetime.now().strftime('%d_%m')}.txt"
            bot.send_document(message.chat.id, file, caption=f"👤 ᴛᴏᴛᴀʟ ᴜsᴇʀs: {len(users)}")

    # --- 2. EXPORT VIP MEMBERS ---
    @bot.message_handler(commands=['getvips'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def export_vip_users(message):
        bot.reply_to(message, "⏳ ɢᴇɴᴇʀᴀᴛɪɴɢ ᴠɪᴘ ᴍᴇᴍʙᴇʀs ʟɪsᴛ...")
        vips = list(USERS_COL.find({"is_vip": True}))
        
        if not vips:
            return bot.reply_to(message, "❌ ɴᴏ ᴠɪᴘ ᴍᴇᴍʙᴇʀs ғᴏᴜɴᴅ.")

        output = "👑 carlo ᴏsɪɴᴛ - ᴠɪᴘ ᴍᴇᴍʙᴇʀs ʟɪsᴛ\n"
        output += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, u in enumerate(vips, 1):
            name = u.get('name', 'Unknown')
            uid = u['_id']
            link = f"tg://user?id={uid}"
            
            output += f"{i}. ᴠɪᴘ ɴᴀᴍᴇ: {name}\n"
            output += f"   ɪᴅ: {uid}\n"
            output += f"   ᴘʀᴏғɪʟᴇ ʟɪɴᴋ: {link}\n"
            output += "──────────────────\n"
        
        with io.BytesIO(output.encode()) as file:
            file.name = f"vip_members_{datetime.now().strftime('%d_%m')}.txt"
            bot.send_document(message.chat.id, file, caption=f"👑 ᴛᴏᴛᴀʟ ᴠɪᴘs: {len(vips)}")
        # --- 3. EXPORT ADVANCED COUPON AUDIT ---

    @bot.message_handler(commands=['getcoupons'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def export_coupons(message):
        try:
            bot.reply_to(message, "⏳ ɢᴇɴᴇʀᴀᴛɪɴɢ ᴀᴅᴠᴀɴᴄᴇᴅ ᴀᴜᴅɪᴛ ʀᴇᴘᴏʀᴛ...")
            
            # MongoDB se data nikalna (COUPONS_COL ab collection object hai ya string uske hisab se)
            # Agar COUPONS_COL string hai toh: db_mongo[COUPONS_COL].find()
            # Agar direct collection hai toh: COUPONS_COL.find()
            coupons = list(COUPONS_COL.find()) 
            
            if not coupons:
                return bot.reply_to(message, "❌ ɴᴏ ᴅᴀᴛᴀ ғᴏᴜɴᴅ ɪɴ ᴄᴏᴜᴘᴏɴ ᴠᴀᴜʟᴛ.")

            active_list = ""
            inactive_list = ""
            user_logs = ""
            a_count, i_count = 0, 0

            for cp in coupons:
                code = cp.get('_id', 'N/A')
                amt = cp.get('amount', 0)
                rem = cp.get('uses', 0)
                claimed_users = cp.get('users', [])
                
                if rem > 0:
                    a_count += 1
                    active_list += f"🎫 ᴄᴏᴅᴇ: {code}\n💰 ᴄʀᴇᴅɪᴛs: {amt}\n📉 ʀᴇᴍᴀɪɴɪɴɢ: {rem} ᴜsᴇs\n──────────────────\n"
                else:
                    i_count += 1
                    inactive_list += f"❌ ᴄᴏᴅᴇ: {code}\n💰 ᴄʀᴇᴅɪᴛs: {amt}\n🚫 sᴛᴀᴛᴜs: ᴇxᴘɪʀᴇᴅ/ꜰᴜʟʟ\n──────────────────\n"
                    
                for user_id in claimed_users:
                    user_logs += f"👤 ᴜsᴇʀ ID: {user_id}\n🎟️ ᴜsᴇᴅ: {code} | ɢᴏᴛ: {amt} ᴄʀ\n──────────────────\n"

            output = "📊 DETOR OSINT - COUPON AUDIT REPORT\n"
            output += f"📅 ᴅᴀᴛᴇ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            output += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            output += f"✅ [ ACTIVE COUPONS ] - ({a_count})\n"
            output += "━━━━━━━━━━━━━━━━━━━━\n"
            output += active_list if active_list else "No active coupons.\n"
            output += "\n"
            
            output += f"⚠️ [ INACTIVE/EXPIRED ] - ({i_count})\n"
            output += "━━━━━━━━━━━━━━━━━━━━\n"
            output += inactive_list if inactive_list else "No inactive coupons.\n"
            output += "\n"
            
            output += "👥 [ USER REDEMPTION LOGS ]\n"
            output += "━━━━━━━━━━━━━━━━━━━━\n"
            output += user_logs if user_logs else "No claims recorded yet.\n"
            output += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nEND OF REPORT"

            with io.BytesIO(output.encode()) as file:
                file.name = f"Coupon_Audit_{datetime.now().strftime('%d_%m')}.txt"
                bot.send_document(
                    message.chat.id, 
                    file, 
                    caption=f"📋 **Coupon Audit Summary**\n\n✅ Active: {a_count}\n⚠️ Inactive: {i_count}\n👤 Total Claims: {user_logs.count('👤')}",
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"Error in export_coupons: {e}")
            bot.send_message(message.chat.id, f"❌ Error generating report: {e}")
            
