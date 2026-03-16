from __future__ import annotations

from collections import defaultdict
from enum import Enum
import re

from flashtext import KeywordProcessor
import pymorphy3


class Mode(Enum):
    NORMAL = "normal"
    POETIC = "poetic"


class TextProcessor:
    prefix1 = ["из", "воз", "вз", "воз", "раз", "роз", "низ"]
    prefix2 = ["без", "через", "чрез"]
    voiceless_consonants = ["к", "п", "с", "т", "ф", "х", "ч", "ц", "ш", "щ"]
    hissing_sounds = ["ж", "ш", "щ", "ч"]

    def split_words(self, text: str) -> list[str]:
        words = re.findall(r"\w+", text)
        words = [word for word in re.split(r"\W+", " ".join(words)) if word]
        return words

    def is_prefix(self, prefix: str, word: str) -> bool:
        return word.startswith(prefix)

    def is_ending(self, ending: str, word: str) -> bool:
        return word.endswith(ending)

    def prefix_check(self, words: list[str]):
        prefix1 = self.prefix1
        prefix2 = self.prefix2
        voiceless_consonants = self.voiceless_consonants
        key_words = defaultdict(list)

        for i in range(len(words)):
            for j in range(len(prefix1)):
                if self.is_prefix(prefix1[j], words[i]) is True:
                    word = words[i]
                    if word[len(prefix1[j])] == "с":
                        position = len(prefix1[j]) - 1
                        word = word[:position] + "с" + word[position + 1 :]
                        key_words[word].append(words[i])
            for k in range(len(prefix2)):
                if self.is_prefix(prefix2[k], words[i]) is True:
                    word = words[i]
                    for m in range(len(voiceless_consonants)):
                        if word[len(prefix2[k])] == voiceless_consonants[m]:
                            position = len(prefix2[k]) - 1
                            word = word[:position] + "с" + word[position + 1 :]
                            key_words[word].append(words[i])

        return key_words

    def noun_thirdDeclension_instrumental_check(self, words: list[str]):
        ending1 = "ію"
        key_words = defaultdict(list)
        morph_analyzer = pymorphy3.MorphAnalyzer()

        for i in range(len(words)):
            if self.is_ending(ending1, words[i]):
                word = words[i]
                stem = word[: -len(ending1)]
                word = stem + "ью"

                lemma = ""
                lemmas = set()
                for p in morph_analyzer.parse(word):
                    lemmas.add(p.normal_form)

                for l in lemmas:
                    p = morph_analyzer.parse(l)[0]
                    if morph_analyzer.word_is_known(l):
                        lemma = l
                    else:
                        continue
                parsed_word = morph_analyzer.parse(lemma)[0]

                if "NOUN" in parsed_word.tag and "gent" in parsed_word.tag:
                    continue
                else:
                    key_words[word].append(words[i])

        return key_words

    def plural_adj_neuterOrFem_check(self, words: list[str]):
        ending1 = "ыя"
        ending2 = "ія"
        key_words = defaultdict(list)
        morph_analyzer = pymorphy3.MorphAnalyzer()

        for i in range(len(words)):
            if self.is_ending(ending1, words[i]):
                word = words[i]
                word = word[: -len(ending1)] + "ые"
            elif self.is_ending(ending2, words[i]):
                word = words[i]
                word = word[: -len(ending2)] + "ие"
            else:
                continue

            parsed_word = morph_analyzer.parse(word)[0]

            if parsed_word.tag.POS == "ADJF" and parsed_word.tag.number == "plur":
                lemma = parsed_word.normalized.word
                lemma_parse = morph_analyzer.parse(lemma)[0]

                if (
                    lemma_parse.tag.gender == "masc"
                    and lemma_parse.tag.number == "sing"
                    and lemma_parse.tag.case == "nomn"
                ):
                    key_words[word].append(words[i])

        return key_words

    def noun_secondDeclension_neuter_prepositional_check(self, words: list[str], mode: Mode):
        ending1 = "ьи"
        key_words = defaultdict(list)
        morph_analyzer = pymorphy3.MorphAnalyzer()

        for i in range(len(words)):
            if self.is_ending(ending1, words[i]):
                word = words[i]
                word = word[: -len(ending1)] + "ье"
                if mode == Mode.NORMAL:
                    key_words[word].append(words[i])
                elif mode == Mode.POETIC:
                    parsed_word = morph_analyzer.parse(word)[0]
                    lemma = parsed_word.normal_form
                    if lemma.endswith("ье"):
                        key_words[word].append(words[i])

        return key_words

    def adj_pronoun_adverb_numeral_check(self, words: list[str]):
        ending1 = "аго"
        ending2 = "яго"
        key_words = defaultdict(list)
        morph_analyzer = pymorphy3.MorphAnalyzer()
        hissing_sounds = self.hissing_sounds

        for i in range(len(words)):
            if self.is_ending(ending1, words[i]) or self.is_ending(ending2, words[i]):
                word = words[i]

                if morph_analyzer.word_is_known(word):
                    continue
                else:
                    if self.is_ending(ending1, word):
                        for j in range(len(hissing_sounds)):
                            if word[len(word) - len(ending1) - 1] == hissing_sounds[j]:
                                word = word[: -len(ending1)] + "его"

                                key_words[word].append(words[i])
                                break
                            word = word[: -len(ending1)] + "ого"

                            key_words[word].append(words[i])

                    elif self.is_ending(ending2, word):
                        word = word[: -len(ending2)] + "его"

                        parse = morph_analyzer.parse(word)[0]

                        if (
                            parse.tag.POS in ["ADJF", "NPRO", "PRTF", "NUMR"]
                            and parse.tag.case in ["accs", "gent"]
                            and parse.tag.gender in ["masc", "neut"]
                            and word.endswith(("ый", "ій", "ий"))
                        ):
                            lemma = parse.normal_form
                            parse_lemma = morph_analyzer.parse(lemma)[0]

                            if parse_lemma.normal_form == lemma and parse_lemma.tag.POS == parse.tag.POS:
                                key_words[word].append(words[i])
                            else:
                                continue
                        else:
                            continue

        return key_words

    def replace_letters(self, text: str) -> str:
        old_letters = {
            "ѣ": "е",
            "i": "и",
            "ѳ": "ф",
            "ѵ": "и",
            "ѕ": "з",
            "ѯ": "кс",
            "ѱ": "пс",
            "і": "и",
        }

        regex = re.compile("|".join(map(re.escape, old_letters.keys())))
        return regex.sub(lambda match: old_letters[match.group(0)], text)

    def check_and_remove_hard_sign(self, words: list[str]):
        morph = pymorphy3.MorphAnalyzer()
        key_words = defaultdict(list)

        for word in words:
            parsed_word = morph.parse(word)[0]

            if parsed_word.is_known is False and (word.endswith("ъ") or word.endswith("ь")):
                new_word = word[:-1]
                key_words[new_word].append(word)

        return key_words


