// Franco Arabic to Arabic Transliteration Engine
class FrancoArabicTransliterator {
    constructor() {
        // Mapping of Franco Arabic characters to Arabic
        this.charMap = {
            // Numbers representing specific Arabic letters
            '2': 'أ',  // hamza
            '3': 'ع',  // ain
            '5': 'خ',  // kha
            '6': 'ط',  // ta (emphatic)
            '7': 'ح',  // ha
            '8': 'ق',  // qaf (alternative)
            '9': 'ق',  // qaf

            // Special combinations (must be checked first)
            'sh': 'ش',
            'gh': 'غ',
            'kh': 'خ',
            'th': 'ث',
            'dh': 'ذ',

            // Basic letters
            'a': 'ا',
            'b': 'ب',
            't': 'ت',
            'j': 'ج',
            'h': 'ه',
            'd': 'د',
            'r': 'ر',
            'z': 'ز',
            's': 'س',
            'S': 'ص',  // sad (emphatic S)
            'D': 'ض',  // dad (emphatic D)
            'T': 'ط',  // ta (emphatic T)
            'Z': 'ظ',  // za (emphatic Z)
            'f': 'ف',
            'q': 'ق',
            'k': 'ك',
            'l': 'ل',
            'm': 'م',
            'n': 'ن',
            'w': 'و',
            'y': 'ي',

            // Vowels and diacritics (optional representation)
            'aa': 'ا',
            'ee': 'ي',
            'oo': 'و',
            'ou': 'و',
            'e': 'ي',
            'i': 'ي',
            'o': 'و',
            'u': 'و',

            // Hamza variations
            '\'': 'ء',
            '2a': 'أ',
            '2e': 'إ',
            '2i': 'إ',
            '2o': 'أ',
            '2u': 'أ',
        };

        // Common word mappings for better accuracy
        this.wordMap = {
            // Greetings
            'salam': 'سلام',
            'salaam': 'سلام',
            'sabah': 'صباح',
            'masa': 'مساء',
            'masa2': 'مساء',
            'ahlan': 'أهلا',
            'marhaba': 'مرحبا',

            // Common words
            'ana': 'أنا',
            'enta': 'أنت',
            'enti': 'أنت',
            'howa': 'هو',
            'heya': 'هي',
            '3amel': 'عامل',
            '3amla': 'عاملة',
            'ezay': 'إزاي',
            'ezayak': 'إزيك',
            'ezayek': 'إزيك',
            'keda': 'كده',
            'kda': 'كدا',
            'ya3ni': 'يعني',
            'wallah': 'والله',
            'wallahi': 'والله',
            'inshallah': 'إن شاء الله',
            'alhamdulillah': 'الحمد لله',
            'subhanallah': 'سبحان الله',
            'bismillah': 'بسم الله',
            'yalla': 'يلا',
            'yala': 'يلا',
            'tab': 'طب',
            'tayeb': 'طيب',
            'tamam': 'تمام',
            'kwayyes': 'كويس',
            'kwayes': 'كويس',
            'mesh': 'مش',
            'msh': 'مش',
            '3ala': 'على',
            '3la': 'على',
            'el': 'ال',
            'al': 'ال',
            'fel': 'في ال',
            'fil': 'في ال',
            'fi': 'في',
            'mn': 'من',
            'min': 'من',
            'masr': 'مصر',
            'misr': 'مصر',
            '7aga': 'حاجة',
            '7etta': 'حتى',
            'ba2a': 'بقى',
            'ba2': 'بقى',
            'kol': 'كل',
            'koll': 'كل',
            'ya': 'يا',
            'eh': 'إيه',
            'eeh': 'إيه',
            'ay': 'أي',
            'aywa': 'أيوه',
            'la2': 'لأ',
            'la': 'لا',
            'naam': 'نعم',
            'na3am': 'نعم',
            'shokran': 'شكرا',
            'shukran': 'شكرا',
            '3afwan': 'عفوا',
            'wala': 'ولا',
            'wla': 'ولا',
            'leh': 'ليه',
            'leeh': 'ليه',
            'fein': 'فين',
            'fen': 'فين',
            'emta': 'إمتى',
            'imta': 'إمتى',
            'meen': 'مين',
            'mein': 'مين',
            'izzay': 'إزاي',
            '3shan': 'عشان',
            '3ashan': 'عشان',
            'bas': 'بس',
            'bs': 'بس',
            'kaman': 'كمان',
            'bardu': 'برضه',
            'bardo': 'برضه',
            'akeed': 'أكيد',
            'akid': 'أكيد',
            '3ayz': 'عايز',
            '3ayza': 'عايزة',
            '3awez': 'عاوز',
            'mafish': 'مافيش',
            'mafesh': 'مافيش',
            'momken': 'ممكن',
            'mumkin': 'ممكن',
            'khalas': 'خلاص',
            'khlas': 'خلاص',
            'ma3lesh': 'معلش',
            'ma3leesh': 'معليش',
            'assef': 'آسف',
            'asf': 'آسف',
            'mabsoot': 'مبسوط',
            'mabsot': 'مبسوط',
            'za3lan': 'زعلان',
            'zay': 'زي',
            'gameel': 'جميل',
            'gamil': 'جميل',
            '7elw': 'حلو',
            '7elwa': 'حلوة',
            'kebeer': 'كبير',
            'kbeer': 'كبير',
            'soghayar': 'صغير',
            'sgheer': 'صغير',
            'gedeed': 'جديد',
            'gdeed': 'جديد',
            'adeem': 'قديم',
            '2deem': 'قديم',
            'sa3b': 'صعب',
            'sahl': 'سهل',
            'katheer': 'كثير',
            'kteer': 'كتير',
            'shwaya': 'شوية',
            'shwya': 'شوية',
            '7abeebi': 'حبيبي',
            '7abibi': 'حبيبي',
            '7abibti': 'حبيبتي',
            'ya3ni': 'يعني',
            'yabni': 'يعني',
            '3aref': 'عارف',
            '3arfa': 'عارفة',
            '3arif': 'عارف',
            'esm': 'اسم',
            'esmi': 'اسمي',
            'esmak': 'اسمك',
            'esmek': 'اسمك',
            'yom': 'يوم',
            'youm': 'يوم',
            'nhar': 'نهار',
            'leil': 'ليل',
            'leila': 'ليلة',
            'saba7': 'صباح',
            '3aleikom': 'عليكم',
            '3alekom': 'عليكم',
            '3alik': 'عليك',
            '3aleek': 'عليك',
            '5alina': 'خلينا',
            'khalina': 'خلينا',
            'nero7': 'نروح',
            'neroo7': 'نروح',
            'negي': 'نجي',
            'negi': 'نجي',
        };

        // Multichar combinations (ordered by length, longest first)
        this.multiCharCombos = [
            'sh', 'gh', 'kh', 'th', 'dh',
            'aa', 'ee', 'oo', 'ou',
            '2a', '2e', '2i', '2o', '2u'
        ].sort((a, b) => b.length - a.length);
    }

