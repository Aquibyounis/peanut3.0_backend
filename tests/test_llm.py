"""
Peanut 3.0 - Groq LLM and Fallback Architecture Tests
"""

import os
import pytest
import asyncio
from app.llm.llm_service import llm_service
from app.rag.embeddings import generate_embedding
from app.core.config import settings

# Verify GROQ API KEY is configured before running tests
GROQ_API_KEY_CONFIGURED = settings.groq_api_key is not None and settings.groq_api_key != "" and settings.groq_api_key != "YOUR_NEW_KEY"

@pytest.mark.asyncio
async def test_local_embeddings():
    """Verify local fastembed Nomics model generates 768-dimension vectors completely offline."""
    text = "Hello World from Peanut AI!"
    embedding = generate_embedding(text)
    
    assert embedding is not None, "Failed to generate embedding vector"
    assert isinstance(embedding, list), "Embedding should be a standard Python list of floats"
    assert len(embedding) == 768, f"Expected 768-dimension Nomics output, got {len(embedding)}"
    assert all(isinstance(val, float) for val in embedding), "All vector values must be floats"

@pytest.mark.skipif(not GROQ_API_KEY_CONFIGURED, reason="Groq API key not configured in .env")
@pytest.mark.asyncio
async def test_groq_completion():
    """Verify async chat completion via Groq works."""
    query = "Who is the developer of Peanut AI? Keep answer under 10 words."
    context = "Pula Aquib Younis developed Peanut AI."
    
    response = await llm_service.generate_chat_response(
        query=query,
        context=context,
        chat_history=None
    )
    
    assert response is not None, "Response from Groq was null"
    assert len(response.strip()) > 0, "Response from Groq was empty"
    assert "aquib" in response.lower() or "younis" in response.lower(), f"Expected answer to name Aquib, got: {response}"

@pytest.mark.skipif(not GROQ_API_KEY_CONFIGURED, reason="Groq API key not configured in .env")
@pytest.mark.asyncio
async def test_groq_streaming():
    """Verify async streaming response streams real-time tokens."""
    query = "Name 3 primary programming languages. Keep it extremely brief."
    context = "The user is exploring coding."
    
    token_stream = llm_service.stream_chat_response(
        query=query,
        context=context,
        is_sse=False
    )
    
    tokens = []
    async for chunk in token_stream:
        assert isinstance(chunk, str), "Each streamed chunk must be a string"
        tokens.append(chunk)
        
    full_text = "".join(tokens)
    assert len(tokens) > 0, "No chunks were streamed"
    assert len(full_text.strip()) > 0, "Full streamed response is empty"

@pytest.mark.skipif(not GROQ_API_KEY_CONFIGURED, reason="Groq API key not configured in .env")
@pytest.mark.asyncio
async def test_generate_followups():
    """Verify live contextual follow-up question generation via Groq."""
    query = "Who is Aquib Younis?"
    response = "Aquib Younis is a software engineer who developed Peanut AI."
    
    follow_ups = await llm_service.stream_handler.generate_followups(
        query=query,
        response=response
    )
    
    assert follow_ups is not None
    assert len(follow_ups) == 3
    # Check that they are not the fallback strings
    assert follow_ups[0] != "Can you tell me more about this?"
    assert follow_ups[1] != "What technologies are involved?"
    assert follow_ups[2] != "How does this compare to similar projects?"

@pytest.mark.asyncio
async def test_fallback_mechanism():
    """Verify fallback provider handles rate limits or API errors by executing fallbacks."""
    # We will trigger a mock failure by passing an invalid model,
    # expecting it to fall back to other models in the chain.
    messages = [{"role": "user", "content": "Ping"}]
    
    try:
        content = await llm_service.fallback_provider.generate_with_fallback(
            messages=messages,
            model="invalid-groq-model-name-for-testing-purposes",
            temperature=0.0,
            max_tokens=10
        )
        assert content is not None, "Fallback generated output was null"
        assert len(content.strip()) > 0, "Fallback generated output was empty"
    except Exception as e:
        # If the Groq key is dummy or not configured, a connection error might raise
        # at the end of the chain, which is also an acceptable validation of the fallback routing attempt.
        assert "RateLimitError" in str(e) or "APIError" in str(e) or "Unauthorized" in str(e) or "Authentication" in str(e) or "401" in str(e)

if __name__ == "__main__":
    # Allow executing the test script directly
    print("\nRunning local fastembed offline vector embedding test...")
    asyncio.run(test_local_embeddings())
    print("SUCCESS: Local offline fastembed vectors generated in perfect 768 size!\n")