def translate_text(text: str, mode: Mode = Mode.NORMAL) -> str:
    keyword_processor = KeywordProcessor(case_sensitive=True)
    keyword_processor2 = KeywordProcessor(case_sensitive=True)
    text_processor = TextProcessor()

    words = text_processor.split_words(text)

    key_words = text_processor.prefix_check(words)
    keyword_processor.add_keywords_from_dict(key_words)

    key_words = text_processor.noun_thirdDeclension_instrumental_check(words)
    keyword_processor.add_keywords_from_dict(key_words)

    key_words = text_processor.plural_adj_neuterOrFem_check(words)
    keyword_processor.add_keywords_from_dict(key_words)

    key_words = text_processor.noun_secondDeclension_neuter_prepositional_check(words, mode)
    keyword_processor.add_keywords_from_dict(key_words)

    key_words = text_processor.adj_pronoun_adverb_numeral_check(words)
    keyword_processor.add_keywords_from_dict(key_words)

    new_text = keyword_processor.replace_keywords(text)
    new_text = text_processor.replace_letters(new_text)

    words2 = text_processor.split_words(new_text)
    key_words2 = text_processor.check_and_remove_hard_sign(words2)
    keyword_processor2.add_keywords_from_dict(key_words2)

    return keyword_processor2.replace_keywords(new_text)
