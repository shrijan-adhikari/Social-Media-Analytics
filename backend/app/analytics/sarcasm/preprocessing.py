import re

def preprocess_sarcasm_text(text: str) -> str:
    """
    Preprocess text specifically for mrm8488/t5-base-finetuned-sarcasm-twitter.
    
    The model card expects:
    - users replaced with @USER
    - urls replaced with URL
    """
    if not text:
        return ""
        
    # Replace mentions with @USER
    text = re.sub(r"@\w+", "@USER", text)
    
    # Replace URLs with URL
    text = re.sub(r"http\S+", "URL", text)
    
    # Clean whitespace
    text = " ".join(text.split())
    
    return text
