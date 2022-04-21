from data import db_session
# Импортируем необходимые классы.
import logging
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler, ConversationHandler
from data.habits import Habit
import datetime
from telegram import ReplyKeyboardMarkup
import requests
from geocoder import get_ll_span

# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)
with open('data/token.txt') as f:
    TOKEN = f.read()

start_keyboard = [['/new_habit', '/help', '/print_by_name'],
                  ['/print_habits_today', '/print_habits_tomorrow', '/print_all_habits']]
start_markup = ReplyKeyboardMarkup(start_keyboard, one_time_keyboard=True)

additionally_keyboard = [['/description', '/address', '/delta_time'],
                         ['/save', '/cancel', '/help']]
additionally_markup = ReplyKeyboardMarkup(additionally_keyboard, one_time_keyboard=True)

cancel_keyboard = [['/help', '/cancel']]
cancel_markup = ReplyKeyboardMarkup(cancel_keyboard, one_time_keyboard=True)


def start(update, context):
    update.message.reply_text(
        "Привет! Я Бот-тренер привычек. Создайте какую-нибудь привычку, и я буду напоминать о ней в течение 21 дня!",
        reply_markup=start_markup)
    habits[update.message.chat_id] = {}


def cancel(update, context):
    update.message.reply_text("Создание привычки было отменено!",
                              reply_markup=start_markup)
    return ConversationHandler.END


def new_habit(update, context):
    update.message.reply_text("Введите название привычки.",
                              reply_markup=cancel_markup)
    return 1


def name_response(update, context):
    context.user_data['name'] = update.message.text
    if context.user_data['name'] in habits.keys():
        update.message.reply_text('Такая привычка уже создана!\nВведите другое название!')
        return 1
    update.message.reply_text(f"В какое время вы хотите тренировать привычку {context.user_data['name']}?\n"
                              f"(Ответ дайте в Формате ЧЧ:ММ.)",
                              reply_markup=cancel_markup)
    return 2


def time_response(update, context):
    chat_id = update.message.chat_id
    context.user_data['start_time'] = update.message.text
    try:
        hours, minutes = map(int, context.user_data['start_time'].split(':'))
        time = datetime.time(hour=hours, minute=minutes, second=0)
    except ValueError:
        update.message.reply_text("Некорректное время!\nВведите ещё раз!")
        return 2
    if any(map(lambda x: x[0].time() == time, habits[chat_id].values())):
        update.message.reply_text("На это время запланирована другая привычка!\nВведите другое время!")
        return 2
    update.message.reply_text("Хотите добавить дополнительную информацию или завершить создание привычки?",
                              reply_markup=additionally_markup)


def save_habit(update, context):
    habit = Habit()
    habit.name = context.user_data['name']

    habit.chat_id = update.message.chat_id

    date_start = datetime.date.today() + datetime.timedelta(days=1)
    hours, minutes = map(int, context.user_data['start_time'].split(':'))
    habit.start_datetime = datetime.datetime(year=date_start.year, month=date_start.month, day=date_start.day,
                                             hour=hours, minute=minutes)
    habit.description = context.user_data.get('description', '')
    habit.address = context.user_data.get('address')
    if 'delta_time' in context.user_data:
        hours, minutes = map(int, context.user_data['delta_time'].split(':'))
        habit.delta_time = datetime.time(hour=hours, minute=minutes, second=0)
    else:
        habit.delta_time = datetime.time(hour=0, minute=0, second=0)
    db_sess = db_session.create_session()
    db_sess.add(habit)
    db_sess.commit()

    habits[update.message.chat_id][habit.name] = (habit.start_datetime, habit.delta_time)

    set_timer(update, context, habit.name)

    update.message.reply_text("Привычка успешно добавлена!",
                              reply_markup=start_markup)

    return ConversationHandler.END


def add_description(update, context):
    update.message.reply_text("Введите описание",
                              reply_markup=cancel_markup)
    return 3


def get_description(update, context):
    context.user_data['description'] = update.message.text
    update.message.reply_text("Описание добавлено!")
    update.message.reply_text("Хотите добавить дополнительную информацию или завершить создание привычки?",
                              reply_markup=additionally_markup)


def add_address(update, context):
    update.message.reply_text("Введите адрес",
                              reply_markup=cancel_markup)
    return 4


def get_address(update, context):
    context.user_data['address'] = update.message.text
    update.message.reply_text("Адрес добавлен!")
    update.message.reply_text("Хотите добавить дополнительную информацию или завершить создание привычки?",
                              reply_markup=additionally_markup)


def add_delta_time(update, context):
    update.message.reply_text("Введите время за которое нужно дополнительно сообщать о привычке",
                              reply_markup=cancel_markup)
    return 5


