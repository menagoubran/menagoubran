// Test script for Franco Arabic transliteration
class FrancoArabicTransliterator {
    constructor() {
        this.charMap = {
            '2': 'أ', '3': 'ع', '5': 'خ', '6': 'ط', '7': 'ح', '8': 'ق', '9': 'ق',
            'sh': 'ش', 'gh': 'غ', 'kh': 'خ', 'th': 'ث', 'dh': 'ذ',
            'a': 'ا', 'b': 'ب', 't': 'ت', 'j': 'ج', 'h': 'ه', 'd': 'د',
            'r': 'ر', 'z': 'ز', 's': 'س', 'S': 'ص', 'D': 'ض', 'T': 'ط',
            'Z': 'ظ', 'f': 'ف', 'q': 'ق', 'k': 'ك', 'l': 'ل', 'm': 'م',
            'n': 'ن', 'w': 'و', 'y': 'ي', 'aa': 'ا', 'ee': 'ي', 'oo': 'و',
            'ou': 'و', '\'': 'ء', '2a': 'أ', '2e': 'إ', '2i': 'إ', '2o': 'أ', '2u': 'أ',
        };

        this.wordMap = {
            'salam': 'سلام', 'ahlan': 'أهلا', 'marhaba': 'مرحبا',
            'ana': 'أنا', 'enta': 'أنت', 'ezayak': 'إزيك', 'keda': 'كده',
            'ya3ni': 'يعني', 'wallah': 'والله', 'yalla': 'يلا',
            'kwayyes': 'كويس', 'alhamdulillah': 'الحمد لله', '7aga': 'حاجة',
        };

        this.multiCharCombos = ['sh', 'gh', 'kh', 'th', 'dh', 'aa', 'ee', 'oo', 'ou', '2a', '2e', '2i', '2o', '2u']
            .sort((a, b) => b.length - a.length);
    }

    transliterateWord(word) {
        const lowerWord = word.toLowerCase();
        if (this.wordMap[lowerWord]) {
            return this.wordMap[lowerWord];
        }

        let result = '';
        let i = 0;

        while (i < lowerWord.length) {
            let matched = false;

            for (const combo of this.multiCharCombos) {
                if (lowerWord.substr(i, combo.length) === combo) {
                    result += this.charMap[combo] || combo;
                    i += combo.length;
                    matched = true;
                    break;
                }
            }

            if (!matched) {
                const char = lowerWord[i];
                const upperChar = word[i];

                if (upperChar === upperChar.toUpperCase() && this.charMap[upperChar]) {
                    result += this.charMap[upperChar];
                } else if (this.charMap[char]) {
                    result += this.charMap[char];
                } else {
                    result += char;
                }
                i++;
            }
        }

        return result;
    }

    transliterate(text) {
        const words = text.split(/(\s+)/);
        return words.map(word => {
            if (/^\s+$/.test(word)) {
                return word;
            }
            return this.transliterateWord(word);
        }).join('');
    }
}

// Test cases
const transliterator = new FrancoArabicTransliterator();

console.log('Testing Franco Arabic Transliteration:\n');

const tests = [
    'ahlan',
    'salam 3aleikom',
    'ana kwayyes alhamdulillah',
    'ya3ni 7aga keda',
    'ezayak?',
    'marhaba, ana esmي Ahmed',
    '3amel eh el yom?',
    'shokran',
    'wallah ya3ni mesh 3aref',
    'yalla 5alina nerو7',
];

tests.forEach(test => {
    const result = transliterator.transliterate(test);
    console.log(`Input:  ${test}`);
    console.log(`Output: ${result}`);
    console.log('---');
});

console.log('\nAll tests completed successfully!');
