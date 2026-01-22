"""
Message Variation Generator API
Generates unique WhatsApp message variations to avoid spam detection
Uses Gemini Flash for Indonesian casual language generation
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
from dotenv import load_dotenv

from emergentintegrations.llm.chat import LlmChat, UserMessage
from routes.auth import get_current_user, User

load_dotenv()

router = APIRouter()

class MessageVariationRequest(BaseModel):
    original_message: str
    num_variations: int = 5  # Default 5 variations
    context: Optional[str] = None  # Optional: promo, follow-up, greeting, etc.

class MessageVariationResponse(BaseModel):
    original: str
    variations: List[str]
    count: int

SYSTEM_PROMPT = """Kamu adalah asisten yang membantu membuat variasi pesan WhatsApp untuk customer service.

ATURAN PENTING:
1. Gunakan bahasa Indonesia sehari-hari yang CASUAL tapi tetap SOPAN dan RAMAH
2. JANGAN PERNAH gunakan kata "gue", "lu", "lo", "elo", "gw"
3. SELALU gunakan kata "aku", "kakak", "kak", "saya" untuk sapaan
4. Tambahkan sentuhan PERSUASIF yang halus (ajakan, manfaat, urgensi ringan)
5. Variasi harus BERBEDA struktur kalimatnya, bukan cuma ganti kata
6. Pertahankan MAKNA dan INFORMASI penting dari pesan asli
7. Gunakan emoji secukupnya (1-3 per pesan) untuk kesan friendly
8. Panjang pesan harus MIRIP dengan pesan asli

GAYA BAHASA:
- Friendly & approachable: "Hai kak", "Halo kakak", "Kak", "Hi kak"
- Casual tapi sopan: "nih", "loh", "yuk", "deh", "ya", "dong"
- Persuasif halus: "sayang banget kalau dilewatin", "khusus buat kakak", "cuma sampai..."

FORMAT OUTPUT:
- Berikan HANYA variasi pesan, satu per baris
- JANGAN tambahkan penomoran atau bullet points
- JANGAN tambahkan penjelasan atau komentar
- JANGAN tambahkan pembuka atau penutup"""

@router.post("/message-variations/generate", response_model=MessageVariationResponse)
async def generate_message_variations(
    request: MessageVariationRequest,
    user: User = Depends(get_current_user)
):
    """Generate unique message variations for WhatsApp"""
    
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM API key not configured")
    
    if not request.original_message.strip():
        raise HTTPException(status_code=400, detail="Original message cannot be empty")
    
    if request.num_variations < 1 or request.num_variations > 10:
        raise HTTPException(status_code=400, detail="Number of variations must be between 1 and 10")
    
    try:
        # Initialize Gemini Flash chat
        chat = LlmChat(
            api_key=api_key,
            session_id=f"msg-var-{uuid.uuid4()}",
            system_message=SYSTEM_PROMPT
        ).with_model("gemini", "gemini-2.5-flash")
        
        # Build the prompt
        context_hint = ""
        if request.context:
            context_hint = f"\nKonteks pesan: {request.context}"
        
        prompt = f"""Buatkan {request.num_variations} variasi pesan WhatsApp dari pesan berikut:{context_hint}

PESAN ASLI:
{request.original_message}

Ingat: Casual, sopan, persuasif, pakai "aku/kakak/kak", JANGAN pakai "gue/lu"."""

        user_message = UserMessage(text=prompt)
        
        # Get response from Gemini
        response = await chat.send_message(user_message)
        
        # Parse variations (split by newlines, clean up)
        variations = []
        for line in response.strip().split('\n'):
            line = line.strip()
            # Skip empty lines and lines that look like comments
            if line and not line.startswith('#') and not line.startswith('*') and not line.startswith('-'):
                # Remove numbering if present (1., 2., etc.)
                import re
                cleaned = re.sub(r'^\d+[\.\)]\s*', '', line)
                if cleaned:
                    variations.append(cleaned)
        
        # Ensure we have the requested number of variations
        variations = variations[:request.num_variations]
        
        if not variations:
            raise HTTPException(status_code=500, detail="Failed to generate variations")
        
        return MessageVariationResponse(
            original=request.original_message,
            variations=variations,
            count=len(variations)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating message variations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate variations: {str(e)}")


@router.get("/message-variations/templates")
async def get_message_templates(user: User = Depends(get_current_user)):
    """Get pre-built message templates for common scenarios"""
    
    templates = [
        {
            "id": "promo",
            "name": "Promo/Diskon",
            "template": "Halo kak! Ada promo spesial nih buat kakak. [DETAIL PROMO]. Yuk buruan sebelum kehabisan! 🎉"
        },
        {
            "id": "follow_up",
            "name": "Follow Up",
            "template": "Hai kak, aku mau follow up soal [TOPIK] kemarin. Gimana kak, ada yang bisa aku bantu? 😊"
        },
        {
            "id": "greeting",
            "name": "Sapaan Awal",
            "template": "Halo kak! Aku dari [NAMA BISNIS]. Ada yang bisa aku bantu hari ini? 👋"
        },
        {
            "id": "reminder",
            "name": "Reminder/Pengingat",
            "template": "Hai kak, friendly reminder nih buat [DETAIL]. Jangan sampai kelewatan ya kak! ⏰"
        },
        {
            "id": "thank_you",
            "name": "Ucapan Terima Kasih",
            "template": "Makasih banyak kak sudah [AKSI]! Semoga kakak puas ya. Kalau ada apa-apa hubungi aku lagi ya kak 🙏"
        }
    ]
    
    return {"templates": templates}
