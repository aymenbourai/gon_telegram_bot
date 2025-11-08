import os
import logging
import requests
import json
import threading
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
from dateutil import parser 

# --- تهيئة التسجيل (Logging) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- إعدادات البوت والـ API (يتم جلبها من البيئة أو استخدام قيم افتراضية) ---
# رمز التوثيق للـ Webhook (كما طلب المستخدم)
VERIFY_TOKEN = 'boykta 2023'

# يجب تعيين هذا كمتغير بيئة سري على Vercel
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN', 'رمز_وصول_صفحة_فيسبوك_الخاص_بك')

# يجب تعيين هذا كمتغير بيئة سري على Vercel
DEVICE_ID = os.environ.get('DEVICE_ID', 'B4A13AE09F22A2A4') 

# عناوين الـ API
AUTH_API_URL = "https://api.vulcanlabs.co/smith-auth/api/v1/token"
CHAT_API_URL = "https://api.vulcanlabs.co/smith-v2/api/v7/chat_android"

# إعدادات المحادثة
MAX_CHAT_HISTORY = 100 
MAX_TOKENS = 0 # 0 تعني استخدام الإعداد الافتراضي للنموذج

# --- المتغيرات العامة لحفظ الحالة ---
user_chats = {}  # لتخزين سجل الدردشة لكل مستخدم
access_token_data = {"token": "", "expiry": datetime.now(timezone.utc)} # لتخزين توكن الوصول ووقته

# تهيئة تطبيق Flask
app = Flask(__name__)

