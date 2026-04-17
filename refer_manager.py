import telebot
from telebot import types

def handle_referral(bot, db_mongo, USERS_COL, uid, referrer_id):
    suid = str(uid)
    sref = str(referrer_id)

    # 1. Self-refer check
    if sref == suid:
        return 

    # 2. Database mein check karein ki user purana hai ya naya
    # Hum 'referred_by' field check karenge ya check karenge ki user pehle se DB mein hai
    target_user = db_mongo[USERS_COL].find_one({'_id': suid})
    
    # Agar user pehle se registered hai (Old User)
    if target_user:
        try:
            bot.send_message(sref, "❌ <b>Old User Detected!</b>\nYour friend is already a member, so no referral points added.", parse_mode="HTML")
        except: pass
        return

    # 3. Referrer (jisne link bheja) ka data nikalein
    ref_user = db_mongo[USERS_COL].find_one({'_id': sref})
    
    if ref_user:
        # Naye user ko DB mein register karein (taaki wo dubara refer na ho sake)
        # Note: Ye registration aapke get_user logic se pehle handle ho raha hai
        db_mongo[USERS_COL].insert_one({
            '_id': suid,
            'referred_by': sref,
            'credits': 2, # Starting credits
            'refer_count': 0
        })

        # Referrer ka count badhayein
        db_mongo[USERS_COL].update_one({'_id': sref}, {'$inc': {'refer_count': 1}})
        
        # Fresh count check karein
        updated_ref = db_mongo[USERS_COL].find_one({'_id': sref})
        current_count = updated_ref.get('refer_count', 0)

        if current_count >= 2:
            # Reward logic: 2 refer complete
            db_mongo[USERS_COL].update_one(
                {'_id': sref}, 
                {'$inc': {'credits': 2}, '$set': {'refer_count': 0}}
            )
            bot.send_message(sref, "🎁 <b>Congratulations!</b>\nYou completed 2 refers and earned <b>2 Credits</b>!", parse_mode="HTML")
        else:
            # Progress update message
            bot.send_message(sref, f"👤 <b>New Referral!</b>\nSomeone joined using your link.\nProgress: <code>{current_count}/2</code>", parse_mode="HTML")


def setup_refer_handlers(bot, get_user):
    
    @bot.callback_query_handler(func=lambda call: call.data == "refer_info")
    def show_refer_details(call):
        uid = str(call.from_user.id)
        u = get_user(uid)
        bot_username = (bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={uid}"
        
        ref_msg = (
            "<b>👥 Refer & Earn Program</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Invite your friends and earn extra credits for FREE!\n\n"
            f"🎁 <b>Reward:</b> 2 Credits per 2 successful refers.\n"
            f"📊 <b>Your Current Refers:</b> <code>{u.get('refer_count', 0)}/2</code>\n\n"
            f"🔗 <b>Your Invite Link:</b>\n<code>{ref_link}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Note: Credits will be added automatically once you hit 2 refers.</i>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data="back_to_no_credits"))
        bot.edit_message_text(ref_msg, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_no_credits")
    def go_back(call):
        channel_link = "https://t.me/+SMMZP8shgK01NWZl" 
        
        # --- Buttons Layout ---
        markup = types.InlineKeyboardMarkup()
        btn_buy = types.InlineKeyboardButton("💳 ʙᴜʏ ᴄʀᴇᴅɪᴛs", callback_data="buy_credits")
        btn_refer = types.InlineKeyboardButton("👥 ʀᴇғᴇʀ & ᴇᴀʀɴ", callback_data="refer_info")
        btn_join = types.InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=channel_link) # Direct link button
        
        # Layout set kar rahe hain: Buy aur Refer ek line mein, Join niche akela (Professional look)
        markup.row(btn_buy, btn_refer)
        markup.add(btn_join)
        
        msg = (
            "<b>⚠️ Access Denied!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Your account has <b>0 Credits</b> remaining.\n\n"
            "<b>Refill Options:</b>\n"
            "1. 💰 Claim daily rewards via <b>Bonus</b>.\n"
            "2. 👥 <b>Refer 2 friends</b> to get 2 credits FREE!\n"
            "3. 💳 Purchase credits from owner or click buy button.\n"
            "4. 🎟️ <b>Join channel for Redeem Codes!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 <b>Official:</b> <a href='{channel_link}'>Carlo Dark World</a>"
        )
        
        bot.edit_message_text(
            msg, 
            call.message.chat.id, 
            call.message.message_id, 
            parse_mode="HTML", 
            reply_markup=markup, 
            disable_web_page_preview=True
        )

    
