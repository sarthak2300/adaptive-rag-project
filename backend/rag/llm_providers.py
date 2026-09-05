"""
Multi-provider LLM factory.
Lets the app switch between OpenAI / Groq / Gemini via one env var
(LLM_PROVIDER) without touching any node code.
"""
from langchain_core.language_models.chat_models import BaseChatModel

from config import settings


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """Return a LangChain chat model based on settings.llm_provider."""
    provider = settings.llm_provider.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env")
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature,
            api_key=settings.openai_api_key,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq

        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set in .env")
        return ChatGroq(
            model=settings.groq_model,
            temperature=temperature,
            api_key=settings.groq_api_key,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is not set in .env")
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=temperature,
            google_api_key=settings.google_api_key,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use openai | groq | gemini."
    )


def get_embeddings():
    """Local/free HuggingFace sentence-transformer embeddings (no API cost)."""
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=settings.embedding_model)
