import copy
import json

import telegram
from telegram import User
from telegram.ext import MessageHandler

with open("init_groups.json", "r") as f:
    init_groups_json = json.loads(f.read())
with open("group_names.json", "r") as f:
    group_names_json = json.loads(f.read())


def get_user(user_id: int, context: telegram.ext.CallbackContext):
    for user in context.bot_data["all_users"]:
        if user.id == user_id:
            return user


def get_group_id(user_id: int, context: telegram.ext.CallbackContext) -> str:
    for group_id in context.bot_data["all_groups"]:
        for user in context.bot_data["all_groups"][group_id]['users']:
            if user_id == user.id:
                return context.bot_data["all_groups"][group_id]['name']
    return str(user_id)


def get_member_ids(group_id: str, context: telegram.ext.CallbackContext) -> list:
    for other_group_id in context.bot_data["all_groups"]:
        if context.bot_data["all_groups"][other_group_id]['name'] == group_id:
            users = []
            if "users" not in context.bot_data["all_groups"][other_group_id]:
                return users
            for user in context.bot_data["all_groups"][other_group_id]['users']:
                users.append(user.id)
            return users
    return [int(group_id)]


def get_group_members_text(group_id, context: telegram.ext.CallbackContext, add_ids=False):
    text = "امتیاز:" + str(context.bot_data[group_id]['scores']) + "\n"
    for user_id in get_member_ids(group_id, context):
        if user_id in context.bot_data["names"]:
            if add_ids:
                text += str(user_id) + " "
            if user_id in context.bot_data["names"]:
                text += context.bot_data["names"][user_id] + " "
            if get_user(user_id, context) is not None and get_user(user_id, context).username is not None:
                text += "@" + get_user(user_id, context).username + " "
            text += "\n"
    return text


def get_scoreboard_text(Game, context: telegram.ext.CallbackContext):
    text = "رتبه‌بندی تاکنون:\n\n"
    for group_id, score in Game.get_scoreboard(context).items():
        text += group_id + ":\n"
        text += get_group_members_text(group_id, context)
        text += "\n\n"
    return text


def get_all_group_members_text(context: telegram.ext.CallbackContext, add_ids=False):
    text = ""
    for group_id in context.bot_data["all_groups"]:
        if len(get_member_ids(group_id, context)) == 0:
            continue
        text += "\n\n" + group_id + "\n"
        for user_id in get_member_ids(group_id, context):
            if add_ids:
                text += str(user_id) + " "
            if user_id in context.bot_data["names"]:
                text += context.bot_data["names"][user_id] + " "
            if get_user(user_id, context) is not None and get_user(user_id, context)["username"] is not None:
                text += "@" + get_user(user_id, context).username + " "
            text += "\n"
    return text


def change_group(Game, user_id, group_id, context: telegram.ext.CallbackContext):
    try:
        old_group = get_group_id(user_id, context)
        context.bot_data["all_groups"][old_group]['users'].remove(get_user(user_id, context))
    except Exception as e:
        print(e)
    context.bot_data["all_groups"][group_id]['users'].append(get_user(user_id, context))

    key_conv = list()
    key_conv.append(user_id)
    Game.conversation_handler.update_state(context.bot_data[group_id]['state_id'], tuple(key_conv))


def remove_user(Game, user_id, context: telegram.ext.CallbackContext):
    try:
        old_group = get_group_id(user_id, context)
        context.bot_data["all_groups"][old_group]['users'].remove(get_user(user_id, context))
    except Exception as e:
        print(e)

    key_conv = list()
    key_conv.append(user_id)
    Game.conversation_handler.update_state(2, tuple(key_conv))


def add_user(user: User, context: telegram.ext.CallbackContext):
    context.bot_data["all_users"].append(user)
    for i in range(len(init_groups_json)):
        for username in init_groups_json[i]:
            if username == user.username:
                if i + 1 not in context.bot_data["users_init_groups"]:
                    context.bot_data["users_init_groups"][i + 1] = []
                context.bot_data["users_init_groups"][i + 1].append(user)
                return None
    if 0 not in context.bot_data["users_init_groups"]:
        context.bot_data["users_init_groups"][0] = []
    context.bot_data["users_init_groups"][0].append(user)


def get_sequence(n: int):
    assert n >= 1
    if n == 1:
        return [1]
    if n % 3 == 1:
        return [2, 2] + [3] * (n // 3 - 1)
    if n % 3 == 2:
        return [2] + [3] * (n // 3)
    return [3] * (n // 3)


def get_state(user_id, context: telegram.ext.CallbackContext):
    return context.bot_data[get_group_id(user_id, context)]["state_id"]


def build_groups(context: telegram.ext.CallbackContext):
    context.bot_data["all_groups"].clear()
    for gp_name in group_names_json:
        context.bot_data["all_groups"][gp_name] = {'name': gp_name, "users": []}
    sz_gp = 0
    for index in context.bot_data["users_init_groups"]:
        user_list = []
        for x in context.bot_data["users_init_groups"][index]:
            print(x, get_state(x.id, context))
            if get_state(x.id, context) != 1:
                user_list.append(x)
        seq = get_sequence(len(user_list))
        assert sum(seq) == len(user_list)
        util = 0
        for x in seq:
            context.bot_data["all_groups"][group_names_json[sz_gp + 1]]["users"] = \
                copy.copy(user_list[util:util + x])
            util += x
            sz_gp += 1
