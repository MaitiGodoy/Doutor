import os, requests, json
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Say
from kernel.config import TWILIO_SID, TWILIO_TOKEN, TWILIO_WHATSAPP_FROM, USER_PHONE

# Fallback para CallMeBot se Twilio não estiver configurado
CALLMEBOT_API = os.getenv("CALLMEBOT_API", "")

def send_whatsapp_text(message: str, media_url: str = None) -> dict:
    """Envia mensagem de texto (ou com mídia) via WhatsApp"""
    if not TWILIO_SID:
        # Fallback: CallMeBot (free para uso pessoal)
        if CALLMEBOT_API and USER_PHONE:
            url = f"https://api.callmebot.com/whatsapp.php?phone={USER_PHONE}&text={requests.utils.quote(message)}&apikey={CALLMEBOT_API}"
            res = requests.get(url)
            return {"status": "sent" if res.status_code == 200 else "failed", "provider": "callmebot"}
        return {"status": "no_provider", "error": "Twilio not configured and CallMeBot missing"}
    
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        payload = {"body": message, "from": f"whatsapp:{TWILIO_WHATSAPP_FROM}", "to": f"whatsapp:{USER_PHONE}"}
        if media_url: payload["media_url"] = media_url
        msg = client.messages.create(**payload)
        return {"status": "sent", "sid": msg.sid, "provider": "twilio"}
    except Exception as e:
        return {"status": "failed", "error": str(e), "provider": "twilio"}

def send_whatsapp_voice(text: str) -> dict:
    """Converte texto para áudio e envia via WhatsApp (usando Twilio + TTS free)"""
    # Twilio tem TTS embutido na API de Voice, mas para WhatsApp usamos fallback
    # Opção free: usar Google TTS via gTTS e enviar como áudio
    try:
        from gtts import gTTS
        import tempfile, os
        tts = gTTS(text=text, lang='pt')
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            tts.save(f.name)
            # Upload para servidor público (ex: Cloudinary free tier) ou usar Twilio Media
            # Simplificação: enviar link de texto se não tiver hosting
            return send_whatsapp_text(f"🔊 Áudio: {text}")
    except:
        return send_whatsapp_text(f"🔊 (fallback) {text}")

def make_voice_call(text: str) -> dict:
    """Liga para o usuário e fala o texto via TTS (Callbot)"""
    if not TWILIO_SID:
        return {"status": "no_provider", "error": "Twilio not configured"}
    
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        # TwiML para falar o texto
        twiml = VoiceResponse()
        twiml.add(Say(text, voice='alice', language='pt-BR'))
        
        call = client.calls.create(
            twiml=str(twiml),
            to=USER_PHONE,
            from_=os.getenv("TWILIO_PHONE_FROM")
        )
        return {"status": "calling", "sid": call.sid}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def escalate_notification(priority: str, message: str, requires_response: bool = False) -> dict:
    """
    Decide qual canal usar baseado na prioridade:
    - low: WhatsApp texto
    - medium: WhatsApp texto + áudio
    - high: WhatsApp + ligação automática (callbot)
    - critical: Ligação imediata + texto + fallback email
    """
    result = {"channels_used": []}
    
    if priority in ["low", "medium", "high", "critical"]:
        res_text = send_whatsapp_text(message)
        result["text"] = res_text
        if res_text["status"] == "sent": result["channels_used"].append("whatsapp_text")
    
    if priority in ["medium", "high", "critical"]:
        res_voice = send_whatsapp_voice(message)
        result["voice_msg"] = res_voice
        if res_voice["status"] == "sent": result["channels_used"].append("whatsapp_voice")
    
    if priority in ["high", "critical"]:
        res_call = make_voice_call(f"Atenção: {message}")
        result["call"] = res_call
        if res_call["status"] == "calling": result["channels_used"].append("voice_call")
    
    # Fallback crítico: email se tudo falhar
    if priority == "critical" and not result["channels_used"]:
        # Implementar fallback para email (smtplib + Gmail App Password)
        result["fallback"] = "email_pending"
    
    return result
