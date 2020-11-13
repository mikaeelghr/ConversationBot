import json
import os

import telegram
from telegram.ext import MessageHandler

from Users import build_groups, get_member_ids, change_group, add_user, remove_user

proxy = 'http://127.0.0.1:38673/'
os.environ['http_proxy'] = proxy
os.environ['HTTP_PROXY'] = proxy
os.environ['https_proxy'] = proxy
os.environ['HTTPS_PROXY'] = proxy

with open("keys.json", "r") as f:
    secrets = json.loads(f.read())
bot = telegram.Bot(token=secrets["token"])


def send_message(user_id: int, data: str, inline=False):
    try:
        message = bot.send_message(chat_id=user_id, text=data)
        if not inline:
            bot.forwardMessage(chat_id=secrets['admin_chat'], from_chat_id=user_id, message_id=message.message_id)
    except Exception as e:
        print(e)


class Levels:
    @staticmethod
    def save_name(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        context.bot_data["names"][update.effective_user.id] = update.message.text
        add_user(update.effective_user, context)

    @staticmethod
    def build_groups(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        build_groups(context)

    @staticmethod
    def start_game(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        for group_id in context.bot_data["all_groups"]:
            Game.update_group_state(group_id, Game.dic_states['level1'], context)

    @staticmethod
    def print(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        send_message(secrets['admin_chat'], Game.correct_data(
            "\n".join(update.message.text.split('\n')[1:]), update.effective_user.id, context), True)

    @staticmethod
    def change_group(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        query = update.message.text
        user_id = int(query.split('\n')[1])
        group_id = query.split('\n')[2]
        change_group(Game, user_id, group_id, context)

    @staticmethod
    def remove_user(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        query = update.message.text
        user_id = int(query.split('\n')[1])
        remove_user(Game, user_id, context)

    @staticmethod
    def change_score(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        query = update.message.text
        group_id = query.split('\n')[1]
        score_diff = int(query.split('\n')[2])
        context.bot_data[group_id]['scores'] += score_diff
        print(context.bot_data)

    @staticmethod
    def send_message_to_user(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        query = update.message.text
        user_id = int(query.split('\n')[1])
        message = "\n".join(query.split('\n')[2:])
        send_message(user_id, message, inline=True)

    @staticmethod
    def send_message_to_group(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        query = update.message.text
        group_id = query.split('\n')[1]
        message = "\n".join(query.split('\n')[2:])
        for user_id in get_member_ids(group_id, context):
            send_message(user_id, message, inline=True)

    @staticmethod
    def send_message_to_all(Game, update: telegram.Update, context: telegram.ext.CallbackContext):
        query = update.message.text
        message = "\n".join(query.split('\n')[1:])
        for user in context.bot_data["all_users"]:
            send_message(user.id, message, inline=True)


def levelHandler(Game, function_name, update: telegram.Update, context: telegram.ext.CallbackContext):
    if callable(getattr(Levels, function_name)):
        getattr(Levels, function_name)(Game, update, context)
        return None
    update.message.reply_text("خطا")