def get_delta_time(update, context):
    context.user_data['delta_time'] = update.message.text
    try:
        hours, minutes = map(int, context.user_data['delta_time'].split(':'))
        datetime.time(hour=hours, minute=minutes, second=0)
    except ValueError:
        update.message.reply_text("Некорректное время!\nВведите ещё раз!")
        return 5
    update.message.reply_text("Добавлено!")
    update.message.reply_text("Хотите добавить дополнительную информацию или завершить создание привычки?",
                              reply_markup=additionally_markup)


def print_habits(update, context, habits_names):
    chat_id = update.message.chat_id
    for name_habit in habits_names:
        update.message.reply_text(f"{name_habit} - {habits[chat_id][name_habit][0].time()}",
                                  reply_markup=start_markup)
    if not habits_names:
        update.message.reply_text("Привычки отсутствуют!",
                                  reply_markup=start_markup)


def print_all_habits(update, context):
    chat_id = update.message.chat_id
    print_habits(update, context, habits[chat_id].keys())


def print_habits_today(update, context):
    chat_id = update.message.chat_id
    habits_today = tuple(filter(lambda x: habits[chat_id][x][0].date() <= datetime.date.today(), habits[chat_id].keys()))
    print_habits(update, context, habits_today)


def print_habits_tomorrow(update, context):
    chat_id = update.message.chat_id
    habits_tomorrow = tuple(
        filter(lambda x: habits[chat_id][x][0].date() <= datetime.date.today() + datetime.timedelta(days=1),
               habits[chat_id].keys()))
    print_habits(update, context, habits_tomorrow)


def print_by_name1(update, context):
    update.message.reply_text("Введите название привычки",
                              reply_markup=cancel_markup)
    return 1


def print_by_name2(update, context):
    name = update.message.text
    chat_id = update.message.chat_id
    if name not in habits[chat_id]:
        update.message.reply_text("Привычка не найдена!",
                                  reply_markup=start_markup)
        return ConversationHandler.END
    habit = db_sess.query(Habit).filter(Habit.name == name, Habit.chat_id == chat_id).first()
    update.message.reply_text(f"Название: {name}\n"
                              f"Действует до {habit.start_datetime + datetime.timedelta(days=21)}",
                              reply_markup=start_markup)
    if habit.description:
        update.message.reply_text(f"Описание: {habit.description}")
    if habit.address:
        update.message.reply_text(
            f"Необходимое местоположение: {habit.address}")
        get_picture(update, context, habit.address)
    if habit.delta_time != datetime.time(hour=0, minute=0, second=0):
        update.message.reply_text(
            f"Дополнительное напоминание приходит за {habit.delta_time.hour}ч. {habit.delta_time.minute} м.")

    return ConversationHandler.END


def cancel2(update, context):
    update.message.reply_text("Вы вернулись назад",
                              reply_markup=start_markup)
    return ConversationHandler.END


def set_timer(update, context, name_habit):
    chat_id = update.message.chat_id
    datetime_first = habits[chat_id][name_habit][0]
    delta_time = habits[chat_id][name_habit][1]
    t2 = datetime.timedelta(hours=delta_time.hour, minutes=delta_time.minute)
    for i in range(21):
        context.job_queue.run_once(advance_reminder,
                                   datetime_first + datetime.timedelta(days=i) - datetime.datetime.now() - t2,
                                   context=chat_id, name=str(chat_id))
        context.job_queue.run_once(reminder, datetime_first + datetime.timedelta(days=i) - datetime.datetime.now(),
                                   context=chat_id, name=str(chat_id))


def reminder(context):
    job = context.job
    chat_id = job.context
    now = datetime.time(hour=datetime.datetime.now().hour, minute=datetime.datetime.now().minute)
    name = tuple(filter(lambda x: habits[chat_id][x][0].time() == now, habits[chat_id].keys()))[0]
    context.bot.send_message(job.context, text=f'Пришло время для привычки {name}')


def advance_reminder(context):
    job = context.job
    chat_id = job.context
    now = datetime.time(hour=datetime.datetime.now().hour, minute=datetime.datetime.now().minute)
    name = tuple(filter(
        lambda x: (habits[chat_id][x][0] - datetime.timedelta(hours=habits[chat_id][x][1].hour,
                                                              minutes=habits[chat_id][x][1].minute)).time() == now,
        habits[chat_id].keys()))[0]
    context.bot.send_message(job.context,
                             text=f'Через {habits[chat_id][name][1].hour}ч. {habits[chat_id][name][1].minute}м. \
нужно будет'
                                  f' заняться привычкой {name}')


