import logging

from google import genai
from google.genai import types
from google.genai.types import (
    Content,
    Part,
)

from .models import (
    pprint,
)


def llm_query(
    articles: str,
    system_prompt_path: str,
    model: str,
    api_key: str,
    research_interests_path: str = None,
    tools: list = [],
):
    """
    Query LLM to process articles based on user research interests.

    Args:
        articles (str): The articles to process (JSON string or list).
        system_prompt_path (str): The path to the system prompt file.
        model (str): The model to use for screening. One of 'gemini-1.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'.
        api_key (str): The Google API key for authentication.
        research_interests_path (str): The path to a text file containing the user's research interests. It will be inserted into the system prompt.
        tools (list): List of tools for the LLM to use.

    Returns:
        str: The LLM response text.
    """

    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not found. "
            "Did you remember to `nextflow secrets set GOOGLE_API_KEY '<YOUR-KEY'`?"
        )

    client = genai.Client(api_key=api_key)

    logging.info("Began reading system prompt...")
    with open(system_prompt_path, "r") as f:
        system_instruction = f.read().strip()
    logging.info("Done reading system prompt.")

    if research_interests_path:
        logging.info("Began reading research interests...")
        with open(research_interests_path, "r") as F:
            research_interests = F.read().strip()
        logging.info("Done reading research interests.")

        system_instruction = system_instruction.format(
            research_interests=research_interests
        )
    logging.debug(f"System prompt: {system_instruction}")

    prompt = f"Here are the articles: {pprint(articles)}"
    logging.debug(f"User prompt: {prompt}")

    context = [
        Content(role="user", parts=[Part(text=system_instruction)]),
        Content(
            role="model",
            parts=[
                Part(
                    text="Understood. I will analyze the articles based on the provided research interests and use the available tools if necessary. Please provide the articles."
                )
            ],
        ),
        Content(role="user", parts=[Part(text=prompt)]),
    ]

    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(include_thoughts=False),
        tools=tools,
    )

    response = client.models.generate_content(
        model=model,
        contents=context,
        config=config,
    )

    response_text = response.text.strip()
    logging.debug(f"✅ LLM Response: {response_text}")
    return response_text
