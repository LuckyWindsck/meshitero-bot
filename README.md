# 飯テロボット

「#飯テロ」のツイートを評価する Twitter bot

- `README.md`
  - このファイル
- `Pipfile`
  - Pipenv 仮想環境がプロジェクトの依存関係を管理するために使用する専用のファイルです。
- `Pipfile.lock`
  - 上と同じ
- `comments`
  - ボットが引用RTする場合のコメントリスト
- `foods`
  - 料理名リスト
- `searched_tweet`
  - どのツイートまで検索したかを記録用
- `query`
  - クエリリスト
- `good`
  - goodの学習データ
- `poor`
  - poorの学習データ
- `.env`
  - APIを使うための各種key
- `naive_bayes_classifier.py`
  - 単純ベイズ分類器
- `kana_translate.py`
  - ひらがなとカタカナの変換
- `twitter_client.py`
  - Twitterクライアント
- `meshitero_bot.py`
  - 飯テロボット(main)

## コードの流れ
1. `.env` から認証するための環境変数を読み込む
```
    load_dotenv()

    # 認証するための環境変数
    env_keys = ["CONSUMER_KEY", "CONSUMER_SECRET",
                "ACCESS_TOKEN_KEY", "ACCESS_TOKEN_SECRET"]

    credentials = {key: os.getenv(key) for key in env_keys}
```
2. 単純ベイズ分類器を初期化する
```
    classifier = naive_bayes.default_classifier
```
3. ツイッターAPIに繋げて、ボットスタート
```
    MeshiteroBot(classifier)\         # ボットを初期化する
        .setCredentials(credentials)\ # 認証するためのキーを与える
        .connect()\                   # APIに繋がる
        .run()                        # 起動する
```
4. 繰り返して働かせる
```
    while True:
        # 起動してから30分経ったを判定
        # そうであればボット終了
        # そうでなければ働かせる
        self.task()
        # もしツイート制限に達したらボット終了
        # まだ大丈夫だったら、少し休ませてから働かせる
```
5. 飯テロツイートを検索して、取得かどうかを確認する
```
    # 条件を満たすツイートのみ検索する
    # 1. query の一つでも含まれること
    # 2. 「#飯テロ」タグが付いてること
    # 3. 画像が付いてること
    # 4. RT でないこと
    # 5. 昨日からのツイートのみ
    # 6. 日本語であること
    # 7. 「最新ツイート」であること
    # 8. tweet_id 以後のツイートのみ（重複しないように）

    tweets = self.search_meshitero()

    if not tweets:
          print("引用すべきツイートがなさそうですね。")
          self.rest_time = self.max_request_frequency
          return self
```
6. 重複に検索しないように、どのツイートまで検索したかをファイルに書き込む
```
    with open(self.file["searched_tweet"], "w") as file:
        self.searched_id = str(tweets[0].id)
        file.write(self.searched_id)
```
7. 引用すべきツイートをボットで判定する
```
    1. 食に関すること
    2. 評価がいいこと
    3. 最近のツイートであること
    retweets = [tweet
        for tweet in tweets
        if self.judge(tweet)]
```
7.a. 食に関すること
```
    # 料理もツイートもまずひらがなに転換し、もしツイートの中に料理名が含まればＯ（まる）
    tweet_foods = [food
                  for food in self.foods
                  if to_hiragana(food) in to_hiragana(tweet.text)]
    is_food_related = len(self.get_tweet_foods(tweet)) > 0
```
7.b. 評価がいいこと (詳しい説明は最後で)
```
    # 単純ベイズ分類器で good か poor かを判定する
    classification = self.classifier.classify(tweet.text)
    is_good = classification == "good"
```
7.c. 最近のツイートであること
```
    # 正規表現で年/月/日/時/分/秒を取り出す
    self.tweet_time_formatter = "%Y-%m-%d %H:%M:%S"
    self.tweet_time_regex = re.compile(
        r"(?P<year>\d*?)-(?P<month>\d{2})-(?P<date>\d{2}) "
        r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})")
    
    # ツイート時間と今の時間差を計算
    hour_diff = (current_date - tweet_date) * \
            24 + (current_hour - tweet_hour)

    # 12時間内であるかどうかを判定
    is_recent = hour_diff < hours
```
8. 引用RTして、4. に戻って繰り返す
```
    # 引用RT
    status = self.generate_status(retweet)
    self.retweet_with_comment(retweet, status)

    # 引用したツイートを記録（30分間に50回の引用RTを超えないように）
    self.retweeted.append(retweet.id)

    # ボットを休ませる (15分間に180回の検索を超えないように)
    self.rest_time = max(0, self.max_request_frequency - retweets_count)
```

## 単純ベイズ分類器
分類器は文書をカテゴリに分類することができる。

カテゴリの例
- スパムかどうか（2つのカテゴリ）
- 大学生 / 高校生 / 中学生 / 小学生の中のどの学生が書いたか（4つのカテゴリ）

今回のカテゴリは二つある（good か poor か）
```
    with open(good_file, 'r') as file:
        good = Category("good", file.read().splitlines())

    with open(poor_file, 'r') as file:
        poor = Category("poor", file.read().splitlines())
```
各カテゴリに対し、`good`と`poor`のテキストファイルを解析し、単語（形態素）リストを取得する。

そしてリストで、単語の数と頻度を計算する。単語の数と頻度さえがあれば分類できる。
```
    def update_morphemes(self, documents):
        self.morphemes = document2morphemes('\n'.join(documents))
        self.count = len(self.morphemes)
        self.dict = {m: self.morphemes.count(m)
                     for m in set(self.morphemes)}
```
各カテゴリの処理が終わったら次は分類器を作る。
```
default_classifier = Classifier([good, poor])
```
 `PROB(good)` と `PROB(poor)` と二つのカテゴリが所有する単語の総数を計算する
```
    def update_classifier(self):
        self.morphemes_count = sum([category.count
                                    for category in self.categories])

        for category in self.categories:
            category.prior_prob = category.count / self.morphemes_count
```
できたら分類を始める
```
    def classify(self, document):
        # ベイズ確率が最大のカテゴリに分類する
        max_log_bayes_prob = -math.inf
        classification = ''

        # 確率を計算する前には分類する文書を解析し、単語リストを取得する
        morphemes = document2morphemes(document)

        # 各カテゴリ (good と poor) の確率を計算し分類する
        for category in self.categories:
            log_bayes_prob = self.calculate_bayes_prob(morphemes, category)

            if log_bayes_prob > max_log_bayes_prob:
                max_log_bayes_prob = log_bayes_prob
                classification = category.name

        return classification
```
ベイズ確率の計算は下記のよう
```
    def calculate_bayes_prob(self, morphemes, category):
        # まずは `PROB(good)` や `PROB(poor)`
        counts = [category.prior_prob]
        # それから各単語（形態素）が頻度辞書で現れた確率を計算する
        for morpheme in morphemes:
            if morpheme in category.dict:
                counts.append(category.dict[morpheme] / category.count)
            # もし単語が辞書になければ 1 / 単語の総数で計算する
            else:
                counts.append(1 / self.morphemes_count)

        # そのまま確率の掛け算をしたら、確率が小さくすぎてバグがでるから対数で計算
        log_bayes_prob = sum([math.log(count) for count in counts])
        return log_bayes_prob
```

## 終わり
