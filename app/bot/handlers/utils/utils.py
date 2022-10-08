from bot import models
from abridge_bot.settings import TELEGRAM_LOGS_CHAT_ID

from flashtext import KeywordProcessor
from bot.handlers.broadcast_message.utils import (
    _send_message, _send_media_group, _revoke_message,
    _remove_message_markup, _edit_message
)
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_inline_marckup(markup):
    keyboard = []
    for row in markup:
        keyboard.append([])
        for col in row:
            if len(col) == 2 and col[1]:
                btn = InlineKeyboardButton(text=col[0], url=col[1])
            else:
                btn = InlineKeyboardButton(
                    text=col[0], callback_data=col[0].lower().replace(' ', ''))
            keyboard[-1].append(btn)

    return InlineKeyboardMarkup(keyboard)


def get_keyboard_marckup(markup):
    keyboard = []
    for row in markup:
        keyboard.append([])
        for col in row:
            btn = KeyboardButton(text=col[0])
            keyboard[-1].append(btn)

    return ReplyKeyboardMarkup(keyboard)



MARKUP_MSG_DECODER = {
    models.MessageType.POLL: lambda x: x,
    models.MessageType.FLY_BTN: get_inline_marckup,
    models.MessageType.KEYBOORD_BTN: get_keyboard_marckup,
    models.MessageType.SIMPLE_TEXT: lambda x: None,
    None: lambda x: None
}

def get_message_text(text, user_keywords):
    keyword_processor = KeywordProcessor()
    keyword_processor.add_keywords_from_dict(user_keywords)
    text = keyword_processor.replace_keywords(text)
    return text


def send_poll(user_id, poll_id, text, markup, context):
    questions = [m[0][0] for m in markup]
    message = context.bot.send_poll(
        user_id,
        text,
        questions,
        is_anonymous=False,
        allows_multiple_answers=False,
    )
    payload = {
        message.poll.id: {
            'poll_id': poll_id,
            "questions": questions,
            "message_id": message.message_id,
            "chat_id": user_id,
            #"answers": 0,
        }
    }
    context.bot_data.update(payload)
    return None


def send_message(prev_state, next_state, context, user_id, prev_message_id):
    prev_msg_type = prev_state["message_type"] if prev_state else None
    next_msg_type = next_state["message_type"]

    message_text = get_message_text(
        next_state["text"], next_state['user_keywords']
    )
    
    photos = next_state.get("photos", [])
    if len(photos) > 1:
        _send_media_group(photos, user_id=user_id)
        photo = None
    elif len(photos) == 1:
        photo = photos.pop(0)
    else:
        photo = None

    need_remove_markup = prev_message_id and \
        (prev_msg_type in [models.MessageType.FLY_BTN, models.MessageType.KEYBOORD_BTN])
    reply_markup = MARKUP_MSG_DECODER[next_msg_type](next_state["markup"])

    if need_remove_markup:
        if next_msg_type == prev_msg_type and len(prev_state.get("photos", [])) == 0:
            message_id = _edit_message(
                user_id=user_id,
                text=message_text,
                photo=photo,
                reply_markup=reply_markup,
                message_id=prev_message_id
            )
            return message_id
        _remove_message_markup(user_id=user_id, message_id=prev_message_id)
    
    if next_msg_type == models.MessageType.POLL:
        message_id = send_poll(
            user_id, poll_id=next_state['poll_id'], 
            text=message_text, markup=reply_markup, context=context
        )
        return message_id
    message_id = _send_message(
        user_id=user_id, text=message_text,
        photo=photo, reply_markup=reply_markup
    )
    return message_id


def send_broadcast_message(next_state, user_id, prev_message_id):
    next_msg_type = next_state["message_type"]
    if next_msg_type == models.MessageType.POLL:
        return None

    message_text = get_message_text(next_state["text"], next_state['user_keywords'])
    if prev_message_id:
        _remove_message_markup(user_id=user_id, message_id=prev_message_id)
        
    reply_markup = MARKUP_MSG_DECODER[next_msg_type](next_state["markup"])
    photos = next_state.get("photos", [])
    photo = photos.pop(0) if len(photos) > 0 else None

    prev_msg_id = _send_message(
        user_id=user_id,
        text=message_text,
        photo=photo,
        reply_markup=reply_markup
    )
    return prev_msg_id


def send_logs_message(msg_text, user_keywords, prev_state):
    try:
        markup = prev_state['markup']
        decoder = dict([(k[0][0].replace(' ', '').lower(), k[0][0]) for k in markup])
        msg_text = decoder.get(msg_text, msg_text)
    except Exception as e:
        msg_text = msg_text

    text = f'{msg_text}\n\n<b>first_name</b> (user_id)' 
    try:
        text = get_message_text(text, user_keywords)
    except Exception as e:
        text = f'{msg_text}\n\n<b>first_name</b> (user_id)' 
    _send_message(user_id=TELEGRAM_LOGS_CHAT_ID, text=text)


def admin_logs_message(msg_text, **kwargs):
    message_text = msg_text.format(**kwargs)
    _send_message(user_id=TELEGRAM_LOGS_CHAT_ID, text=message_text)