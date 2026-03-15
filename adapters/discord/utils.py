"""
Discord utility functions.

Helper functions for Discord-specific operations like message chunking.
"""


def chunk_message(text: str, max_length: int = 2000) -> list[str]:
    """
    Split a message into chunks that fit within Discord's character limit.

    Args:
        text: The message to split
        max_length: Maximum characters per chunk (default: 2000 for Discord)

    Returns:
        List of message chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by lines first to preserve formatting
    lines = text.split("\n")

    for line in lines:
        # If a single line is longer than max_length, split it by words
        if len(line) > max_length:
            words = line.split(" ")
            for word in words:
                # If a single word is longer than max_length, force character split
                while len(word) > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.rstrip())
                        current_chunk = ""
                    chunks.append(word[:max_length])
                    word = word[max_length:]

                # Add the remaining word
                if len(current_chunk) + len(word) + 1 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.rstrip())
                    current_chunk = word + " "
                else:
                    current_chunk += word + " "
        else:
            # Check if adding this line would exceed the limit
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.rstrip())
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.rstrip())

    return chunks
