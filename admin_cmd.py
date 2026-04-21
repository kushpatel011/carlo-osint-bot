import telebot
from datetime import datetime
import pytz

# Timezone Setup
IST = pytz.timezone('Asia/Kolkata')

print("✅ admin_cmd.py: Loading Handlers...")

def register_admin_handlers(bot, ADMIN_IDS, db_mongo, USERS_COL, COUPONS_COL, SETTING_COL):
    
    # --- COMMAND: DECREASE CREDITS ---
    # Isko function ke andar rakha hai taaki main file se connect ho jaye
    @bot.message_handler(commands=['decrease'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def decrease_credits(message):
        try:
            # Format: /decrease userid amount
            args = message.text.split()
            if len(args) < 3:
                return bot.reply_to(message, "❌ ᴜsᴇ ᴘʀᴏᴘᴇʀ ғᴏʀᴍᴀᴛ: <code>/decrease userid amount</code>", parse_mode="HTML")
            
            target_uid = str(args[1])
            amount = int(args[2])
            
            # MongoDB Update
            result = db_mongo[USERS_COL].update_one(
                {"_id": target_uid},
                {"$inc": {"credits": -amount}}
            )
            
            if result.modified_count > 0:
                bot.reply_to(message, f"✅ sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇᴅᴜᴄᴛᴇᴅ {amount} ᴄʀᴇᴅɪᴛs ғʀᴏᴍ <code>{target_uid}</code>.", parse_mode="HTML")
                try:
                    bot.send_message(target_uid, f"⚠️ <b>ᴀʟᴇʀᴛ:</b> {amount} ᴄʀᴇᴅɪᴛs ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ʙʏ ᴀᴅᴍɪɴ.", parse_mode="HTML")
                except: pass
            else:
                bot.reply_to(message, "❌ User not found in database.")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")

    # --- COMMAND: REMOVE VIP ---
    @bot.message_handler(commands=['Remove', 'remove'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def remove_vip(message):
        try:
            # Format: /Remove userid reason
            args = message.text.split(" ", 2)
            if len(args) < 3:
                return bot.reply_to(message, "❌ ᴜsᴇ ᴘʀᴏᴘᴇʀ ғᴏʀᴍᴀᴛ: <code>/remove userid reason</code>", parse_mode="HTML")
            
            target_uid = str(args[1])
            reason = args[2]
            
            result = db_mongo[USERS_COL].update_one(
                {"_id": target_uid},
                {"$set": {"is_vip": False}}
            )
            
            if result.modified_count > 0:
                bot.reply_to(message, f"🚫 <b>ᴠɪᴘ ʀᴇᴍᴏᴠᴇᴅ!</b>\nᴜsᴇʀ: <code>{target_uid}</code>\nʀᴇᴀsᴏɴ: {reason}", parse_mode="HTML")
                try:
                    bot.send_message(target_uid, f"🔴 <b>ᴠɪᴘ ʀᴇᴠᴏᴋᴇᴅ:</b> {reason}", parse_mode="HTML")
                except: pass
            else:
                bot.reply_to(message, "❌ User not VIP or not found.")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {str(e)}")
            
    # --- NEW COMMAND: REMOVE COUPON ---
    @bot.message_handler(commands=['delcoupon', 'rmcoupon'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def remove_coupon(message):
        try:
            # Format: /delcoupon CODE
            args = message.text.split()
            if len(args) < 2:
                return bot.reply_to(message, "⚠️ <b>ᴜsᴇ ᴘʀᴏᴘᴇʀ ғᴏʀᴍᴀᴛ:</b> <code>/delcoupon CODE</code>", parse_mode="HTML")
            
            coupon_code = args[1].upper().strip()
            
            # MongoDB Delete Operation
            result = db_mongo[COUPONS_COL].delete_one({"_id": coupon_code})
            
            if result.deleted_count > 0:
                bot.reply_to(message, f"🗑️ <b>ᴄᴏᴜᴘᴏɴ ᴅᴇʟᴇᴛᴇᴅ!</b>\nCode <code>{coupon_code}</code> has been removed from database.", parse_mode="HTML")
            else:
                bot.reply_to(message, f"❌ <b>ɴᴏᴛ ғᴏᴜɴᴅ!</b>\nCoupon <code>{coupon_code}</code> does not exist.", parse_mode="HTML")
                
        except Exception as e:
            bot.reply_to(message, f"❌ <b>Error:</b> {str(e)}", parse_mode="HTML")
      # --- COMMAND: SET CREDIT FOR NEW USERS ---      
    @bot.message_handler(commands=['setcredit'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def set_default_credit(message):
       try:
        val = message.text.split()
        if len(val) < 2 or not val[1].isdigit():
            return bot.reply_to(message, "⚠️ ᴜsᴀɢᴇ: <code>/setcredit 10</code>", parse_mode="HTML")
        
        new_amt = int(val[1])
        db_mongo[SETTING_COL].update_one(
            {"_id": "global"}, 
            {"$set": {"default_reg_credit": new_amt}}, 
            upsert=True
        )
        bot.reply_to(message, f"✅ <b>sᴜᴄᴄᴇss!<b>\nNew users will now get <code>{new_amt}</code> credits on registration.", parse_mode="HTML")
        
       except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

    # --- COMMAND: DEDUCT ALL USERS ---
    @bot.message_handler(commands=['deduct_all'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def deduct_all_users(message):
        try:
            args = message.text.split()
            if len(args) < 2 or not args[1].isdigit():
                return bot.reply_to(message, "⚠️ ᴜsᴀɢᴇ: <code>/deduct_all 10</code>", parse_mode="HTML")
            
            deduct_val = abs(int(args[1])) # Positive value for deduction logic
            
            # 1. Update in DB (Pehle sabka minus karo)
            result = db_mongo[USERS_COL].update_many({}, {"$inc": {"credits": -deduct_val}})
            
            # SMART LOGIC: Jiske bhi credits 0 se niche (negative) gaye, unhe 0 kar do
            db_mongo[USERS_COL].update_many({"credits": {"$lt": 0}}, {"$set": {"credits": 0}})
            
            # 2. Status message
            status_msg = bot.reply_to(message, f"⏳ <b>ᴜᴘᴅᴀᴛᴇᴅ {result.modified_count} ᴜsᴇʀs.</b>\nBroadcasting deduction notification...", parse_mode="HTML")
            
            # 3. Fetch users
            all_users = db_mongo[USERS_COL].find({}, {"_id": 1})
            
            sent_count = 0
            failed_count = 0
            
            for index, user in enumerate(all_users):
                uid = user.get("_id")
                
                try:
                    # User ko message
                    notify_text = (
                        "⚠️ <b>ᴄʀᴇᴅɪᴛs ᴅᴇᴅᴜᴄᴛᴇᴅ!</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"<b>Up to {deduct_val} ᴄʀᴇᴅɪᴛs</b> ʜᴀᴠᴇ ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ʙʏ ᴀᴅᴍɪɴ."
                    )
                    bot.send_message(uid, notify_text, parse_mode="HTML")
                    sent_count += 1
                except Exception:
                    failed_count += 1
                
                # --- 🛡️ FLOOD WAIT LOGIC ---
                if (index + 1) % 25 == 0:
                    import time # Ensure time is imported
                    time.sleep(2)
                    
            # 4. Final Report
            final_report = (
                "✅ <b>ᴅᴇᴅᴜᴄᴛɪᴏɴ ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"💸 <b>Mᴀx Aᴍᴏᴜɴᴛ Dᴇᴅᴜᴄᴛᴇᴅ:</b> <code>{deduct_val}</code>\n"
                f"📨 <b>Mᴇssᴀɢᴇs Sᴇɴᴛ:</b> <code>{sent_count}</code>\n"
                f"🚫 <b>Fᴀɪʟᴇᴅ/Bʟᴏᴄᴋᴇᴅ:</b> <code>{failed_count}</code>"
            )
            bot.edit_message_text(final_report, message.chat.id, status_msg.message_id, parse_mode="HTML")

        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")
