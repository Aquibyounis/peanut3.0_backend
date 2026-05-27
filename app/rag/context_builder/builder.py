from app.utils.token_counter import count_tokens, truncate_to_tokens

class ContextBuilder:
    def build_context(self, rag_results: list[dict], memory_context: str, stm_context: str, max_tokens: int = 2000) -> str:
        # Budget: 50% RAG, 30% LTM Memory, 20% STM
        rag_budget = int(max_tokens * 0.5)
        memory_budget = int(max_tokens * 0.3)
        stm_budget = int(max_tokens * 0.2)
        
        final_stm = truncate_to_tokens(stm_context, stm_budget)
        final_memory = truncate_to_tokens(memory_context, memory_budget)
        
        # Distribute remaining tokens to RAG
        remaining = max_tokens - count_tokens(final_stm) - count_tokens(final_memory)
        rag_budget = max(rag_budget, remaining)
        
        rag_texts = []
        current_rag_tokens = 0
        
        for res in rag_results:
            text = f"Title: {res.get('title', 'Unknown')}\n{res['text']}"
            tokens = count_tokens(text)
            if current_rag_tokens + tokens > rag_budget:
                break
            rag_texts.append(text)
            current_rag_tokens += tokens
            
        final_rag = "\n\n".join(rag_texts)
        
        return f"{final_rag}\n\nMEMORY:\n{final_memory}\n\nRECENT CONVERSATION:\n{final_stm}"
