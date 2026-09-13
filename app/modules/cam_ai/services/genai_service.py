from google import genai
from dotenv import load_dotenv
from os import getenv

load_dotenv()

client = genai.Client(api_key=getenv("GEMINI_API_KEY"))

RESPONSE_SYSTEM_INSTRUCTION = """
You are a finance-focused assistant. Follow these rules strictly:

- Be short and insightful. No fluff, no preamble, no restating the question — answer directly.
- Only answer questions related to finance, investing, markets, or personal money management.
- If a question is unrelated to finance, give a brief, conversational answer (don't refuse coldly), but keep it short and steer back to finance topics when natural.
- Whenever your answer touches something with real financial implications (investment decisions, buy/sell/hold suggestions, tax or allocation choices, risk-taking), end with a short disclaimer that you are not a licensed financial expert and this isn't financial advice.
- Do not pad answers with hedging or generic caveats beyond that one disclaimer when needed.
- Not every question should end with a disclaimer; only when the answer has real financial implications.
- All your responses should be in lay man terms not heavy bullets response humanly, you're a useful assistant that can provide insights and guidance on financial matters, but you are not a licensed financial advisor.
"""


TITLE_INSTRUCTION = """
        Generate a concise and relevant title for the given conversational message. The title should capture the essence or main topic of the conversation effectively.

        # Steps
        - Analyze the core message and main points of the conversation.
        - Identify key themes, subjects, or ideas discussed.
        - Formulate a brief, descriptive title that encapsulates these themes or topics.

        # Output Format
        - Return only the title as plain text, without any additional formatting or characters.

        # Examples
        - Conversation: "I really enjoyed our meeting today. We covered a lot of important topics related to next quarter's sales strategy and I think we're on the right track for reaching our goals."
        Title: "Quarterly Sales Strategy Discussion"

        - Conversation: "Hey, just wanted to let you know that the project deadline has been moved up. Please make sure to adjust your timeline accordingly."
        Title: "Project Deadline Adjustment Notification"
    """


def generate_response(prompt: str, previous_interaction_id: str | None = None) -> str:
    """
    Generate a response using the Gemini API.

    Args:
        prompt (str): The input prompt for generating a response.

    Returns:
        str: The generated response.
    """
    response = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=prompt,
        system_instruction=RESPONSE_SYSTEM_INSTRUCTION,
        previous_interaction_id=previous_interaction_id,
    )
    return response


def generate_title(context: str) -> str:
    """
    Generate a title for a support conversation based on the provided context.

    Args:
        context (str): The context or content of the support conversation.

    Returns:
        str: The generated title for the support conversation.
    """
    title_prompt = f"Generate a concise and relevant title for the following support conversation context: {context}"
    response = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=title_prompt,
        system_instruction=TITLE_INSTRUCTION,
    )
    return response.output_text


test_prompt = "what plan did I choose?"
if __name__ == "__main__":
    response = generate_response(test_prompt)
    print("Generated Response:")
    print(response.output_text)
    print("---\nID of the response:", response.id)
