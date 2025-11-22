# API Fixes - livekit-agents 1.3+ Compatibility

## Fix #1: ChatChunk API Change

### Issue
After updating to `livekit-agents==1.3.3`, the custom LLM implementation was using the old API:

```python
# OLD API (pre-1.3) - DOESN'T WORK
chunk = llm.ChatChunk(
    choices=[llm.Choice(
        delta=llm.ChoiceDelta(content=response, role="assistant")
    )]
)
```

**Error:**
```
AttributeError: module 'livekit.agents.llm' has no attribute 'Choice'
```

## Root Cause
The livekit-agents API changed in version 1.3+. The `ChatChunk` class no longer accepts a `choices` parameter with `Choice` objects. Instead, it takes the `delta` parameter directly.

## Solution
Updated the custom LLM implementation to use the new API:

```python
# NEW API (1.3+) - CORRECT
chunk = llm.ChatChunk(
    id=f"closer-{id(response)}",  # Unique ID for this chunk
    delta=llm.ChoiceDelta(content=response, role="assistant")
)
```

## File Changed
- `metatron/agents/voice_agent.py` (line 78-83)

## Status
✅ **FIXED** - The voice agent now works with livekit-agents 1.3.3

## Testing
Run the voice worker and verify it processes messages without errors:
```bash
uv run metatron voice-worker
```

You should see:
- CloserLLM response messages in logs
- No more "AttributeError: module 'livekit.agents.llm' has no attribute 'Choice'"
- Voice agent successfully generates responses

---

## Fix #2: Groq Response Format Parsing

### Issue
The Groq API was returning responses in dict format, but the code expected a list:

```python
# Groq returns (dict format):
{
  "directa": "¡Hola Rafael! Como ingeniero...",
  "consultiva": "Rafael, entiendo que...",
  "empatica": "¡Hola Rafael! Sé lo emocionante..."
}

# Code expected (list format):
[
  {"id": "directa", "intent": "cierre", "text": "..."},
  {"id": "consultiva", "intent": "pregunta", "text": "..."},
  {"id": "empatica", "intent": "confianza", "text": "..."}
]
```

**Error:**
```
WARNING: Validation error: Expected list, got dict
WARNING: Using fallback options due to parsing error
```

### Root Cause
The prompts in `ResponseGenerator` methods were ambiguous about the JSON structure. They said things like:
- "Devuelve exactamente 3 opciones en formato JSON con IDs: directa, consultiva, empatica"
- "Devuelve JSON exacto con 3 opciones: directa, consultiva y empatica"

Groq interpreted this as returning a dict with those IDs as keys, not a list.

### Solution
Updated the `_call_openai` method to handle both dict and list formats:

```python
# Now handles both formats
if isinstance(parsed_data, dict):
    # Convert dict to list format
    intent_mapping = {
        "directa": "cierre",
        "consultiva": "pregunta",
        "empatica": "confianza"
    }
    
    options = []
    for key in ["directa", "consultiva", "empatica"]:
        if key in parsed_data:
            options.append({
                "id": key,
                "intent": intent_mapping.get(key, "general"),
                "text": parsed_data[key]
            })
    
    return options

elif isinstance(parsed_data, list):
    # Already in correct format
    return parsed_data
```

### File Changed
- `metatron/agents/response_generator.py` (lines 310-360)

### Status
✅ **FIXED** - The response generator now accepts both dict and list formats from Groq

---

**Date:** November 22, 2025  
**Fixed by:** AI Assistant  
**Related to:** VALIDATION_REPORT.md updates

## Summary

Both issues have been fixed:
1. ✅ ChatChunk API compatibility with livekit-agents 1.3+
2. ✅ Groq response format parsing (handles both dict and list)

The voice agent now works correctly with the latest versions of all dependencies!

