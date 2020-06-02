hiragana_chart = \
    "ぁぃぅぇぉ"\
    "ゃゅょゎっ"\
    "ゔゕゖゝゞ"\
    "あいうえお"\
    "かきくけこ"\
    "がぎぐげご"\
    "さしすせそ"\
    "ざじずぜぞ"\
    "たちつてと"\
    "だぢづでど"\
    "なにぬねの"\
    "はひふへほ"\
    "ばびぶべぼ"\
    "ぱぴぷぺぽ"\
    "まみむめも"\
    "やゆよ"\
    "らりるれろ"\
    "わゐゑをん"

katakana_chart = \
    "ァィゥェォ"\
    "ャュョヮッ"\
    "ヴヵヶヽヾ"\
    "アイウエオ"\
    "カキクケコ"\
    "ガギグゲゴ"\
    "サシスセソ"\
    "ザジズゼゾ"\
    "タチツテト"\
    "ダヂヅデド"\
    "ナニヌネノ"\
    "ハヒフヘホ"\
    "バビブベボ"\
    "パピプペポ"\
    "マミムメモ"\
    "ヤユヨ"\
    "ラリルレロ"\
    "ワヰヱヲン"

hiragana = str.maketrans(katakana_chart, hiragana_chart)
katakana = str.maketrans(hiragana_chart, katakana_chart)


def to_hiragana(text):
    """カタカナをひらがなに変換

    Parameters
    ----------
    text : 変換したいテキスト

    Returns
    -------
    hiragana_text : ひらがなに変換したテキスト
    """
    hiragana_text = text.translate(hiragana)

    return hiragana_text


def to_katakana(text):
    """ひらがなをカタカナに変換

    Parameters
    ----------
    text : 変換したいテキスト

    Returns
    -------
    katakana_text : ひらがなに変換したテキスト
    """
    katakana_text = text.translate(katakana)

    return katakana_text
