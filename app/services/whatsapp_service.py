import httpx
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.api_token = settings.WHATSAPP_API_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v19.0/{self.phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    async def send_text_message(self, to_phone_number: str, text: str):
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone_number,
            "type": "text",
            "text": {"body": text}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            response = getattr(e, 'response', None)
            if response:
                logger.error(f"Response: {response.text}")
            return None

    async def send_interactive_buttons(self, to_phone_number: str, text_body: str, buttons: list):
        """
        Sends an interactive button message.
        buttons list format: [{"id": "btn_1", "title": "Yes"}, {"id": "btn_2", "title": "No, Edit"}]
        Maximum of 3 buttons.
        """
        interactive_buttons = []
        for btn in buttons[:3]:
            interactive_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": btn["title"]
                }
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text_body},
                "action": {
                    "buttons": interactive_buttons
                }
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error sending WhatsApp interactive message: {e}")
            response = getattr(e, 'response', None)
            if response:
                logger.error(f"Response: {response.text}")
            return None

whatsapp_service = WhatsAppService()