def get_picture(update, context, address):
    geocoder_uri = "http://geocode-maps.yandex.ru/1.x/"
    response = requests.get(geocoder_uri, params={
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "format": "json",
        "geocode": address
    })
    response = response.json()
    if not response["response"]["GeoObjectCollection"]["featureMember"]:
        update.message.reply_text("Картинка местоположения не найдена.")
        return
    toponym = response["response"]["GeoObjectCollection"][
        "featureMember"][0]["GeoObject"]
    ll, spn = get_ll_span(toponym)
    # Можно воспользоваться готовой функцией,
    # которую предлагалось сделать на уроках, посвящённых HTTP-геокодеру.
    static_api_request = f"http://static-maps.yandex.ru/1.x/?ll={ll}&spn={spn}&l=map"
    context.bot.send_photo(
        update.message.chat_id,  # Идентификатор чата. Куда посылать картинку.
        # Ссылка на static API, по сути, ссылка на картинку.
        # Телеграму можно передать прямо её, не скачивая предварительно карту.
        static_api_request,
        caption="Местоположение на карте"
    )


def help(update, context):
    update.message.reply_text("/new_habit - создать новую привычку,")
    update.message.reply_text("/print_by_name - вывести информацию о привычке по имени,")
    update.message.reply_text('/print_habits_today - вывести список запланированных на сегодня привычек,'),
    update.message.reply_text("/print_habits_tomorrow - вывести список запланированных на завтра привычек,")
    update.message.reply_text("/print_all_habits - вывести список всех привычек,")
    update.message.reply_text("/description - добавить или изменить описание привычки,")
    update.message.reply_text("/address - добавить или изменить необходимое местоположение,")
    update.message.reply_text(
        "/delta_time - добавить или изменить время за которое необходимо сообщить о привычке заранее,")
    update.message.reply_text("/save - сохранить привычку,")
    update.message.reply_text("/cancel - отмена.")


def main():
    # Создаём объект updater.
    # Вместо слова "TOKEN" надо разместить полученный от @BotFather токен
    updater = Updater(TOKEN)

    # Получаем из него диспетчер сообщений.
    dp = updater.dispatcher

    # Регистрируем обработчик в диспетчере.
    dp.add_handler(CommandHandler("start", start))

    dp.add_handler(CommandHandler("print_all_habits", print_all_habits))
    dp.add_handler(CommandHandler("print_habits_today", print_habits_today))
    dp.add_handler(CommandHandler("print_habits_tomorrow", print_habits_tomorrow))
    dp.add_handler(CommandHandler('help', help))

    conv_handler = ConversationHandler(

        entry_points=[CommandHandler('new_habit', new_habit)],

        states={
            1: [MessageHandler(Filters.text & ~Filters.command, name_response)],
            2: [MessageHandler(Filters.text & ~Filters.command, time_response), CommandHandler('save', save_habit),
                CommandHandler('description', add_description), CommandHandler('address', add_address),
                CommandHandler('delta_time', add_delta_time)],
            3: [MessageHandler(Filters.text & ~Filters.command, get_description), CommandHandler('save', save_habit),
                CommandHandler('description', add_description), CommandHandler('address', add_address),
                CommandHandler('delta_time', add_delta_time)],
            4: [MessageHandler(Filters.text & ~Filters.command, get_address), CommandHandler('save', save_habit),
                CommandHandler('description', add_description), CommandHandler('address', add_address),
                CommandHandler('delta_time', add_delta_time)],
            5: [MessageHandler(Filters.text & ~Filters.command, get_delta_time), CommandHandler('save', save_habit),
                CommandHandler('description', add_description), CommandHandler('address', add_address),
                CommandHandler('delta_time', add_delta_time)],
        },

        # Точка прерывания диалога. В данном случае — команда /cancel.
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    conv_handler2 = ConversationHandler(

        entry_points=[CommandHandler('print_by_name', print_by_name1)],

        states={
            1: [MessageHandler(Filters.text & ~Filters.command, print_by_name2)],
        },

        # Точка прерывания диалога. В данном случае — команда /cancel.
        fallbacks=[CommandHandler('cancel', cancel2)]
    )

    dp.add_handler(conv_handler2)
    # Запускаем цикл приема и обработки сообщений.
    updater.start_polling()

    # Ждём завершения приложения.
    # (например, получения сигнала SIG_TERM при нажатии клавиш Ctrl+C)
    updater.idle()


# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    db_session.global_init("db/habits.db")
    db_sess = db_session.create_session()
    habits = {}
    for habit in db_sess.query(Habit):
        if habit.chat_id not in habits:
            habits[habit.chat_id] = {}
        habits[habit.chat_id][habit.name] = (habit.start_datetime, habit.delta_time)
    main()