# --- 1. وظيفة جلب التوكن (Vulcan Labs Auth) ---
def get_access_token(force_refresh=False):
    """جلب أو تجديد توكن الوصول من Vulcan Labs API."""
    global access_token_data
    
    # التحقق من صلاحية التوكن الحالي
    if not force_refresh and access_token_data["token"] and access_token_data["expiry"] > datetime.now(timezone.utc):
        return access_token_data["token"]

    logger.info("جلب/تجديد توكن الوصول من Vulcan Labs.")
    url = AUTH_API_URL
    payload = {"device_id": DEVICE_ID, "order_id": "", "product_id": "", "purchase_token": "", "subscription_id": ""}
    headers = {
        "User-Agent": "Chat Smith Android, Version 4.0.5(1032)",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-vulcan-application-id": "com.smartwidgetlabs.chatgpt",
        "x-vulcan-request-id": "9149487891757687027212"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status() # إطلاق استثناء إذا كانت الحالة HTTP غير ناجحة (4xx أو 5xx)
        data = response.json()
        
        token = data.get("AccessToken", "")
        expiry_str = data.get("AccessTokenExpiration")
        
        if expiry_str:
            expiry = parser.isoparse(expiry_str).astimezone(timezone.utc)
        else:
            # تعيين وقت انتهاء صلاحية افتراضي في حال عدم توفره
            expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
            
        access_token_data = {"token": token, "expiry": expiry}
        return token
    except Exception as e:
        logger.error(f"فشل الحصول على التوكن: {e}")
        return ""

# --- 2. وظيفة الاستعلام من Vulcan Labs API ---
def query_vulcan(token, messages):
    """إرسال سجل الدردشة إلى Vulcan Labs Chat API والحصول على الرد."""
    url = CHAT_API_URL
    payload = {
        "model": "gpt-4o-mini",
        "user": DEVICE_ID,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "nsfw_check": True
    }
    headers = {
        "User-Agent": "Chat Smith Android, Version 4.0.5(1032)",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-auth-token": token,
        "authorization": f"Bearer {token}",
        "x-vulcan-application-id": "com.smartwidgetlabs.chatgpt",
        "x-vulcan-request-id": "9149487891757687028153"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # استخراج المحتوى المتوقع
        if data.get("choices") and data["choices"][0].get("Message") and data["choices"][0]["Message"].get("content"):
            return data["choices"][0]["Message"]["content"]
        else:
            logger.error(f"رد غير متوقع من Vulcan: {data}")
            return "حدث خطأ أثناء معالجة الرد من النموذج."
    except Exception as e:
        logger.error(f"خطأ في طلب Vulcan: {e}")
        return "حدث خطأ أثناء الاتصال بالنموذج."

# --- 3. وظيفة إرسال الرسائل إلى ماسنجر ---
def send_message(recipient_id, message_text, quick_replies=None):
    """إرسال رسالة إلى المستخدم، تدعم الردود السريعة."""
    
    # بناء حمولة الرسالة
    message_payload = {"text": message_text}
    
    if quick_replies:
        message_payload["quick_replies"] = quick_replies

    data = {
        "recipient": {"id": recipient_id},
        "message": message_payload,
        "messaging_type": "RESPONSE"
    }
    
    # إرسال طلب POST إلى Messenger API
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(
            "https://graph.facebook.com/v19.0/me/messages",
            params=params,
            headers=headers,
            data=json.dumps(data)
        )
        if response.status_code != 200:
            logger.error(f"فشل إرسال الرسالة: {response.status_code} - {response.text}")
        else:
            logger.info(f"تم إرسال الرسالة بنجاح إلى: {recipient_id}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"خطأ في طلب الـ API لـ Messenger: {e}")

# --- 4. وظيفة معالجة الرسالة الرئيسية (تنفذ في خيط منفصل) ---
def process_message_thread(sender_id, user_text):
    """
    تنفذ منطق استدعاء الـ API والرد. 
    يتم تشغيلها في خيط منفصل لتجنب انتهاء مهلة الويب هوك.
    """
    
    # رسالة للمستخدم أثناء المعالجة
    send_message(sender_id, "جارٍ معالجة طلبك، لحظة من فضلك...")

    token = get_access_token()
    if not token:
        send_message(sender_id, "فشل الحصول على رمز التوكن اللازم للوصول إلى النموذج. يرجى المحاولة مرة أخرى.")
        return

    # إعداد سجل الدردشة
    if sender_id not in user_chats:
        user_chats[sender_id] = []

    # إضافة رسالة المستخدم
    user_chats[sender_id].append({"role": "user", "content": user_text})

    # تقليم سجل الدردشة للحفاظ على الحجم (2 * MAX_CHAT_HISTORY بسبب دور 'user' و 'assistant')
    if len(user_chats[sender_id]) > MAX_CHAT_HISTORY * 2:
        user_chats[sender_id] = user_chats[sender_id][-MAX_CHAT_HISTORY*2:]

    # استدعاء Vulcan API
    reply = query_vulcan(token, user_chats[sender_id])

    # إضافة رد المساعد إلى سجل الدردشة
    user_chats[sender_id].append({"role": "assistant", "content": reply})

    # إعداد أزرار الرد السريع (Quick Replies)
    quick_replies = [
        {"content_type": "text", "title": "سؤال جديد", "payload": "NEW_QUESTION"},
        {"content_type": "text", "title": "مسح السجل", "payload": "CLEAR_HISTORY"},
        {"content_type": "text", "title": "المساعدة", "payload": "HELP"}
    ]
    
    # الرد على المستخدم بنتيجة الـ API مع الأزرار
    send_message(sender_id, reply, quick_replies)


# --- 5. نقطة نهاية الويب هوك (GET) للتحقق ---
@app.route("/", methods=["GET"])
def verify_webhook():
    """التحقق من الويب هوك باستخدام رمز التوثيق boykta 2023."""
    try:
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                logger.info("تم التحقق من الويب هوك بنجاح!")
                return challenge, 200
            else:
                return "Verification token mismatch", 403
        
        return "Webhook setup endpoint.", 200

    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من الويب هوك: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- 6. نقطة نهاية الويب هوك (POST) لاستقبال الرسائل ---
@app.route("/", methods=["POST"])
def webhook():
    """استقبال رسائل المستخدمين ومعالجتها."""
    try:
        data = request.json
        logger.info(f"استلام بيانات الويب هوك.")

        if data.get("object") == "page":
            for entry in data["entry"]:
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event["sender"]["id"]
                    
                    if messaging_event.get("message"):
                        
                        # معالجة ضغطة زر الرد السريع (Quick Reply)
                        if 'quick_reply' in messaging_event['message']:
                            payload = messaging_event['message']['quick_reply']['payload']
                            
                            if payload == "CLEAR_HISTORY":
                                user_chats[sender_id] = []
                                send_message(sender_id, "تم مسح سجل محادثتك بالكامل. يمكنك البدء بسؤال جديد الآن!")
                            elif payload == "HELP":
                                send_message(sender_id, "أنا بوت يعمل بالذكاء الاصطناعي ويستخدم نموذج GPT-4o-mini لمعالجة النصوص. أرسل لي أي سؤال أو كود!")
                            elif payload == "NEW_QUESTION":
                                send_message(sender_id, "تفضل، ما هو سؤالك الجديد؟")
                            else:
                                send_message(sender_id, f"تلقيت الأمر: {payload}. تفضل بطرح سؤالك.")
                        
                        # معالجة الرسالة النصية
                        elif 'text' in messaging_event['message']:
                            message_text = messaging_event["message"]["text"]
                            
                            # تشغيل المعالجة في خيط منفصل لتجنب انتهاء مهلة الويب هوك (10 ثوانٍ)
                            threading.Thread(target=process_message_thread, args=(sender_id, message_text)).start()
                            
                        else:
                            # الرد على أنواع الرسائل الأخرى (ملصقات، صور، إلخ)
                            send_message(sender_id, "عذراً، أنا أستطيع معالجة الرسائل النصية فقط.")
                            
                    # معالجة رسالة "بدء الاستخدام" (Postback) - اختيارية، لكن تركناها للتعامل مع أي حالة قديمة
                    elif messaging_event.get("postback"):
                         send_message(sender_id, "أهلاً بك! يمكنك البدء بإرسال سؤالك مباشرةً.")


            return "OK", 200
        else:
            return "Event not from a page", 403
            
    except Exception as e:
        logger.error(f"خطأ في معالجة رسالة الويب هوك: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# تشغيل التطبيق محلياً (لن يتم تنفيذه على Vercel)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
