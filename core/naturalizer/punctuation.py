import re


def cleanup_spacing(text: str) -> str:
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\s+([,\.!?;:])", r"\1", text)
    return text.strip()
