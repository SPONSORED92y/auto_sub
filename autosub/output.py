"""Non-destructive subtitle output typography."""
import re
import unicodedata


def format_punctuation(text: str, mode: str = "keep") -> str:
    if mode not in {"keep", "remove", "spaces"}:
        raise ValueError("不支援的輸出標點方式。")
    if mode == "keep":
        return text
    protected = set()
    # Keep URL syntax intact, excluding trailing sentence punctuation.
    for match in re.finditer(r"(?:https?://|www\.)[^\s<>()「」【】，。！？；：、\"“”]+", text):
        url = match.group().rstrip(".,!?;:，。！？；：")
        protected.update(range(match.start(), match.start()+len(url)))
    result = []
    for i, char in enumerate(text):
        before = text[i-1] if i else ""
        after = text[i+1] if i+1 < len(text) else ""
        ascii_word = (bool(before and after) and before.isascii() and before.isalnum()
                      and after.isascii() and after.isalnum())
        internal = (char in ".'’-_/@" and ascii_word
                    or char in ".,：:" and before.isdigit() and after.isdigit()
                    or char in "%‰‱" and before.isdigit()
                    or char == "#" and before.isascii() and before.isalnum()
                    or char == "-" and after.isdigit() and not before.isalnum())
        if i not in protected and not internal and unicodedata.category(char).startswith("P"):
            result.append(" " if mode == "spaces" else "")
        else:
            result.append(char)
    # Collapse horizontal spaces, keep nonempty manual line breaks.
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in "".join(result).splitlines()]
    return "\n".join(line for line in lines if line)
