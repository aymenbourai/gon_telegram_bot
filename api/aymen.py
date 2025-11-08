import os
import logging
import requests
import json
from flask import Flask, request, jsonify

# تهيئة التسجيل (Logging)
# هذا يساعد في تتبع الطلبات والأخطاء على Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name)

# --- إعدادات البوت والـ API (يرجى التعديل) ---
# رمز التوثيق للـ Webhook الذي يتم إدخاله في إعدادات فيسبوك (كما طلب المستخدم)
VERIFY_TOKEN = 'boykta 2023'

# رمز الوصول الخاص بالصفحة. يجب تعيينه كمتغير بيئة سري على Vercel
# (مثال: PAGE_ACCESS_TOKEN). قم بوضع قيمة وهمية هنا لتذكيرك بالتغيير.
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN', 'ضع_رمز_الوصول_الخاص_بصفحتك_هنا')

# رابط الـ API الخارجي الذي سيتم استدعاؤه
API_URL = "https://sonnet3-5.free.nf/api/reasoning.php"

# تهيئة تطبيق Flask
app = Flask(name)

# --- 1. وظيفة إرسال الرسائل إلى ماسنجر ---
def send_message(recipient_id, message_text, quick_replies=None):
    """
    إرسال رسالة إلى المستخدم باستخدام Messenger Send API.
    يمكن أن تتضمن الردود السريعة (Quick Replies) كأزرار.
    """
    logger.info(f"إرسال رسالة إلى: {recipient_id}")

    # بناء حمولة الرسالة
    message_payload = {"text": message_text}
    
    if quick_replies:
        # إذا تم توفير أزرار الردود السريعة
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
            # يمكن إرسال رسالة خطأ داخلية للمستخدم هنا إذا لزم الأمر
        else:
            logger.info("تم إرسال الرسالة بنجاح.")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"خطأ في طلب الـ API لـ Messenger: {e}")

# --- 2. وظيفة معالجة النص واستدعاء الـ API الخارجي ---
def call_api_and_respond(recipient_id, user_text):
    """
    تستدعي الـ API الخارجي وتعالج الرد، ثم ترسل النتيجة للمستخدم.
    """
    
    # رسالة للمستخدم أثناء المعالجة
    send_message(recipient_id, "جارٍ معالجة النص، لحظة من فضلك...")

    try:
        # إعداد بيانات الطلب
        payload = {'text': user_text}
        
        # إرسال طلب GET إلى الـ API الخارجي
        response = requests.get(API_URL, params=payload, timeout=30)
        
        if response.status_code == 200:
            api_result = response.text
            
            # إعداد أزرار الرد السريع كأمثلة (يمكنك تغييرها)
            quick_replies = [
                {"content_type": "text", "title": "مزيد من التفاصيل", "payload": "PAYLOAD_DETAILS"},
                {"content_type": "text", "title": "سؤال جديد", "payload": "PAYLOAD_NEW_QUESTION"}
            ]
            
            # الرد على المستخدم بنتيجة الـ API مع الأزرار
            final_message = f"نتيجة المعالجة:\n\n{api_result}"
            send_message(recipient_id, final_message, quick_replies)
            
        else:
            send_message(recipient_id, f"حدث خطأ في الاتصال بالـ API. رمز الحالة: {response.status_code}")

    except requests.exceptions.RequestException as e:
        logger.error(f"خطأ في طلب الـ API الخارجي: {e}")
        send_message(recipient_id, "عذراً، حدث خطأ أثناء محاولة الاتصال بخدمة المعالجة.")
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {e}")
        send_message(recipient_id, "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى لاحقاً.")

# --- 3. نقطة نهاية الويب هوك (GET) للتحقق ---
