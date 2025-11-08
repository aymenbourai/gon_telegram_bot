import os
import logging
import requests
import json
from flask import Flask, request, jsonify

# تهيئة التسجيل (Logging)
# هذا يساعد في تتبع الطلبات والأخطاء على Vercel
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- إعدادات البوت والـ API (يرجى التعديل) ---
# رمز التوثيق للـ Webhook الذي يتم إدخاله في إعدادات فيسبوك (كما طلب المستخدم)
VERIFY_TOKEN = 'boykta 2023'

# رمز الوصول الخاص بالصفحة. يجب تعيينه كمتغير بيئة سري على Vercel
# (مثال: PAGE_ACCESS_TOKEN). قم بوضع قيمة وهمية هنا لتذكيرك بالتغيير.
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN', 'ضع_رمز_الوصول_الخاص_بصفحتك_هنا')

# رابط الـ API الخارجي الذي سيتم استدعاؤه
API_URL = "https://sonnet3-5.free.nf/api/reasoning.php"

# تهيئة تطبيق Flask
app = Flask(__name__)

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
            final_message = f"**نتيجة المعالجة:**\n\n{api_result}"
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
@app.route("/", methods=["GET"])
def verify_webhook():
    """
    نقطة نهاية للتحقق من الويب هوك لفيسبوك.
    تستخدم رمز VERIFY_TOKEN ('boykta 2023')
    """
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
        
        return "Webhook setup endpoint. Pass correct parameters for verification.", 200

    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من الويب هوك: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- 4. نقطة نهاية الويب هوك (POST) لاستقبال الرسائل ---
@app.route("/", methods=["POST"])
def webhook():
    """
    نقطة نهاية لاستقبال رسائل المستخدمين من فيسبوك.
    """
    try:
        data = request.json
        logger.info(f"استلام بيانات الويب هوك: {data}")

        if data.get("object") == "page":
            for entry in data["entry"]:
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event["sender"]["id"]
                    
                    # تحقق مما إذا كانت رسالة نصية
                    if messaging_event.get("message"):
                        # تجاهل رسائل الإيموجي أو المرفقات، وركز على النص
                        if 'text' in messaging_event['message']:
                            message_text = messaging_event["message"]["text"]
                            call_api_and_respond(sender_id, message_text)
                        else:
                            # للرد على أي مرفقات أو إيموجي برسالة بسيطة
                            send_message(sender_id, "عذراً، أنا أستطيع معالجة الرسائل النصية فقط.")
                            
                    # يمكنك إضافة معالجة لـ Quick Reply هنا إذا كان الرد هو ضغطة زر
                    elif messaging_event.get("postback"):
                        # مثال على معالجة زر "ابدأ" إذا لم يتم إلغاؤه
                        payload = messaging_event["postback"]["payload"]
                        send_message(sender_id, f"تلقيت الأمر: {payload}")
                        
                    # معالجة الردود السريعة (Quick Replies)
                    elif messaging_event.get("quick_reply"):
                        payload = messaging_event["quick_reply"]["payload"]
                        if payload == "PAYLOAD_DETAILS":
                             send_message(sender_id, "سأبحث عن مزيد من التفاصيل لك...")
                        elif payload == "PAYLOAD_NEW_QUESTION":
                            send_message(sender_id, "تفضل بطرح سؤالك الجديد!")
                        else:
                             send_message(sender_id, f"تلقيت استجابة الرد السريع: {payload}")


            return "OK", 200
        else:
            return "Event not from a page", 403
            
    except Exception as e:
        logger.error(f"خطأ في معالجة رسالة الويب هوك: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# تشغيل التطبيق محلياً (لن يتم تشغيله على Vercel لأن Vercel يدير التشغيل)
if __name__ == "__main__":
    # تشغيل التطبيق على منفذ محلي للاختبار
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
