import tweepy
import re


class TwitterClient:
    def __init__(self, name, credentials=None):
        """Twitterクライアント

        Parameters
        ----------
        name : クライアント名
        credentials : APIを使うための各種 Key
        """
        self.name = name
        self.credentials = credentials

        # ツイート関連
        self.tweet_time_formatter = "%Y-%m-%d %H:%M:%S"
        self.tweet_time_regex = re.compile(
            r"(?P<year>\d*?)-(?P<month>\d{2})-(?P<date>\d{2}) "
            r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})")

        print("{}です。よろしくお願いします。".format(self.name))

    def setCredentials(self, credentials):
        """credentials を設定する

        Parameters
        ----------
        credentials : APIを使うための各種 Key

        Returns
        -------
        self
        """
        self.credentials = credentials
        return self

    def connect(self):
        """API に繋がる

        Returns
        -------
        self
        """

        try:
            self.auth = tweepy.OAuthHandler(
                self.credentials["CONSUMER_KEY"],
                self.credentials["CONSUMER_SECRET"])
            self.auth.set_access_token(
                self.credentials["ACCESS_TOKEN_KEY"],
                self.credentials["ACCESS_TOKEN_SECRET"])
        except TypeError:
            print("APIキーを忘れましたか？")
            return self

        # 検索するため twitter api の認証をする
        self.api = tweepy.API(self.auth)

        # 認証の確認
        try:
            self.api.verify_credentials()
        except tweepy.error.TweepError:
            print("認証に問題があります。")
            return self

        print("API取得しました。")
        return self
