import telebot
from datetime import datetime
import pytz

# Timezone Setup
IST = pytz.timezone('Asia/Kolkata')

print("✅ admin_cmd.py: Loading Handlers...")

def register_admin_handlers(bot, ADMIN_ID, db_mongo, USERS_COL, COUPONS_COL, SETTING_COL):
    
    # --- COMMAND: DECREASE CREDITS ---
    # Isko function ke andar rakha hai taaki main file se connect ho jaye
    @bot.message_handler(commands=['decrease'], func=lambda m: m.from_user.id == ADMIN_ID)
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
    @bot.message_handler(commands=['Remove', 'remove'], func=lambda m: m.from_user.id == ADMIN_ID)
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
    @bot.message_handler(commands=['delcoupon', 'rmcoupon'], func=lambda m: m.from_user.id == ADMIN_ID)
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
    @bot.message_handler(commands=['setcredit'], func=lambda m: m.from_user.id == ADMIN_ID)
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

        # --- COMMAND: CREDIT ALL USERS ---
    @bot.message_handler(commands=['credit_all'], func=lambda m: m.from_user.id == ADMIN_ID)
    def credit_all_users(message):
        try:
            args = message.text.split()
            if len(args) < 2 or not args[1].isdigit():
                return bot.reply_to(message, "⚠️ ᴜsᴀɢᴇ: <code>/credit_all 50</code>", parse_mode="HTML")
            
            amount = int(args[1])
            # update_many ({}) matlab empty filter, yani saare documents par apply hoga
            result = db_mongo[USERS_COL].update_many({}, {"$inc": {"credits": amount}})
            
            bot.reply_to(message, f"✅ <b>ʙᴜʟᴋ ᴀᴅᴅɪᴛɪᴏɴ sᴜᴄᴄᴇss!</b>\nAdded <code>{amount}</code> credits to <b>{result.modified_count}</b> users.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")

    # --- COMMAND: DEDUCT ALL USERS ---
    @bot.message_handler(commands=['deduct_all'], func=lambda m: m.from_user.id == ADMIN_ID)
    def deduct_all_users(message):
        try:
            args = message.text.split()
            if len(args) < 2 or not args[1].isdigit():
                return bot.reply_to(message, "⚠️ ᴜsᴀɢᴇ: <code>/deduct_all 10</code>", parse_mode="HTML")
            
            # Amount ko negative kar rahe hain taaki minus ho jaye
            amount = -abs(int(args[1])) 
            result = db_mongo[USERS_COL].update_many({}, {"$inc": {"credits": amount}})
            
            bot.reply_to(message, f"✅ <b>ʙᴜʟᴋ ᴅᴇᴅᴜᴄᴛɪᴏɴ sᴜᴄᴄᴇss!</b>\nRemoved <code>{abs(amount)}</code> credits from <b>{result.modified_count}</b> users.", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")
           
    print("🚀 admin_cmd: Handlers Registered!")
                    
