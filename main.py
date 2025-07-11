import telebot
import json
import random
import os
from telebot.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("TOKEN") or "7573788951:AAFuIehvHgf3C0XWxaAVyklHbN4aIKxvSPk"
bot = telebot.TeleBot(TOKEN)

# ملف تخزين القروبات
try:
    with open("groups.json", "r") as f:
        groups = json.load(f)
except:
    groups = []

# كلمات ممنوعة
banned_words = ["t.me", "http", "كلب", "حيوان", "حقير", "تافه"]

# ردود تلقائية
replies = {
    "سلام عليكم": "وعليكم السلام ورحمة الله وبركاته 🌸",
    "هاي": "❌ لا يجوز قول 'هاي'، قل: السلام عليكم لأنك مسلم(ة) وتفتخر بذلك 💚",
    "باي": "❌ لا يجوز قول 'باي'، الأفضل قول: في أمان الله 🌟",
    "كرهت": "متكرهش، كاين بوت غون ينحي القلق 🌿"
}

# أسئلة كت (عربية)
questions = [
    "ما أكثر شيء تندم عليه؟", "هل سبق وخنت ثقة شخص؟", "ما الشيء الذي لا تستطيع نسيانه؟",
    "هل تعتبر نفسك محبوبًا؟", "ما أكبر مخاوفك؟", "هل تحب الوحدة؟", "هل يمكنك مسامحة من ظلمك؟",
    "ما هو أكثر شيء يجعلك تبكي؟", "هل سبق وأحببت من طرف واحد؟", "ما أكثر شيء تفخر به؟",
    "هل أنت شخص انطوائي؟", "هل تؤمن بالحب الحقيقي؟", "هل تثق بالناس بسهولة؟",
    "ما أجمل ذكرى في حياتك؟", "لو عاد بك الزمن، ما الذي ستغيره؟", "ما هو هدفك الأكبر في الحياة؟",
    "هل أنت راضٍ عن نفسك؟", "ما هي أسوأ صفة فيك؟", "هل تحب المغامرات؟",
    "هل سبق وندمت لأنك كنت طيبًا؟", "ما أكثر شيء تخاف فقدانه؟", "ما حلمك المستحيل؟"
]

# أمثال عربية
sayings = [
    "الصبر مفتاح الفرج", "من جد وجد ومن زرع حصد", "درهم وقاية خير من قنطار علاج",
    "العقل زينة", "الوقت كالسيف إن لم تقطعه قطعك", "اعمل خير وارمه في البحر",
    "من راقب الناس مات همًا", "احذر عدوك مرة وصديقك ألف مرة", "عصفور باليد خير من عشرة على الشجرة",
    "إذا كان الكلام من فضة فالسكوت من ذهب", "لا تؤجل عمل اليوم إلى الغد",
    "من شب على شيء شاب عليه", "كما تدين تدان", "رب أخ لك لم تلده أمك",
    "الجار قبل الدار", "القناعة كنز لا يفنى", "اتق شر من أحسنت إليه",
    "الكتاب يُقرأ من عنوانه", "العين لا تعلو على الحاجب", "الحق يعلو ولا يُعلى عليه"
]

# ترحيب بالأعضاء الجدد
@bot.message_handler(content_types=["new_chat_members"])
def welcome(msg):
    for user in msg.new_chat_members:
        bot.send_message(msg.chat.id, f"👋 مرحباً {user.first_name}، نورت المجموعة!")

