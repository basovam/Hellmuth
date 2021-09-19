# Hellmuth
This is a bot for telegram with some features for automation of stocks analysis. It is not a final version, work is still in the process.\
You can try current version: [@Hellmuth_bot](https://telegram.dog/Hellmuth_bot)

## 1. Updating of config file.
Change `hostname` and `serverport` if it necessary.\
Replace `bot_token` with your bot token and `api_key` with your [AlphaVantage](https://www.alphavantage.co) api key.\
Fill path-section with correct file and folder paths.

## 2. Run data_file_maker.py for creation data file.
It using [AlphaVantage](https://www.alphavantage.co) service for getting data. For correct work of the script premium api_kei is necessary.

## 3. Start bot
```python3 main.py```

## 4. Create a Webhook.
For example, with curl:\
```curl -F "url=https://<your url address>" https://api.telegram.org/bot<your bot token>/setWebhook```

## Todo list:
- adding writing in log file in callback query processing section; \
- adding check for user language and english text of messages.
