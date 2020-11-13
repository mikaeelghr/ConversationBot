import json
import logging
from typing import List, Dict

import telegram
from telegram.ext import MessageHandler, Filters, ConversationHandler

from Levels import levelHandler, send_message, bot, secrets
from Users import get_member_ids, get_group_id, get_group_members_text, get_all_group_members_text, get_scoreboard_text

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


class Game:
    conversation_handler = None
    with open("game.json", "r") as f:
        game_json = json.loads(f.read())
    dic_states = {}
    state_name = []

    index = 0
    for key in game_json["states"]:
        dic_states[key] = index
        state_name.append(key)
        index += 1

    @staticmethod
    def init_data(context: telegram.ext.CallbackContext):
        if "names" not in context.bot_data:
            context.bot_data["names"] = {}
        if "users_init_groups" not in context.bot_data:
            context.bot_data["users_init_groups"] = {}
        if "all_groups" not in context.bot_data:
            context.bot_data["all_groups"] = {}
        if "all_users" not in context.bot_data:
            context.bot_data["all_users"] = []

    @staticmethod
    def update_group_state(group_id: str, state_id: int, context: telegram.ext.CallbackContext):
        if group_id not in context.bot_data:
            context.bot_data[group_id] = {"state_id": 0, "scores": 0}
        context.bot_data[group_id]['state_id'] = state_id
        for user in get_member_ids(group_id, context):
            key_conv = list()
            key_conv.append(user)
            Game.conversation_handler.update_state(state_id, tuple(key_conv))
            send_message(user, Game.correct_data(
                Game.game_json["states"][Game.state_name[state_id]]["desc"], user, context))

    @staticmethod
    def get_scoreboard(context: telegram.ext.CallbackContext):
        scoreboard = {}
        for group_id in context.bot_data:
            if group_id.isnumeric():
                continue
            if 'scores' in context.bot_data[group_id]:
                scoreboard[group_id] = context.bot_data[group_id]['scores']
        print(scoreboard)
        return {k: v for k, v in sorted(scoreboard.items(), key=lambda item: -item[1]) if v > 0}

    @staticmethod
    def get_rank(group_id, context: telegram.ext.CallbackContext):
        scores = Game.get_scoreboard(context)
        if group_id not in scores:
            return -1
        rank = 1
        for other_group in scores:
            if scores[other_group] > scores[group_id]:
                rank += 1
        return rank

    @staticmethod
    def correct_data(data: str, user_id: int, context: telegram.ext.CallbackContext):
        group_id = get_group_id(user_id, context)
        print(group_id)
        cor_list = [
            ("$scoreboard", get_scoreboard_text(Game, context)),
            ("$score", str(context.bot_data[group_id]['scores'])),
            ("$rank", str(Game.get_rank(group_id, context))),
            ("$group_details_with_id", group_id + ":\n" + get_group_members_text(group_id, context, add_ids=True)),
            ("$all_group_details_with_id", get_all_group_members_text(context, add_ids=True)),
            ("$group_details", group_id + ":\n" + get_group_members_text(group_id, context)),
            ("$all_group_details", get_all_group_members_text(context)),
        ]
        for x in cor_list:
            data = data.replace(x[0], x[1])
        return data

    @staticmethod
    def get_input_js(update: telegram.Update):
        update_result = Game.conversation_handler.check_update(update)
        assert update_result and update_result[1] and update_result[1]
        for handler, input_js in all_handlers:
            if handler == update_result[1]:
                return input_js
        return None

    @staticmethod
    def process_message(update: telegram.Update, context: telegram.ext.CallbackContext):
        Game.init_data(context)
        bot.forwardMessage(chat_id=secrets["admin_chat"], from_chat_id=update.effective_chat.id,
                           message_id=update.message.message_id)
        input_js = Game.get_input_js(update)
        group_id = get_group_id(update.effective_user.id, context)
        if group_id not in context.bot_data:
            context.bot_data[group_id] = {"state_id": 0}
        if 'scores' not in context.bot_data[group_id]:
            context.bot_data[group_id]['scores'] = 0
        if "score_diff" in input_js:
            context.bot_data[group_id]['scores'] += input_js['score_diff']

        print(context.bot_data)
        for response in input_js["responses"]:
            assert 'sendto' in response
            if response['sendto'] == 'all_group_members':
                assert "data" in response
                for user_id in get_member_ids(group_id, context):
                    send_message(user_id, Game.correct_data(response["data"], update.effective_user.id, context))
            elif response['sendto'] == 'effective_user':
                send_message(update.effective_user.id,
                             Game.correct_data(response["data"], update.effective_user.id, context))
            else:
                raise Exception("invalid sendto type")
        if 'function' in input_js:
            levelHandler(Game, input_js["function"], update, context)

        if 'goto' in input_js:
            Game.update_group_state(group_id, Game.dic_states[input_js['goto']], context)

    @staticmethod
    def get_inputs(inputs_json: list) -> List[telegram.ext.Handler]:
        global all_handlers
        handlers = list()
        for input_json in inputs_json:
            assert "type" in input_json
            assert "responses" in input_json

            input_type = input_json["type"].lower()

            if input_type == "regex":
                print(input_json["regex"])
                assert "regex" in input_json
                handlers.append(
                    MessageHandler(Filters.regex(r'^(' + input_json["regex"] + r')$'), Game.process_message))
            elif input_type == "text":
                assert "text" in input_json
                handlers.append(MessageHandler(Filters.text(input_json["text"]), Game.process_message))
            elif input_type == "photo":
                handlers.append(MessageHandler(Filters.photo, Game.process_message))
            elif input_type == "video":
                handlers.append(MessageHandler(Filters.video, Game.process_message))
            elif input_type == "audio":
                handlers.append(MessageHandler(Filters.voice, Game.process_message))
            elif input_type == "all":
                handlers.append(MessageHandler(Filters.all, Game.process_message))
            else:
                raise Exception("invalid input type")
            all_handlers.append((handlers[-1], input_json))
        return handlers

    @staticmethod
    def get_states(type_name: str) -> Dict[int, List[telegram.ext.Handler]]:
        all_states = dict()
        for st_name, state in Game.game_json[type_name].items():
            assert 'inputs' in state
            handlers = Game.get_inputs(state['inputs'])
            all_states[Game.dic_states[st_name]] = handlers
        return all_states


all_handlers = []
states = Game.get_states("states")
entry_points_index = 0
if "entry_points" in Game.dic_states:
    entry_points_index = Game.dic_states["entry_points"]
entry_points = states[entry_points_index]
fallbacks = []
if "fallbacks" in Game.dic_states:
    fallbacks = states[Game.dic_states["fallbacks"]]
print(states)

Game.conversation_handler = ConversationHandler(
    entry_points=entry_points,
    states=states,
    per_user=True,
    per_chat=False,
    per_message=False,
    fallbacks=fallbacks,
    name="my_conversation",
    persistent=True,
)