# أمر /start في الخاص
@bot.message_handler(commands=["start"])
def start_msg(msg):
    if msg.chat.type == "private":
        bot_name = bot.get_me().username
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("➕ أضفني لمجموعتك", url=f"https://t.me/{bot_name}?startgroup=true"),
            InlineKeyboardButton("📤 انشر البوت", url=f"https://t.me/share/url?url=https://t.me/{bot_name}?startgroup=true")
        )
        markup.add(InlineKeyboardButton("👨‍💻 المطور: zedk26", url="https://t.me/zedk26"))
        bot.send_message(msg.chat.id, "👋 مرحبًا! أنا \"غون\" بوت حماية وتسلية متكامل!\n\n"
                                      "• أحمـي مجموعتك 💂‍♂️\n"
                                      "• أضيف التفاعل والمتعة 🎮\n"
                                      "• أنظمة: البنك، المزرعة، الغزاة، وأكثر! ⚔️💰🌾\n\n"
                                      "🔹 أضفني لقروبك\n"
                                      "🔹 ارفعني مشرف\n"
                                      "🔹 أرسل (تفعيل) لبدء المتعة!", reply_markup=markup)

# تفعيل البوت
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "تفعيل")
def activate(msg):
    try:
        admins = [admin.user.id for admin in bot.get_chat_administrators(msg.chat.id)]
        if msg.from_user.id in admins:
            if msg.chat.id not in groups:
                groups.append(msg.chat.id)
                with open("groups.json", "w") as f:
                    json.dump(groups, f)
                bot.reply_to(msg, "✅ تم تفعيل البوت في هذه المجموعة!")
            else:
                bot.reply_to(msg, "⚠️ البوت مفعل من قبل.")
        else:
            bot.reply_to(msg, "❌ يجب أن تكون مشرفًا لتفعيل البوت.")
    except:
        bot.reply_to(msg, "❌ تأكد أن البوت لديه صلاحية المشرف.")

# أوامر إدارية تلقائية بالرد على كلمة مثل "شتم"
@bot.message_handler(func=lambda m: m.reply_to_message and m.text.lower() in ["حظر", "كتم", "الغاء حظر", "الغاء كتم"])
def admin_action_by_reply(msg):
    try:
        admins = [admin.user.id for admin in bot.get_chat_administrators(msg.chat.id)]
        if msg.from_user.id in admins:
            target_id = msg.reply_to_message.from_user.id
            action = msg.text.lower()

            if action == "كتم":
                bot.restrict_chat_member(msg.chat.id, target_id, ChatPermissions(can_send_messages=False))
                bot.reply_to(msg, "🔇 تم كتم العضو.")

            elif action == "حظر":
                bot.kick_chat_member(msg.chat.id, target_id)
                bot.reply_to(msg, "🚫 تم حظر العضو.")

            elif action == "الغاء كتم":
                bot.restrict_chat_member(msg.chat.id, target_id, ChatPermissions(can_send_messages=True))
                bot.reply_to(msg, "🔊 تم فك الكتم.")

            elif action == "الغاء حظر":
                bot.unban_chat_member(msg.chat.id, target_id)
                bot.reply_to(msg, "✅ تم فك الحظر.")
    except:
        bot.reply_to(msg, "❌ تأكد من صلاحيات البوت.")

# تفاعل القروب
@bot.message_handler(func=lambda m: m.chat.id in groups)
def group_handler(msg):
    txt = msg.text.lower()

    # فلترة الرسائل الطويلة
    if len(txt) > 300:
        try:
            bot.delete_message(msg.chat.id, msg.message_id)
        except: pass
        return

    # حذف الكلمات الممنوعة
    if any(w in txt for w in banned_words):
        try:
            bot.delete_message(msg.chat.id, msg.message_id)
        except: pass
        return

    # ردود تلقائية
    for key in replies:
        if key in txt:
            bot.reply_to(msg, replies[key])
            return

    # أوامر ترفيهية
    if txt == "كت":
        bot.reply_to(msg, random.choice(questions))
    elif txt == "مثل":
        bot.reply_to(msg, random.choice(sayings))
    elif txt == "مساعدة":
        bot.reply_to(msg, "أوامر البوت:\nكت، مثل، كتم، حظر، تفعيل، إلغاء كتم، إلغاء حظر، مساعدة")

print("✅ البوت يعمل الآن...")
bot.polling(none_stop=True)
