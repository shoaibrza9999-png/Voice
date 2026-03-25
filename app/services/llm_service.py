import json
import logging
from datetime import datetime
from groq import AsyncGroq
from app.config import settings
from app.schemas import AddTransactionSchema, RemoveTransactionSchema, EditTransactionSchema, FindTransactionSchema, FilterTransactionSchema

logger = logging.getLogger(__name__)

# Note: In production you'd use a more capable model for strict function calling or OpenAI's models via openai API if Groq models struggle with complex schemas.
# Here we'll configure it using Groq.
class LLMService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = "llama3-70b-8192" # Replace with 'openai/gpt-oss-120' or 'llama3-groq-70b-8192-tool-use-preview' based on exact availability

        # Define tools using JSON schema
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "add_transaction",
                    "description": "Extracts information to add a new financial transaction (income or expense) to the database.",
                    "parameters": AddTransactionSchema.model_json_schema()
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_transaction",
                    "description": "Removes a financial transaction from the database. Needs the S.No (serial number or ID).",
                    "parameters": RemoveTransactionSchema.model_json_schema()
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_transaction",
                    "description": "Edits a financial transaction. Needs the S.No and the specific field to edit.",
                    "parameters": EditTransactionSchema.model_json_schema()
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_transaction",
                    "description": "Finds a transaction based on proximity to a date, specific names, amounts, or categories.",
                    "parameters": FindTransactionSchema.model_json_schema()
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "filter_transactions",
                    "description": "Filters transactions to view a specific date range or category.",
                    "parameters": FilterTransactionSchema.model_json_schema()
                }
            }
        ]

    def _get_system_prompt(self, user_timezone: str, current_time: datetime, context_summary: str) -> str:
        return f"""You are an AI financial agent designed to process text and voice notes to manage a user's finances.
You classify the intent of the user (add, remove, edit, find, filter) and extract necessary information.

User's Timezone: {user_timezone}
Current Date and Time for the User: {current_time.strftime("%Y-%m-%d %H:%M:%S")}

CRITICAL PRECAUTIONS:
- Always use the current date ({current_time.strftime("%Y-%m-%d")}) if the user doesn't specify a date for a new transaction.
- If they specify "yesterday", map it to the exact date relative to the user's current date.
- Categories should be generalized (e.g. Food, Transport, Rent, Salary, Entertainment, Custom).
- For 'type' in add_transaction, determine if it is 'income' or 'expense' based on the context. Spending/Buying is 'expense', Receiving/Salary is 'income'.
- If the user provides conversational corrections (e.g. "Actually, make that $60 instead of $50"), update your understanding before calling the function.

Previous Conversation Context:
{context_summary if context_summary else 'No prior context.'}
"""

    async def process_message(self, message: str, user_timezone: str = "UTC", context_summary: str = ""):
        """
        Sends the message to the LLM and asks it to determine the appropriate action.
        Returns the called function and its arguments, or a text response if no function is called.
        """
        import pytz

        try:
            tz = pytz.timezone(user_timezone)
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC

        current_time = datetime.now(tz)

        messages = [
            {"role": "system", "content": self._get_system_prompt(user_timezone, current_time, context_summary)},
            {"role": "user", "content": message}
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.1,
            )

            choice = response.choices[0]

            # Check if a tool was called
            if choice.message.tool_calls:
                tool_call = choice.message.tool_calls[0]
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                return {"action": function_name, "data": arguments, "reply": choice.message.content}
            else:
                return {"action": "reply", "data": None, "reply": choice.message.content}

        except Exception as e:
            logger.error(f"Error processing message with LLM: {e}")
            return {"action": "error", "data": None, "reply": "Sorry, I had trouble understanding that."}

llm_service = LLMService()
