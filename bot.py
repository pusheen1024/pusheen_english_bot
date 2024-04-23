import random

import logging
import requests
from telegram import ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, ConversationHandler, filters

from config import BOT_TOKEN

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

FIRST_STATE = 1
SECOND_STATE = 2
TRIES = 5
WEBSITE = 'https://prism-colorful-engineer.glitch.me'

def create_hints(word, entry):
    try:
        synonyms = list(map(lambda x: x['text'],
                            random.sample([syn for syn in entry["def"][0]["tr"] if word not in syn['text']], 2)))
        hints = [f'The first letter of this word is <b>{word[0]}</b>.',
                 f'This word can mean the same as "{synonyms[0]}" :3',
                 f'The last letter of this word is <b>{word[-1]}</b> ^^',
                 f'This word can mean the same as "{synonyms[1]}"!',
                 f'This word is pronounced like [{entry["def"][0]["ts"]}]']
        return hints
    except Exception:
        pass


def add_points(email, success):
    requests.post(f'{WEBSITE}/api/users/{email}', json={'success': success})


async def start(update, context):
    response = requests.get(f'{WEBSITE}/api/random_word').json()
    hints = create_hints(response['word'], response['entry'])
    while not hints:
        hints = create_hints(response['word'], response['entry'])
    context.user_data['correct_word'] = response['word']
    context.user_data['hints'] = hints
    context.user_data['tries'] = 0
    if 'email' not in context.user_data:
        user = update.effective_user
        await update.message.reply_html(
            rf'Hello, {user.mention_html()}! I am Pusheen and I am here to play a guessing game with you :3')
        await context.bot.send_photo(update.message.chat_id, photo=open('img/bot.png', 'rb'))
        await update.message.reply_text('Please, enter the email address which you used for registration!')
        await update.message.reply_html(rf'''If you haven't signed up at the website yet, you can do it
<a href="{WEBSITE}/register">here</a> ^^''')
        return FIRST_STATE
    else:
        await update.message.reply_html("Let's play again! Waiting for your guess...")
        return SECOND_STATE


async def login(update, context):
    if 'message' in requests.get(f'{WEBSITE}/api/users/{update.message.text}').json():
        await update.message.reply_text('Sorry, we do not have a user with this email address :(')
    else:
        context.user_data['email'] = update.message.text
        await update.message.reply_text('Thanks!')
        await update.message.reply_text('Waiting for your guess...')
        return SECOND_STATE


async def guess(update, context):
    if update.message.text.lower() == context.user_data['correct_word'].lower():
        await update.message.reply_text("Congratulations! You've guessed the word!!")
        await update.message.set_reaction(reaction='❤')
        add_points(context.user_data["email"], 1)
        await update.message.reply_text('Do you want to play again?', reply_markup=markup)
    else:
        if context.user_data['tries'] == TRIES:
            await update.message.reply_text(f"""Sorry, you didn't guess the word :(
It was "{context.user_data['correct_word']}".""")
            add_points(context.user_data["email"], 0)
            await update.message.reply_text('Do you want to play again?', reply_markup=markup)
        else:
            await update.message.reply_html(context.user_data['hints'][context.user_data['tries']])
            context.user_data['tries'] += 1
            await update.message.set_reaction(reaction='💔')


async def stop(update, context):
    context.user_data.clear()
    await update.message.reply_text("Bye! See you soon :3")
    return ConversationHandler.END


application = Application.builder().token(BOT_TOKEN).build()

start_handler = CommandHandler('start', start)
stop_handler = CommandHandler('stop', stop)
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={FIRST_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, login)],
            SECOND_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, guess)]},
    fallbacks=[CommandHandler('stop', stop)])

application.add_handler(conv_handler)
application.add_handler(start_handler)
application.add_handler(stop_handler)
reply_keyboard = [['/start', '/stop']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

application.run_polling()
