import os
import json
import logging
import requests
from flask import Flask, request, jsonify

# =========================================================
# === إعدادات البوت والـ API (يجب تغيير هذه القيم) ===
# =========================================================

# رمز التوكن الخاص بصفحة فيسبوك (Page Access Token)
# يجب الحصول عليه من تطبيق فيسبوك الخاص بك
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "YOUR_FACEBOOK_PAGE_ACCESS_TOKEN_HERE")

# رمز التحقق من الويب هوك الذي وضعته في إعدادات فيسبوك
VERIFY_TOKEN = "boykta 2023"

# عنوان API الخارجي لمعالجة النصوص
API_URL = "https://sonnet3-5.free.nf/api/reasoning.php"

# =========================================================
# === تهيئة Flask والتسجيل (Logging) ===
# =========================================================

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================
# === دالة إرسال الرسائل إلى فيسبوك Messenger ===
# =========================================================

def send_facebook_message(recipient_id, message_text, quick_replies=None):
    """
    إرسال رسالة إلى فيسبوك Messenger باستخدام Page Access Token.
    يمكن إضافة Quick Replies (أزرار) اختيارياً.
    """
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    
    # بناء حمولة (Payload) الرسالة
    data = {
        'recipient': {'id': recipient_id},
        'message': {'text': message_text}
    }

    # إضافة الأزرار (Quick Replies) إذا كانت موجودة
    if quick_replies:
        data['message']['quick_replies'] = quick_replies

    try:
        response = requests.post(
            f"https://graph.facebook.com/v19.0/me/messages",
            params=params,
            headers=headers,
            data=json.dumps(data)
        )
        response.raise_for_status() # إلقاء استثناء لأكواد الحالة الخاطئة (4xx أو 5xx)
        logger.info(f"تم إرسال الرسالة بنجاح إلى {recipient_id}")
    except requests.exceptions.RequestException as e:
        logger.error(f"فشل إرسال الرسالة إلى فيسبوك: {e}")
        logger.error(f"رد فيسبوك: {response.text}")

# =========================================================
# === دالة معالجة النصوص واستدعاء API الخارجي ===
# =========================================================

def process_and_reply(sender_id, user_text):
    """
    استدعاء API الخارجي وإرسال النتيجة مرة أخرى للمستخدم.
    """
    logger.info(f"معالجة النص من {sender_id}: {user_text}")

    # إرسال رسالة انتظار للمستخدم
    send_facebook_message(sender_id, "جارٍ معالجة طلبك باستخدام الـ API الخارجي، لحظة من فضلك...")

    try:
        # إعداد بيانات الطلب (باستخدام المعامل 'text')
        payload = {'text': user_text}
        
        # إرسال طلب GET إلى الـ API الخارجي
        response = requests.get(API_URL, params=payload, timeout=30)
        response.raise_for_status() # التأكد من حالة 200

        # افتراض أن الرد هو نص عادي أو بيانات يمكن طباعتها مباشرة
        api_result = response.text
        
        # تحديد الأزرار (Quick Replies) المراد إرسالها مع الرد
        # يمكنك تخصيص هذه الأزرار حسب وظيفة البوت
        buttons = [
            {"content_type": "text", "title": "معالجة جديدة", "payload": "NEW_PROCESS"},
            {"content_type": "text", "title": "مساعدة", "payload": "HELP"},
        ]
        
        # الرد على المستخدم بنتيجة الـ API مع الأزرار
        send_facebook_message(
            sender_id, 
            f"**نتيجة المعالجة:**\n\n{api_result}",
            quick_replies=buttons
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"خطأ في الاتصال بالـ API الخارجي: {e}")
        send_facebook_message(
            sender_id, 
            "عذراً، حدث خطأ أثناء محاولة الاتصال بخدمة المعالجة الخارجية."
        )
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {e}")
        send_facebook_message(
            sender_id, 
            "حدث خطأ غير متوقع. يرجى المحاولة لاحقاً."
        )


# =========================================================
# === مسار الـ Webhook لتأكيد فيسبوك واستقبال الرسائل ===
# =========================================================

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    نقطة النهاية الرئيسية لمعالجة طلبات الويب هوك من فيسبوك.
    """
    if request.method == 'GET':
        # --- معالجة طلب التحقق (Verification) ---
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                logger.info("تم التحقق من الويب هوك بنجاح!")
                return challenge, 200
            else:
                return "رمز التحقق غير صحيح", 403
        
        # إذا لم يكن طلب تحقُّق، نرجع خطأ 400
        return "طلب غير صحيح", 400

    elif request.method == 'POST':
        # --- معالجة الرسائل الواردة (Message Handling) ---
        data = request.get_json()
        logger.info(f"البيانات الواردة: {data}")

        if data.get("object") == "page":
            for entry in data["entry"]:
                for event in entry["messaging"]:
                    sender_id = event["sender"]["id"]
                    
                    # 1. معالجة الرسائل النصية
                    if "message" in event and "text" in event["message"]:
                        user_text = event["message"]["text"]
                        process_and_reply(sender_id, user_text)
                    
                    # 2. معالجة النقرات على الأزرار (Quick Replies أو Postbacks)
                    elif "postback" in event:
                        # يمكنك إضافة منطق خاص لمعالجة الـ Postbacks هنا إذا استخدمت أزرار القوالب
                        postback_payload = event["postback"]["payload"]
                        send_facebook_message(sender_id, f"تلقيت الأمر: {postback_payload}")

        return "EVENT_RECEIVED", 200

# =========================================================
# === تشغيل التطبيق (للنشر على Vercel، هذا القسم اختياري) ===
# =========================================================

# ملاحظة: Vercel يستخدم بروتوكول WSGI تلقائياً، لذا هذا الجزء هو للاختبار المحلي
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