    transliterateWord(word) {
        const lowerWord = word.toLowerCase();

        // Check if the whole word is in the word map
        if (this.wordMap[lowerWord]) {
            return this.wordMap[lowerWord];
        }

        // Character-by-character transliteration
        let result = '';
        let i = 0;

        while (i < lowerWord.length) {
            let matched = false;

            // Try to match multi-character combinations first
            for (const combo of this.multiCharCombos) {
                if (lowerWord.substr(i, combo.length) === combo) {
                    result += this.charMap[combo] || combo;
                    i += combo.length;
                    matched = true;
                    break;
                }
            }

            // If no multi-char match, try single character
            if (!matched) {
                const char = lowerWord[i];
                const upperChar = word[i]; // Preserve original case for capital letters

                // Check if it's a capital letter (for emphatic sounds)
                if (upperChar === upperChar.toUpperCase() && this.charMap[upperChar]) {
                    result += this.charMap[upperChar];
                } else if (this.charMap[char]) {
                    result += this.charMap[char];
                } else {
                    // Keep character as-is if no mapping (e.g., spaces, punctuation)
                    result += char;
                }
                i++;
            }
        }

        return result;
    }

    transliterate(text) {
        // Split by spaces and process each word
        const words = text.split(/(\s+)/); // Keep whitespace
        return words.map(word => {
            // If it's whitespace, keep it
            if (/^\s+$/.test(word)) {
                return word;
            }
            return this.transliterateWord(word);
        }).join('');
    }
}

// Create global instance
const transliterator = new FrancoArabicTransliterator();

// Function to handle transliteration
function handleTransliteration() {
    const input = document.getElementById('francoInput').value;
    const output = document.getElementById('arabicOutput');

    if (input.trim() === '') {
        output.textContent = '';
        return;
    }

    const result = transliterator.transliterate(input);
    output.textContent = result;
}

// Function to copy result to clipboard
function copyToClipboard() {
    const output = document.getElementById('arabicOutput');
    const text = output.textContent;

    if (text) {
        navigator.clipboard.writeText(text).then(() => {
            const copyBtn = document.getElementById('copyBtn');
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            setTimeout(() => {
                copyBtn.textContent = originalText;
            }, 2000);
        });
    }
}

// Function to swap input/output
function swapText() {
    const input = document.getElementById('francoInput');
    const output = document.getElementById('arabicOutput');

    const temp = input.value;
    input.value = output.textContent;
    output.textContent = temp;

    handleTransliteration();
}

// Function to clear all
function clearAll() {
    document.getElementById('francoInput').value = '';
    document.getElementById('arabicOutput').textContent = '';
}

// Add examples functionality
function loadExample(exampleText) {
    document.getElementById('francoInput').value = exampleText;
    handleTransliteration();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('francoInput');

    // Handle input event for real-time transliteration
    input.addEventListener('input', handleTransliteration);

    // Add example buttons
    const examples = [
        { label: 'Greeting', text: 'ahlan, ezayak? ana kwayyes alhamdulillah' },
        { label: 'Common Phrases', text: 'ya3ni ana 3ayez a2ول 7aga' },
        { label: 'Mixed Numbers', text: 'salam 3aleikom, 3amel eh el yom?' },
        { label: 'Egyptian Dialect', text: 'enta mesh 3aref 7aga ya3ni?' }
    ];

    const examplesContainer = document.getElementById('examples');
    examples.forEach(example => {
        const btn = document.createElement('button');
        btn.className = 'example-btn';
        btn.textContent = example.label;
        btn.onclick = () => loadExample(example.text);
        examplesContainer.appendChild(btn);
    });
});
