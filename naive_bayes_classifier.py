import doctest
import math
import MeCab
import numpy as np
import re

mecab = MeCab.Tagger()
mecab_regex = re.compile(r'(?P<morpheme>.*?)\t(.*)')

good_file = 'good'
poor_file = 'poor'


def document2morphemes(document):
    """MeCabで文書を解析し、形態素リストを返す

    Parameters
    ----------
    document : 解析する文書

    Returns
    -------
    morphemes : 形態素リスト

    Examples
    --------
    >>> document2morphemes("日本語が難しい")
    ['日本語', 'が', '難しい']
    """
    parsed_list = mecab.parse(document).split("\n")

    morphemes = [mecab_regex.match(parsed_str).group('morpheme')
                 for parsed_str in parsed_list
                 if parsed_str not in ['EOS', '']]

    return morphemes


class Category:
    def __init__(self, name, documents):
        """カテゴリ

        Parameters
        ----------
        name : カテゴリ名
        documents : カテゴリに持たせる文書リスト
        """
        self.name = name
        self.update_morphemes(documents)

        self.datasets = np.array_split(documents, 10)
        self.accurate_count = 0
        self.test_count = 0

    def update_morphemes(self, documents):
        """文書リストを解析し、カテゴリの形態素リストをアップデートし、形態素の数と頻度を再計算する

        Parameters
        ----------
        documents : 文書リスト
        """
        self.morphemes = document2morphemes('\n'.join(documents))
        self.count = len(self.morphemes)
        self.dict = {m: self.morphemes.count(m)
                     for m in set(self.morphemes)}

    def fold(self, test_index):
        """カテゴリの標本群をテスト事例と訓練事例に分割する

        Parameters
        ----------
        test_index : 分割する位置を表すインデックス
        """
        self.train = np.concatenate(np.delete(self.datasets, test_index, 0))
        self.test = self.datasets[test_index]
        self.update_morphemes(self.train)


class Classifier:
    def __init__(self, categories, k=10):
        """ベイズ分類器

        Parameters
        ----------
        categories : カテゴリオブジェクトのリスト
        k : K-分割交差検証においてKの値（デフォルト: 10）
        """
        self.categories = categories
        self.k = k

        self.update_classifier()

    def update_classifier(self):
        """分類器の形態素総数と各カテゴリの確率を再計算する"""
        self.morphemes_count = sum([category.count
                                    for category in self.categories])

        for category in self.categories:
            category.prior_prob = category.count / self.morphemes_count

    def calculate_bayes_prob(self, morphemes, category):
        """ベイズ確率を計算し、対数を返す

        Parameters
        ----------
        morphemes : 分類される形態素リスト
        category: カテゴリオブジェクト

        Returns
        -------
        log_bayes_prob : ベイズ確率の対数
        """
        counts = [category.prior_prob]
        for morpheme in morphemes:
            if morpheme in category.dict:
                counts.append(category.dict[morpheme] / category.count)
            else:
                counts.append(1 / self.morphemes_count)

        log_bayes_prob = sum([math.log(count) for count in counts])
        return log_bayes_prob

    def classify(self, document):
        """分類器で分類されたカテゴリの名前を返す

        Parameters
        ----------
        document : 分類される文書

        Returns
        -------
        classification : 分類されたカテゴリの名前
        """
        max_log_bayes_prob = -math.inf
        classification = ''

        morphemes = document2morphemes(document)

        for category in self.categories:
            log_bayes_prob = self.calculate_bayes_prob(morphemes, category)

            if log_bayes_prob > max_log_bayes_prob:
                max_log_bayes_prob = log_bayes_prob
                classification = category.name

        return classification

    def verify(self, test_index):
        """分割交差検証を一回する

        Parameters
        ----------
        test_index : 分割する位置を表すインデックス
        """
        for category in self.categories:
            category.fold(test_index)

        self.update_classifier()

        for category in self.categories:
            category.result = [self.classify(test)
                               for test in category.test]

            category.accurate_count += category.result.count(category.name)
            category.test_count += len(category.test)

    def k_fold(self):
        """分類器の精度をK-分割交差検証で検証する"""
        for i in range(self.k):
            print("{}/{}".format(i, self.k))
            self.verify(i)

        print("{}/{}".format(self.k, self.k))

        for category in self.categories:
            accurate_count = category.accurate_count
            test_count = category.test_count
            accuracy = round(accurate_count / test_count * 100, 2)
            print("{}: {}/{} ({}%)".format(category.name,
                                           accurate_count,
                                           test_count,
                                           accuracy))


with open(good_file, 'r') as file:
    good = Category("good", file.read().splitlines())

with open(poor_file, 'r') as file:
    poor = Category("poor", file.read().splitlines())

default_classifier = Classifier([good, poor])

if __name__ == "__main__":
    num_failure, num_test = doctest.testmod()
    if num_failure > 0:
        exit(1)

    default_classifier.k_fold()
