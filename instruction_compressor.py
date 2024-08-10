import re
from collections import Counter

# Common abbreviations
ABBREVIATIONS = {
    'function': 'func',
    'variable': 'var',
    'parameter': 'param',
    'return': 'ret',
    'string': 'str',
    'number': 'num',
    'example': 'ex',
    'without': 'w/o',
    'with': 'w/',
    'please': 'pls',
    'thank you': 'ty',
    'instructions': 'instrs',
    'information': 'info',
}

# List of stop words to remove
STOP_WORDS = set(['the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but'])

def compress_instructions(instructions):
    # Convert to lowercase and remove punctuation
    instructions = re.sub(r'[^\w\s]', '', instructions.lower())
    
    # Split into words
    words = instructions.split()
    
    # Remove stop words and apply abbreviations
    compressed_words = []
    for word in words:
        if word not in STOP_WORDS:
            word = ABBREVIATIONS.get(word, word)
            compressed_words.append(word)
    
    # Apply run-length encoding for repeated words
    encoded_words = []
    for word, count in Counter(compressed_words).items():
        if count > 1:
            encoded_words.append(f"{count}x{word}")
        else:
            encoded_words.append(word)
    
    # Join the words back into a string
    return ' '.join(encoded_words)

def decompress_instructions(compressed):
    # Split the compressed string into words
    words = compressed.split()
    
    # Decode run-length encoding and expand abbreviations
    decompressed_words = []
    for word in words:
        if 'x' in word and word[0].isdigit():
            count, word = word.split('x')
            count = int(count)
        else:
            count = 1
        
        # Expand abbreviations
        for full, abbr in ABBREVIATIONS.items():
            if word == abbr:
                word = full
                break
        
        decompressed_words.extend([word] * count)
    
    return ' '.join(decompressed_words)

# Example usage
if __name__ == "__main__":
    original = "Please create a function that takes two parameters and returns their sum. Thank you!"
    compressed = compress_instructions(original)
    decompressed = decompress_instructions(compressed)
    
    print(f"Original: {original}")
    print(f"Compressed: {compressed}")
    print(f"Decompressed: {decompressed}")
    print(f"Compression ratio: {len(compressed) / len(original):.2f}")