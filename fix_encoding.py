"""Fix encoding issues in streamlit_app.py - convert all non-ASCII to HTML entities."""

p = 'e:/AURA-ECE/streamlit_app.py'
t = open(p, 'r', encoding='utf-8').read()

# Replace common emojis used as feature icons with clean Unicode symbols (in ASCII entity form)
emoji_replacements = [
    ('\U0001f4dd', '&#9998;'),
    ('\U0001f9e0', '&#9670;'),
    ('\U0001f50e', '&#9906;'),
    ('\U0001f4ca', '&#9632;'),
    ('\U0001f512', '&#9679;'),
    ('\U0001f4da', '&#9733;'),
    ('\U0001f91d', '&#10023;'),
    ('\U0001f3a8', '&#9830;'),
    ('\U0001f4d6', '&#9827;'),
    ('\U0001f3ae', '&#10047;'),
    ('\U0001f917', '&#10084;'),
    ('\U0001f5e3\ufe0f', '&#10148;'),
]

for emoji, replacement in emoji_replacements:
    t = t.replace(emoji, replacement)

t = t.replace('\u2014', '&mdash;')
t = t.replace('\u00b7', '&middot;')
t = t.replace('\u00a9', '&copy;')
t = t.replace('\u2026', '...')
t = t.replace('\u2198', '&#8600;')
t = t.replace('\u2192', '&rarr;')
t = t.replace('\u2019', "'")
t = t.replace('\u2018', "'")
t = t.replace('\u200d', '')

out = t.encode('ascii', errors='xmlcharrefreplace').decode('ascii')
open(p, 'w', encoding='ascii').write(out)
print(f'Done - {len(out)} chars, all ASCII')
non_ascii = [c for c in out if ord(c) > 127]
print(f'Non-ASCII chars remaining: {len(non_ascii)}')
