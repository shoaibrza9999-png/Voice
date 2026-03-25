from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime

from app.config import settings
from app.database import get_db
from app.models import User, Context, Transaction, Category
from app.services.whatsapp_service import whatsapp_service
from app.services.transcription_service import transcription_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhook",
    tags=["whatsapp"]
)

@router.get("")
async def verify_webhook(request: Request):
    """
    Webhook verification for WhatsApp Cloud API.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            return PlainTextResponse(challenge, status_code=200)
        else:
            raise HTTPException(status_code=403, detail="Verification token mismatch")

    raise HTTPException(status_code=400, detail="Missing parameters")

@router.post("")
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handles incoming messages (text/audio) from WhatsApp.
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    # WhatsApp webhook structure check
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for msg in messages:
                    # Determine sender and message type
                    whatsapp_id = msg.get("from")
                    msg_type = msg.get("type")

                    # Ensure user exists
                    user = db.query(User).filter(User.whatsapp_id == whatsapp_id).first()
                    if not user:
                        # Extract name if available
                        name = value.get("contacts", [{}])[0].get("profile", {}).get("name")
                        user = User(whatsapp_id=whatsapp_id, name=name)
                        db.add(user)
                        db.commit()
                        db.refresh(user)

                    # Get user context
                    context = db.query(Context).filter(Context.whatsapp_id == whatsapp_id).first()
                    if not context:
                        context = Context(whatsapp_id=whatsapp_id)
                        db.add(context)
                        db.commit()
                        db.refresh(context)

                    # Extract text content
                    text_content = ""

                    if msg_type == "text":
                        text_content = msg.get("text", {}).get("body", "")
                    elif msg_type == "audio":
                        # Handle audio message
                        media_id = msg.get("audio", {}).get("id")
                        if media_id:
                            # 1. Download media
                            file_path = await transcription_service.download_media(media_id)
                            if file_path:
                                # 2. Transcribe
                                text_content = await transcription_service.transcribe_audio(file_path)
                                if not text_content:
                                    await whatsapp_service.send_text_message(whatsapp_id, "Sorry, I couldn't transcribe the audio properly.")
                                    continue
                    elif msg_type == "interactive":
                        # Handle interactive button replies
                        interactive_reply = msg.get("interactive", {})
                        button_reply = interactive_reply.get("button_reply", {})
                        reply_id = button_reply.get("id")

                        if reply_id == "confirm_add" and context.last_action == "pending_add":
                            await handle_confirm_add(whatsapp_id, context, user, db)
                            continue
                        elif reply_id == "edit_add" and context.last_action == "pending_add":
                            context.last_action = None
                            context.last_data = None
                            db.commit()
                            await whatsapp_service.send_text_message(whatsapp_id, "Got it! Please provide the details again or let me know what to correct.")
                            continue
                        elif reply_id == "cancel_add" and context.last_action == "pending_add":
                            context.last_action = None
                            context.last_data = None
                            db.commit()
                            await whatsapp_service.send_text_message(whatsapp_id, "Action cancelled.")
                            continue

                    if text_content:
                        # Send text to LLM
                        llm_response = await llm_service.process_message(
                            message=text_content,
                            user_timezone=user.timezone,
                            context_summary=context.summary
                        )

                        # Update conversation context
                        new_context_entry = f"User: {text_content}\nBot Action: {llm_response.get('action')}\nBot Response: {llm_response.get('reply', '')}\n"
                        # Append to existing summary, keeping last 5 exchanges
                        if context.summary:
                            lines = context.summary.split('\n')
                            if len(lines) > 20: # Keep roughly last ~6 exchanges
                                lines = lines[-20:]
                            context.summary = "\n".join(lines) + "\n" + new_context_entry
                        else:
                            context.summary = new_context_entry
                        db.commit()

                        await handle_llm_action(whatsapp_id, llm_response, context, user, db)

    return {"status": "ok"}

async def handle_llm_action(whatsapp_id: str, llm_response: dict, context: Context, user: User, db: Session):
    action = llm_response.get("action")
    data = llm_response.get("data")
    reply = llm_response.get("reply")

    if action == "reply":
        await whatsapp_service.send_text_message(whatsapp_id, reply or "I'm not sure how to help with that.")

    elif action == "add_transaction":
        # Human-in-the-loop: Ask for confirmation
        summary = f"Add {data.get('type')}: ${data.get('amount')} to {data.get('category')} on {data.get('date')}?\nNote: {data.get('description')}"
        buttons = [
            {"id": "confirm_add", "title": "Yes"},
            {"id": "edit_add", "title": "No, Edit"},
            {"id": "cancel_add", "title": "Cancel"}
        ]

        # Save pending state
        context.last_action = "pending_add"
        context.last_data = json.dumps(data)
        db.commit()

        await whatsapp_service.send_interactive_buttons(whatsapp_id, summary, buttons)

    elif action == "remove_transaction":
        s_no = data.get("s_no")
        tx = db.query(Transaction).filter(Transaction.id == s_no, Transaction.user_id == user.id).first()
        if tx:
            db.delete(tx)
            db.commit()
            await whatsapp_service.send_text_message(whatsapp_id, f"Successfully removed transaction #{s_no}.")
        else:
            await whatsapp_service.send_text_message(whatsapp_id, f"Transaction #{s_no} not found.")

    elif action == "edit_transaction":
        s_no = data.get("s_no")
        field = data.get("field_to_edit")
        new_value = data.get("new_value")

        tx = db.query(Transaction).filter(Transaction.id == s_no, Transaction.user_id == user.id).first()
        if tx:
            if field == "amount":
                try:
                    tx.amount = float(new_value)
                except ValueError:
                    await whatsapp_service.send_text_message(whatsapp_id, "Invalid amount format. Expected a number.")
                    return
            elif field == "description":
                tx.description = new_value
            elif field == "date":
                try:
                    tx.date = datetime.strptime(new_value, "%Y-%m-%d").date()
                except ValueError:
                    await whatsapp_service.send_text_message(whatsapp_id, "Invalid date format. Expected YYYY-MM-DD.")
                    return
            elif field == "category":
                # Find or create category
                cat = db.query(Category).filter(Category.name == new_value).first()
                if not cat:
                    cat = Category(name=new_value, type="expense") # Default to expense, logic could be improved
                    db.add(cat)
                    db.commit()
                    db.refresh(cat)
                tx.category_id = cat.id

            db.commit()
            await whatsapp_service.send_text_message(whatsapp_id, f"Successfully updated transaction #{s_no}.")
        else:
            await whatsapp_service.send_text_message(whatsapp_id, f"Transaction #{s_no} not found.")

    elif action == "find_transaction":
        # Simplified find: search description
        query = data.get("query", "").lower()
        results = db.query(Transaction).filter(Transaction.user_id == user.id).all()
        found = [tx for tx in results if query in (tx.description or "").lower()]

        if found:
            msg = f"Found {len(found)} results:\n"
            for tx in found:
                msg += f"#{tx.id}: ${tx.amount} on {tx.date} - {tx.description}\n"
            await whatsapp_service.send_text_message(whatsapp_id, msg)
        else:
            await whatsapp_service.send_text_message(whatsapp_id, "No transactions found matching your query.")

    elif action == "filter_transactions":
        # Simplified filter: by category
        cat_name = data.get("category")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        query = db.query(Transaction).filter(Transaction.user_id == user.id)

        if cat_name:
            cat = db.query(Category).filter(Category.name == cat_name).first()
            if cat:
                query = query.filter(Transaction.category_id == cat.id)

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                query = query.filter(Transaction.date >= start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
                query = query.filter(Transaction.date <= end_dt)
            except ValueError:
                pass

        results = query.all()
        if results:
            msg = f"Found {len(results)} results:\n"
            for tx in results:
                msg += f"#{tx.id}: ${tx.amount} on {tx.date} - {tx.description}\n"
            await whatsapp_service.send_text_message(whatsapp_id, msg)
        else:
            await whatsapp_service.send_text_message(whatsapp_id, "No transactions found matching those filters.")


async def handle_confirm_add(whatsapp_id: str, context: Context, user: User, db: Session):
    """
    Executes the database insertion when user confirms 'Yes' for adding a transaction.
    """
    try:
        data = json.loads(context.last_data)

        # 1. Find or create Category
        cat_name = data.get("category", "Uncategorized")
        cat_type = data.get("type", "expense")
        category = db.query(Category).filter(Category.name == cat_name).first()

        if not category:
            category = Category(name=cat_name, type=cat_type)
            db.add(category)
            db.commit()
            db.refresh(category)

        # 2. Add Transaction
        tx_date_str = data.get("date")
        try:
            tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d").date()
        except ValueError:
            tx_date = datetime.utcnow().date()

        transaction = Transaction(
            amount=float(data.get("amount")),
            description=data.get("description", ""),
            date=tx_date,
            user_id=user.id,
            category_id=category.id
        )
        db.add(transaction)

        # Clear context
        context.last_action = None
        context.last_data = None
        db.commit()

        await whatsapp_service.send_text_message(whatsapp_id, f"✅ Successfully added ${transaction.amount} to {category.name}.")
    except Exception as e:
        logger.error(f"Error saving transaction: {e}")
        db.rollback()
        await whatsapp_service.send_text_message(whatsapp_id, "Sorry, there was an error saving your transaction.")
