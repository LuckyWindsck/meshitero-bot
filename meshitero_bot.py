import os
import random
import time
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path


import naive_bayes_classifier as naive_bayes
from kana_translate import to_hiragana
from twitter_client import TwitterClient


def create_if_inexistent(filename):
    """ファイルがなければ作る。そしてファイルの Path を返す

    Parameters
    ----------
    filename : ファイル名

    Returns
    -------
    file : ファイルの Path
    """

    file = Path(filename)
    file.touch(exist_ok=True)

    return file


def is_time_passed(start_time, delta_time):
    """開始時間から一定の時間差が経ったのかを判定する

    Parameters
    ----------
    start_time : 開始時間
    delta_time : 時間差

    Returns
    -------
    is_passed : 経ったのか
    """

    time_diff = datetime.now() - start_time
    is_passed = time_diff.seconds > delta_time.seconds

    return is_passed


class MeshiteroBot(TwitterClient):
    def __init__(self, classifier):
        """飯テロボット

        Parameters
        ----------
        classifier : 飯テロ判定用の分類器
        """

        super().__init__("飯テロ警察BOT")

        # 15分間に180回の検索を超えないように
        self.max_request_frequency = 15 * 60 / 180
        # 30分間に50回の引用RTを超えないように
        self.max_retweet_per_semihour = 50

        self.classifier = classifier
        self.rest_time = self.max_request_frequency
        # 起動する時間を記録
        self.start_time = datetime.now()

        self.file = {}
        self.file["comments"] = "comments"
        self.file["foods"] = "foods"
        self.file["searched_tweet"] = create_if_inexistent("searched_tweet")
        self.file["query"] = "query"

        # 引用のコメントリスト
        with open(self.file["comments"], "r") as file:
            self.comments = file.read().splitlines()

        # 料理のリスト（ひらがなに変換した）
        with open(self.file["foods"], 'r') as file:
            self.foods = file.read().splitlines()

        # どのツイートまで検索したかをファイルから読み込む
        with open(self.file["searched_tweet"], "r") as file:
            self.searched_id = file.readline().rstrip()

        # 検索用のクエリ
        with open(self.file["query"], "r") as file:
            self.query = " OR ".join(file.read().splitlines())

        # 引用RTしたツイートの id を記録
        self.retweeted = []

    def search_meshitero(self, search_limit=100):
        """飯テロツイートを検索する

        条件を満たすツイートのみ検索する
        1. query の一つでも含まれること
        2. 「#飯テロ」タグが付いてること
        3. 画像が付いてること
        4. RT でないこと
        5. 昨日からのツイートのみ
        6. 日本語であること
        7. 「最新ツイート」であること
        8. tweet_id 以後のツイートのみ（重複しないように）

        Parameters
        ----------
        search_limit : 取得するツイート数（デフォルト: 100 件まで検索する）

        Returns
        -------
        tweets : 取得したツイートリスト
        """
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

        q = "({}) (#飯テロ) filter:images -filter:retweets since:{}"\
            .format(self.query, yesterday)

        tweets = self.api.search(q=q,
                                 lang="ja",
                                 result_type="recent",
                                 since_id=self.searched_id,
                                 count=search_limit)

        return tweets

    def get_tweet_foods(self, tweet):
        """ツイートから料理リストを取得して返す

        Parameters
        ----------
        tweet : ツイート

        Returns
        -------
        tweet_foods : 料理リスト
        """
        tweet_foods = [food
                       for food in self.foods
                       if to_hiragana(food) in to_hiragana(tweet.text)]

        return tweet_foods

    def is_food_related_tweet(self, tweet):
        """食に関するツイートか否かを判定する

        Parameters
        ----------
        tweet : ツイート

        Returns
        -------
        is_food_related : 食に関するツイートか否か
        """
        is_food_related = len(self.get_tweet_foods(tweet)) > 0

        return is_food_related

    def is_good_tweet(self, tweet):
        """ツイートは良い評価か否かを判定する

        Parameters
        ----------
        tweet : ツイート

        Returns
        -------
        is_good : ツイートは良い評価か否か
        """
        classification = self.classifier.classify(tweet.text)
        is_good = classification == "good"

        return is_good

    def is_recent_tweet(self, tweet, hours=12):
        """最近のツイートか否かを判定する

        Parameters
        ----------
        tweet : ツイート
        hours : 「最近」の基準（デフォルト: 12時間内のツイートに反応する）

        Returns
        -------
        is_recent : 最近のツイートか否か
        """
        now = time.strftime(self.tweet_time_formatter, time.gmtime())
        current_time = self.tweet_time_regex.match(now).groupdict()
        tweet_time = self.tweet_time_regex.match(
            str(tweet.created_at)).groupdict()

        current_date = int(current_time['date'])
        tweet_date = int(tweet_time['date'])
        current_hour = int(current_time['hour'])
        tweet_hour = int(tweet_time['hour'])

        hour_diff = (current_date - tweet_date) * \
            24 + (current_hour - tweet_hour)

        is_recent = hour_diff < hours

        return is_recent

    def judge(self, tweet):
        """引用すべきツイートかどうかを判定する
        1. 食に関すること
        2. 評価がいいこと
        3. 最近のツイートであること

        Parameters
        ----------
        tweet : ツイート

        Returns
        -------
        all_passed : 全部の条件を満たしたかどうか
        """
        is_food_related = self.is_food_related_tweet(tweet)
        is_good = self.is_good_tweet(tweet)
        is_recent = self.is_recent_tweet(tweet)

        all_passed = all([is_food_related, is_good, is_recent])

        return all_passed

    def generate_status(self, tweet):
        """引用する場合のツイート内容を作り出す

        Parameters
        ----------
        tweet : ツイート

        Returns
        -------
        status : 引用する場合のツイート内容
        """
        tweet_foods = self.get_tweet_foods(tweet)
        food = random.choice(tweet_foods)
        comment = random.choice(self.comments)
        status = "{}美味しそうですね。\n{}".format(food, comment)

        return status

    def create_tweet_url(self, tweet):
        """ツイートのリンクを取得

        Parameters
        ----------
        tweet : ツイート

        Returns
        -------
        tweet_url : ツイートのリンク
        """
        tweet_url = 'https://twitter.com/{}/status/{}'.format(
            tweet.user.screen_name,
            tweet.id)

        return tweet_url

    # コメントを付けてリツイート
    def retweet_with_comment(self, tweet, comment):
        """コメントを付けてリツイートする

        Parameters
        ----------
        tweet : ツイート
        comment: コメント

        Returns
        -------
        status : 引用する場合のツイート内容
        """
        user_name = tweet.user.screen_name
        user_displayname = tweet.user.name
        tweet_id = tweet.id
        tweet_url = self.create_tweet_url(tweet)

        status = '(授業用BOT)\n{} {}'.format(comment, tweet_url)

        print('{}さん (@{}) のツイートを引用RTしました。'.format(user_displayname, user_name))
        print('ツイートID: {}'.format(tweet_id))
        print('コメント: {}'.format(comment))

        self.api.update_status(status)

        return status

    def task(self):
        """ボットの仕事（取り締まり）

        Returns
        -------
        self
        """
        print("お仕事始めます。")

        # ツイートを検索する
        tweets = self.search_meshitero()

        # もしなかったら仕事終わり
        if not tweets:
            print("引用すべきツイートがなさそうですね。")
            self.rest_time = self.max_request_frequency
            return self

        # どのツイートまで検索したかをファイルに書き込む
        with open(self.file["searched_tweet"], "w") as file:
            self.searched_id = str(tweets[0].id)
            file.write(self.searched_id)

        # 引用すべきツイート
        retweets = [tweet
                    for tweet in tweets
                    if self.judge(tweet)]

        retweets_count = len(retweets)
        print("{}件のツイートを引用します。".format(retweets_count))

        for retweet in retweets:
            time.sleep(1)

            # コメントを作り出して引用RTする
            status = self.generate_status(retweet)
            self.retweet_with_comment(retweet, status)

            # 引用したツイートを記録
            self.retweeted.append(retweet.id)

        # リクエスト制限を超えないように仕事が終わったら休ませる
        self.rest_time = max(0, self.max_request_frequency - retweets_count)
        return self

    def run(self):
        """ボットを起動する"""
        print("{}です。働きます。".format(self.name))
        while True:
            # 起動してから30分経ったらボット終了。
            is_thiry_minutes_passed = is_time_passed(self.start_time,
                                                     timedelta(minutes=30))
            if is_thiry_minutes_passed:
                print("もう30分働きました。帰ります。")
                exit(0)

            self.task()

            # もしツイート制限に達したらボット終了
            is_api_limit_reached = \
                self.max_retweet_per_semihour < len(self.retweeted)

            if is_api_limit_reached:
                print('ツイート制限に達しました。')
                print('ボット終了します。')
                exit(0)

            print("{}秒休みます。".format(self.rest_time))
            time.sleep(self.rest_time)


if __name__ == "__main__":
    load_dotenv()

    # 認証するための環境変数
    env_keys = ["CONSUMER_KEY", "CONSUMER_SECRET",
                "ACCESS_TOKEN_KEY", "ACCESS_TOKEN_SECRET"]

    credentials = {key: os.getenv(key) for key in env_keys}

    classifier = naive_bayes.default_classifier

    MeshiteroBot(classifier)\
        .setCredentials(credentials)\
        .connect()\
        .run()
