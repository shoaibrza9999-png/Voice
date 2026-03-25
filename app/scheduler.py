import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import SessionLocal
from app.models import User, Transaction, Category
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def send_daily_summaries():
    """
    Sends a daily summary to all users.
    """
    logger.info("Running daily summaries task...")
    db = SessionLocal()
    try:
        users = db.query(User).all()

        import pytz

        for user in users:
            try:
                tz = pytz.timezone(user.timezone or "UTC")
            except pytz.UnknownTimeZoneError:
                tz = pytz.UTC

            today = datetime.now(tz).date()

            # Get transactions for today
            transactions = db.query(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.date == today
            ).all()

            if not transactions:
                continue

            total_income = 0.0
            total_expense = 0.0

            for tx in transactions:
                cat = db.query(Category).filter(Category.id == tx.category_id).first()
                if cat and cat.type == 'income':
                    total_income += tx.amount
                else:
                    total_expense += tx.amount

            message = f"📊 *Daily Summary for {today}*\n\n"
            message += f"💵 Total Income: ${total_income:.2f}\n"
            message += f"💸 Total Expense: ${total_expense:.2f}\n\n"
            message += f"Net: ${(total_income - total_expense):.2f}"

            await whatsapp_service.send_text_message(user.whatsapp_id, message)
            await asyncio.sleep(0.5) # Basic rate limiting
    except Exception as e:
        logger.error(f"Error in daily summaries: {e}")
    finally:
        db.close()


async def send_weekly_reports():
    """
    Sends a weekly summary to all users.
    """
    logger.info("Running weekly reports task...")
    db = SessionLocal()
    try:
        users = db.query(User).all()
        import pytz

        for user in users:
            try:
                tz = pytz.timezone(user.timezone or "UTC")
            except pytz.UnknownTimeZoneError:
                tz = pytz.UTC

            today = datetime.now(tz).date()
            week_ago = today - timedelta(days=7)

            transactions = db.query(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.date >= week_ago,
                Transaction.date < today
            ).all()

            if not transactions:
                continue

            total_income = 0.0
            total_expense = 0.0
            categories = {}

            for tx in transactions:
                cat = db.query(Category).filter(Category.id == tx.category_id).first()
                if cat:
                    if cat.type == 'income':
                        total_income += tx.amount
                    else:
                        total_expense += tx.amount
                        categories[cat.name] = categories.get(cat.name, 0.0) + tx.amount

            message = f"📈 *Weekly Report ({week_ago} to {today})*\n\n"
            message += f"💵 Income: ${total_income:.2f}\n"
            message += f"💸 Expense: ${total_expense:.2f}\n\n"
            message += "Top Expenses by Category:\n"

            # Sort categories by amount
            sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
            for cat_name, amt in sorted_cats:
                message += f"- {cat_name}: ${amt:.2f}\n"

            await whatsapp_service.send_text_message(user.whatsapp_id, message)
            await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in weekly reports: {e}")
    finally:
        db.close()

def setup_scheduler():
    # Schedule daily at 21:00 (9 PM) UTC
    scheduler.add_job(send_daily_summaries, 'cron', hour=21, minute=0)

    # Schedule weekly on Monday at 08:00 AM UTC
    scheduler.add_job(send_weekly_reports, 'cron', day_of_week='mon', hour=8, minute=0)

    scheduler.start()
    logger.info("Scheduler started.")

def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler shutdown.")
