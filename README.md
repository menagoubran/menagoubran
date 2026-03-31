# Franco Arabic to Arabic Transliterator

A web-based application that converts Franco Arabic (Arabizi) - phonetic Arabic written using English letters and numbers - into actual Arabic script.

## Features

- **Real-time Transliteration**: Converts text as you type
- **Smart Word Recognition**: Recognizes common Egyptian and Levantine Arabic words
- **Character Mapping**: Supports numbers (2, 3, 5, 6, 7, 9) for special Arabic sounds
- **Multi-character Combinations**: Handles sh, gh, kh, th, dh digraphs
- **Emphatic Consonants**: Capital letters (S, D, T, Z) for emphatic sounds
- **User-friendly Interface**: Clean, modern design with examples and guides
- **Copy to Clipboard**: Easy copying of transliterated text

## Usage

Simply open `transliteration.html` in any modern web browser.

### Character Mapping

| Franco | Arabic | Description |
|--------|--------|-------------|
| 2      | أ      | Hamza |
| 3      | ع      | Ain |
| 5      | خ      | Kha |
| 6      | ط      | Ta (emphatic) |
| 7      | ح      | Ha |
| 9      | ق      | Qaf |
| sh     | ش      | Sheen |
| gh     | غ      | Ghain |
| kh     | خ      | Kha |
| th     | ث      | Thaa |
| S      | ص      | Sad (emphatic) |
| D      | ض      | Dad (emphatic) |
| T      | ط      | Ta (emphatic) |
| Z      | ظ      | Zaa (emphatic) |

### Examples

- `ahlan, ezayak?` → `أهلا، إزيك؟`
- `ana kwayyes alhamdulillah` → `أنا كويس الحمد لله`
- `salam 3aleikom` → `سلام عليكم`
- `ya3ni 7aga keda` → `يعني حاجة كدا`

### Supported Words

The app includes a dictionary of common Egyptian and Levantine Arabic words for accurate transliteration:
- Greetings: salam, ahlan, marhaba
- Common phrases: ya3ni, wallah, inshallah, yalla, tayeb
- Question words: eh, fein, emta, meen, leh, izzay
- And many more...

## Technology

- Pure vanilla JavaScript (no dependencies)
- HTML5 and CSS3
- Responsive design for mobile and desktop

## Files

- `transliteration.html` - Main application page
- `transliteration.js` - Transliteration engine and logic
- `transliteration.css` - Styling and layout

## How It Works

1. **Word-level Matching**: First checks if the entire word exists in the common words dictionary
2. **Character-level Transliteration**: If not found, performs character-by-character conversion
3. **Multi-character Detection**: Prioritizes longer character combinations (e.g., 'sh' before 's')
4. **Context Preservation**: Maintains spacing and punctuation

## Limitations

- Works best with Egyptian and Levantine dialects
- May require manual adjustment for less common words
- Assumes standard Franco Arabic conventions

## Future Enhancements

- Support for more dialects (Gulf, Moroccan, etc.)
- Reverse transliteration (Arabic to Franco)
- User-customizable mappings
- Export options (PDF, image)
- Mobile app version

## License

Open source - feel free to use and modify!
