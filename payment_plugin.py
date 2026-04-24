import telebot
from telebot import types
import os
from datetime import datetime
from pymongo import MongoClient

print("🚀 Payment Plugin: Loading (MongoDB Version)...")

# --- MONGODB SETUP ---
# Environment variable se URI uthayega, nahi toh local use karega
MONGO_URI = os.getenv("MONGO_URI", "your_mongodb_uri_here")
client = MongoClient(MONGO_URI)
db_mongo = client['detor_osint_bot']

USERS_COL = db_mongo['users']
PLANS_COL = db_mongo['plans']
SETTING_COL = db_mongo['settings']

UPI_ID = "kalariyakush5801@oksbi"
QR_PATH = "my_qr.jpg"

def setup_payment_handlers(bot, ADMIN_IDS):
    
    # --- ADMIN: ADD PLAN ---
    @bot.message_handler(commands=['addplan'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def add_plan(message):
        try:
            # Format: /addplan Name|Credits|Price
            _, data = message.text.split(" ", 1)
            name, credits, price = data.split("|")
            
            PLANS_COL.update_one(
                {"name": name},
                {"$set": {"credits": int(credits), "price": price}},
                upsert=True
            )
            bot.reply_to(message, f"✅ ᴘʟᴀɴ <b>'{name}'</b> ᴀᴅᴅᴇᴅ/ᴜᴘᴅᴀᴛᴇᴅ in MongoDB!", parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, "❌ ᴜsᴇ ғᴏʀᴍᴀᴛ: <code>/addplan Starter|10|50</code>", parse_mode="HTML")
        # --- ADMIN: REMOVE PLAN ---
    @bot.message_handler(commands=['removeplan'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def remove_plan(message):
        try:
            # Format: /removeplan Starter
            _, plan_name = message.text.split(" ", 1)
            plan_name = plan_name.strip()
            
            # MongoDB se delete karne ka logic
            result = PLANS_COL.delete_one({"name": plan_name})
            
            if result.deleted_count > 0:
                bot.reply_to(message, f"🗑️ ᴘʟᴀɴ <b>'{plan_name}'</b> ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ!", parse_mode="HTML")
            else:
                bot.reply_to(message, f"❓ ᴘʟᴀɴ <b>'{plan_name}'</b> ɴᴏᴛ ғᴏᴜɴᴅ!", parse_mode="HTML")
                
        except Exception as e:
            bot.reply_to(message, "❌ ᴜsᴇ ғᴏʀᴍᴀᴛ: <code>/removeplan Starter</code>", parse_mode="HTML")
            
    # --- ADMIN: VIEW ALL PLANS ---
    @bot.message_handler(commands=['plans'], func=lambda m: m.from_user.id in ADMIN_IDS)
    def view_plans(message):
        plans = list(PLANS_COL.find())
        if not plans:
            return bot.reply_to(message, "❌ No plans found in database.")
        
        res = "<b>📋 CURRENT ACTIVE PLANS:</b>\n──────────────────\n"
        for plan in plans:
            res += f"🔹 <b>{plan['name']}</b>: {plan['credits']} Cr | ₹{plan['price']}\n"
        
        bot.send_message(message.chat.id, res, parse_mode="HTML")
        
    # --- USER: VIEW PLANS ---
    @bot.callback_query_handler(func=lambda call: call.data == "buy_credits")
    def show_plans(call):
        plans = list(PLANS_COL.find())
        if not plans:
            return bot.answer_callback_query(call.id, "ɴᴏ ᴘʟᴀɴs ᴀᴠᴀɪʟᴀʙʟᴇ ʏᴇᴛ.", show_alert=True)
        
        markup = types.InlineKeyboardMarkup()
        for plan in plans:
            markup.add(types.InlineKeyboardButton(
                f"🎫 {plan['name']} ({plan['credits']} ᴄʀ) - ₹{plan['price']}", 
                callback_data=f"pay_{plan['name']}"
            ))
        
        bot.edit_message_text(
            "<b>💳 sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴘᴜʀᴄʜᴀsᴇ ᴘʟᴀɴ</b>\n──────────────────", 
            call.message.chat.id, call.message.message_id, 
            reply_markup=markup, parse_mode="HTML"
        )

    # --- USER: PAYMENT INSTRUCTIONS ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
    def send_payment_info(call):
        plan_name = call.data.split("_")[1]
        plan = PLANS_COL.find_one({"name": plan_name})
        
        if not plan:
            return bot.answer_callback_query(call.id, "Plan not found.")

        instr = (
            f"<b>✨ ᴘʟᴀɴ sᴇʟᴇᴄᴛᴇᴅ: {plan_name}</b>\n"
            f"💰 ᴀᴍᴏᴜɴᴛ ᴛᴏ ᴘᴀʏ: <b>₹{plan['price']}</b>\n"
            f"──────────────────\n"
            f"🔗 ᴜᴘɪ ɪᴅ: <code>{UPI_ID}</code>\n\n"
            f"📝 ɪɴsᴛʀᴜᴄᴛɪᴏɴs:\n"
            f"1. ᴘᴀʏ ᴛʜᴇ ᴀᴍᴏᴜɴᴛ ᴠɪᴀ ᴀɴʏ ᴜᴘɪ ᴀᴘᴘ.\n"
            f"2. ᴛᴀᴋᴇ ᴀ sᴄʀᴇᴇɴsʜᴏᴛ ᴏғ ᴛʜᴇ sᴜᴄᴄᴇssғᴜʟ ᴘᴀʏᴍᴇɴᴛ.\n"
            f"3. sᴇɴᴅ ᴛʜᴇ sᴄʀᴇᴇɴsʜᴏᴛ ʜᴇʀᴇ ɴᴏᴡ.\n"
            f"──────────────────\n"
            f"⚠️ sʏsᴛᴇᴍ ɪs ᴀᴡᴀɪᴛɪɴɢ ʏᴏᴜʀ ᴘʀᴏᴏғ..."
        )
        
        # State update for screenshot handler
        from __main__ import user_states
        user_states[call.from_user.id] = f"sending_ss|{plan['credits']}"
        
        if os.path.exists(QR_PATH):
            with open(QR_PATH, 'rb') as qr:
                bot.send_photo(call.message.chat.id, qr, caption=instr, parse_mode="HTML")
        else:
            bot.send_message(call.message.chat.id, instr, parse_mode="HTML")

        # --- USER: SCREENSHOT RECEIVER (NOTIFIES ALL ADMINS) ---
    @bot.message_handler(content_types=['photo'])
    def handle_screenshot(message):
        from __main__ import user_states
        uid = message.from_user.id
        
        # Check if user is in "awaiting screenshot" state
        if uid in user_states and user_states[uid].startswith("sending_ss|"):
            try:
                credits = user_states[uid].split("|")[1]
                u_name = message.from_user.first_name
                
                # Admin ke liye approval buttons
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("✅ APPROVE", callback_data=f"p_app_{uid}_{credits}"),
                    types.InlineKeyboardButton("❌ REJECT", callback_data=f"p_rej_{uid}_{credits}")
                )
                
                caption = (
                    f"💰 <b>ɴᴇᴡ ᴘᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 ᴜsᴇʀ: {u_name} (<code>{uid}</code>)\n"
                    f"🎫 ᴘʟᴀɴ: {credits} ᴄʀᴇᴅɪᴛs\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )

                # 🚀 Loop through all admins to send notification
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_photo(
                            admin_id, 
                            message.photo[-1].file_id, 
                            caption=caption, 
                            reply_markup=markup, 
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Failed to notify admin {admin_id}: {e}")

                bot.reply_to(message, "✅ <b>Proof received!</b> Admin will verify and approve soon.", parse_mode="HTML")
                
                # State clear karein taaki har photo admin ko na jaye
                del user_states[uid]

            except Exception as e:
                bot.reply_to(message, f"❌ Error: {e}")
                
            # --- ADMIN: APPROVAL LOGIC (MULTI-ADMIN SECURED) ---
    @bot.callback_query_handler(func=lambda call: call.data.startswith("p_"))
    def admin_approval(call):
        if call.from_user.id not in ADMIN_IDS:
            return bot.answer_callback_query(call.id, "❌ Not authorized!", show_alert=True)

        try:
            # 1. 🛡️ DOUBLE CHECK: Caption check karo ki kya pehle hi process ho chuka hai?
            current_caption = call.message.caption or ""
            if "✅" in current_caption or "❌" in current_caption:
                # Buttons remove kar do agar abhi bhi dikh rahe hain
                try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
                except: pass
                return bot.answer_callback_query(call.id, "⚠️ Already processed by another admin!", show_alert=True)

            data_parts = call.data.split("_")
            action = data_parts[1]
            uid = str(data_parts[2]) 
            credits = int(data_parts[3])
            
            col = db_mongo[USERS_COL] if isinstance(USERS_COL, str) else USERS_COL

            if action == "app": # Approve
                # ✅ Database Update
                col.update_one({"_id": uid}, {"$inc": {"credits": credits}}, upsert=True)
                
                # User ko notification
                try: bot.send_message(uid, f"✅ <b>ᴘᴀʏᴍᴇɴᴛ ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\n{credits} ᴄʀᴇᴅɪᴛs ᴀᴅᴅᴇᴅ.", parse_mode="HTML")
                except: pass

                # 🛑 CRITICAL: Buttons hatao aur status update karo
                bot.edit_message_caption(
                    caption=f"✅ Approved {credits} Cr for {uid}\nAdmin: {call.from_user.first_name}",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=None  # <--- ISSE BUTTONS GAYAB HONGE
                )
                bot.answer_callback_query(call.id, "✅ Done!")

            elif action == "rej": # Reject
                try: bot.send_message(uid, "❌ <b>ᴘᴀʏᴍᴇɴᴛ ʀᴇᴊᴇᴄᴛᴇᴅ!</b>", parse_mode="HTML")
                except: pass

                # 🛑 Buttons hatao aur status update karo
                bot.edit_message_caption(
                    caption=f"❌ Rejected for {uid}\nAdmin: {call.from_user.first_name}",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=None  # <--- ISSE BUTTONS GAYAB HONGE
                )
                bot.answer_callback_query(call.id, "❌ Rejected")

        except Exception as e:
            print(f"Approval Error: {e}")
            bot.answer_callback_query(call.id, f"❌ Error: {e}", show_alert=True)
