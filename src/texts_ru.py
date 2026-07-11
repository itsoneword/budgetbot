SELECT_LANGUAGE = "Пожалуйста, выберите язык словаря, который вы хотите использовать:"
LANGUAGE_REPLY = "Язык словаря установлен на {}."
CHOOSE_CURRENCY_TEXT = "Теперь, пожалуйста, выберите предпочтительную валюту:"
CURRENCY_REPLY = "Валюта сохранена как {}"
CHOOSE_LIMIT_TEXT = "Пожалуйста, установите ваш ожидаемый месячный лимит расходов или нажмите Пропустить"
NO_LIMIT = "Лимит не установлен!"
LIMIT_SET = "Лимит успешно установлен!"
TRANSACTION_START_TEXT = """Настройки успешно сохранены. Теперь вы можете пользоваться ботом для учета ваших трат! 
\n
Есть 2 возможных формата: 
1. Через /menu => Добавить транзакцию
2. Через текстовый ввод:
<b>полный:</b>
<code>дата категория подкатегория сумма</code>
<b>С категорией:</b> 
<code>транспорт такси сумма</code>
<b>Без категории:</b> 
<code>такси сумма</code>

Несколько примеров для справки:
<code>такси 5</code>
<code>дом продукты 25</code>
 
Если дата не указана, то транзакция будет сохранена с текущей датой и временем.

Если не указана категория, бот предложит выбрать её из словаря.

Сохраненные категории и транзакции можно просмотреть и отредактировать через /menu => Редактировать категории \ Редактировать транзакции

Поддерживаются ввод нескольких строк и строк, разделенных запятыми, например, <code>такси 4, еда 5, красота 10</code>

Откройте /menu , для просмотра доступных функций.
\n/help для всех известных команд.
"""
TRANSACTION_SAVED_TEXT = "Транзакция сохранена!"
LIMIT_EXCEEDED = """
Текущий среднедневной расход <b>{current_daily_average}{currency}</b> выше вашего лимита <b>{daily_limit}{currency}</b> на {percent_difference}%❗️
Пожалуйста, <b>избегайте расходов в течение следующих {days_zero_spending} дней</b>✋🏼 или уменьшите дневной лимит до <b>{new_daily_limit}</b> до конца месяца.🙄"
"""
TRANSACTION_ERROR_TEXT = "Необходимо ввести сумму. Например, 'категория сумма' или 'дата категория сумма'. Пожалуйста, попробуйте снова."

INCOME_HELP = """Этот модуль позволяет добавлять доход и отслеживать его. Ожидаемые форматы:\n
<code>дата категория сумма</code>
<code>категория сумма</code>
<code>сумма</code> \n
Чтобы увидеть общую месячную статистику, используйте /show_income. Если вы случайно ввели неверное значение, используйте /delete_income, чтобы удалить последнюю транзакцию.
 """

RECORDS_NOT_FOUND_TEXT = "Записи не найдены."
RECORDS_TEMPLATE = """
Общее {record_type}: <b>{total}</b>{currency}\n
Сумма по категориям:\n{sum_per_cat}\n
Средняя сумма в день по 5 наиболее частым категориям {av_per_day_sum}{currency}, что составляет {comparison}% от вчерашнего дня.\n
По категориям:\n{av_per_day}

Общая среднедневная {record_type} составляет: {total_av_per_day}{currency}, без учета Аренды и Инвестиций
Вы {record_type2}: <b>{predicted_total}</b>{currency} к концу месяца при такой же нагрузке.
"""
START_COMMAND_PROMPT = """Упс, что-то пошло не так. Похоже, запись транзакции не может быть обработана.
 Пожалуйста, перейдите в главное меню /menu или начните сначала с помощью /start.\n\n
 Напоминаем, формат транзакции - наименование, за которым следует цена: <code>продукты 15</code>.
"""
CAT_DICT_MESSAGE = """
{}
Общее количество категорий: {}
"""
ADD_CAT_PROMPT = """Пожалуйста, отправьте мне новую категорию и подкатегорию в формате: `категория:подкатегория`\n
        Если вы хотите удалить уже существующую категорию, используйте '\-'\n `-категория:подкатегория`"""
ADD_CAT_SUCCESS = "Добавлено {}: {} в ваш словарь."
DEL_CAT_SUCCESS = "Удалено {}: {} из вашего словаря."
WRONG_INPUT_FORMAT = (
    "Формат ввода неверен. Пожалуйста, используйте формат: подкатегория:категория"
)
INVALID_RECORD_NUM = "Неверный номер записи. Пожалуйста, введите действительный номер."
NO_RECORDS = "Записей для отображения нет."
RECORD_LINE = "{}: {}"
INVALID_RECORD_NUM = "Неверный номер записи. Пожалуйста, введите действительный номер."
NO_RECORDS_TO_DELETE = "Нет записей для удаления."
RECORD_DELETED = "Запись номер {} удалена."
NOT_ENOUGH_RECORDS = "Записей меньше, чем {}."
LANG = "ru"
HELP_INTRO = """👋 BudgetBot помогает отслеживать расходы и доходы прямо в Telegram.
💬 Добавьте расход обычным сообщением, например «кофе 4» — или «31.12 кофе 4», чтобы записать задним числом.
📱 Попробуйте /menu — большинство функций доступны через интерактивное меню.
Заметили проблему или хотите новую функцию? Напишите @dy0r2"""
UPLOAD_FILE_TEXT = "Пожалуйста, загрузите ваш файл расходов. Он должен быть в формате CSV."
UPLOADING_FINISHED = "Файл расходов обновлен!"
INCOME_TYPE1 = "доход"
INCOME_TYPE2 = "заработок"
SPENDINGS_TYPE1 = "расходы"
SPENDINGS_TYPE2 = "потрачено"
CANCEL_TEXT = "Отменено. Теперь вы можете ввести новую команду."
CONFIRM_SAVE_CAT = "Категория '<code>{}</code>' была выбрана для подкатегории '<code>{}</code>'. Транзакция сохранена. "
REQUEST_CAT = "Пожалуйста, отправьте мне категорию, которую вы хотите использовать для '<code>{}</code>'. Она будет добавлена в ваш словарь, и в следующий раз будет автоматически выбрана для <i>'{}'</i>:"
SPECIFY_MANUALLY_PROMPT = "Указать вручную"
CHOOSE_CATEGORY_PROMPT = """Я не смог найти категорию для '<code>{}</code>' в вашем словаре.
Пожалуйста, выберите одну из недавно использованных или <b>введите новую вручную</b>:"""
CREATE_CATEGORY_PROMPT = """Пожалуйста, введите название новой категории для '<code>{}</code>':"""
SUBCAT_NOT_FOUND = """Я не нашел категорию для '<code>{}</code>' в вашем словаре. Пожалуйста, выберите из следующих категорий или создайте новую:"""
SUBCAT_FOUND_ONE = """Я нашел подкатегорию '<code>{}</code>' в категории '<code>{}</code>'. Хотите использовать эту категорию или выбрать другую?"""
SUBCAT_FOUND_MULTIPLE = """Я нашел подкатегорию '<code>{}</code>' в нескольких категориях: {}. Пожалуйста, выберите, какую вы хотите использовать:"""
CHOOSE_FROM_ALL_CATEGORIES = """Пожалуйста, выберите категорию для '<code>{}</code>' из всех доступных категорий:"""
TRANSACTION_CANCELED = """Транзакция была отменена."""
NOTIFY_OTHER_CAT = """Ваши транзакции для '<code>{}</code>' были сохранены в категории 'другое', так как я не смог найти подходящей категории в словаре.
Если вы знаете, какую категорию использовать, пожалуйста, добавьте её в словарь через /change_cat, или добавьте другую транзакцию в формате <code>категория подкатегория сумма</code>, и она будет автоматически обновлена в базе данных."""
LAST_RECORDS = "Список транзакций с индексным номером.\nОбщая сумма: <b>{}</b> \n\n{} \n\nЧтобы удалить, введите /delete с последующим индексом транзакции."
ABOUT = 'Привет, {}!\nВаша текущая валюта - <b>{}</b>, язык - <b>{}</b>, и\nМесячный лимит - <b>{}</b>\nТекущая версия {} от {}'
NO_LIMIT = "без лимита"

# Menu text strings
MAIN_MENU_TEXT = "📱 <b>Главное меню</b>\nЧто вы хотите сделать?"
SHOW_TRANSACTIONS_MENU_TEXT = "📊 <b>Показать транзакции</b>\nВыберите, что вы хотите просмотреть:"
SETTINGS_MENU_TEXT = "⚙️ <b>Настройки</b>\nВыберите, что вы хотите настроить:"
ADD_TRANSACTION_TEXT = "Пожалуйста, введите вашу транзакцию в одном из следующих форматов:\n<code>дата категория подкатегория сумма</code>\n<code>категория подкатегория сумма</code>\n<code>подкатегория сумма</code>"
BACK_TO_MAIN_MENU = "Возвращение в главное меню."

# Category editor text strings
NO_CATEGORIES_FOUND = "В вашем словаре не найдено категорий."
EDIT_CATEGORIES_PROMPT = "📝 <b>Выберите категорию для редактирования:</b>"
CATEGORY_OPTIONS = "Опции для категории '<code>{}</code>':"
ENTER_NEW_CATEGORY_NAME = "Пожалуйста, введите новое имя для категории '<code>{}</code>':"
CONFIRM_RENAME_CATEGORY = "Переименовать категорию '<code>{}</code>' в '<code>{}</code>'?"
CATEGORY_RENAMED = "Категория '<code>{}</code>' была переименована в '<code>{}</code>'."
RENAME_CANCELLED = "Переименование отменено."
CONFIRM_DELETE_CATEGORY = "Вы уверены, что хотите удалить категорию '<code>{}</code>' и все её траты?"
CATEGORY_DELETED = "Категория '<code>{}</code>' была удалена."
DELETE_CANCELLED = "Удаление '<code>{}</code>' отменено."
CATEGORY_TASKS = "Задачи в категории '<code>{}</code>':"
ENTER_NEW_TASK = "Пожалуйста, введите новую трату для категории '<code>{}</code>':"
TASK_ADDED = "Задача '<code>{}</code>' добавлена в категорию '<code>{}</code>'."
TASK_OPTIONS = "Опции для траты '<code>{}</code>' в категории '<code>{}</code>':"
ENTER_NEW_TASK_NAME = "Пожалуйста, введите новое имя для траты '<code>{}</code>':"
CONFIRM_RENAME_TASK = "Переименовать трату '<code>{}</code>' в '<code>{}</code>' в категории '<code>{}</code>'?"
TASK_RENAMED = "Задача '<code>{}</code>' была переименована в '<code>{}</code>' в категории '<code>{}</code>'."
RENAME_TASK_CANCELLED = "Переименование трату '<code>{}</code>' отменено."
CONFIRM_DELETE_TASK = "Вы уверены, что хотите удалить трату '<code>{}</code>' из категории '<code>{}</code>'?"
TASK_DELETED = "Задача '<code>{}</code>' была удалена из категории '<code>{}</code>'."
DELETE_TASK_CANCELLED = "Удаление траты '<code>{}</code>' отменено."
ERROR_PROCESSING_REQUEST = "Ошибка обработки вашего запроса. Пожалуйста, попробуйте снова."

CATEGORY_ADDED = "Категория '<code>{}</code>' была успешно добавлена."

SELECT_RECORDS_COUNT = "Выберите количество записей для отображения:"
LOADING_TRANSACTIONS = "Загрузка последних {count} транзакций..."
LOADING_MONTHLY_SUMMARY = "Загрузка месячной статистики..."
LOADING_LAST_MONTH_SUMMARY = "Загрузка статистики за прошлый месяц..."
LOADING_EXTENDED_STATS = "Загрузка расширенной статистики..."
LOADING_LAST_MONTH_EXTENDED_STATS = "Загрузка расширенной статистики за прошлый месяц..."
LOADING_INCOME_STATS = "Загрузка статистики доходов..."
GENERATING_MONTHLY_CHARTS = "Создание месячных графиков..."
GENERATING_YEARLY_CHARTS = "Создание годовых графиков..."

# Transaction entry texts
SELECT_TRANSACTION_CATEGORY = """Пожалуйста, выберите категорию, в которую вы бы хотели сохранить вашу трату.
Вы так же можете отправьте транзакцию в чат в одном из следующих форматов:

<code>такси 5</code>
<code>дом продукты 25</code>
<code>01.04 путешестия билеты 125</code>

Если дата не указана, то транзакция будет сохранена с текущей датой и временем.
Если не указана категория, то бот предложит выбрать её из существующих или создать новую.
"""
SELECT_TRANSACTION_SUBCATEGORY = "Пожалуйста, выберите подкатегорию или введите вручную в формате 'Подкатегория сумма':"
RECENT_SUBCATEGORY_AMOUNTS = "Недавние суммы для '{subcategory}':"
ENTER_TRANSACTION_AMOUNT = "Пожалуйста, введите сумму для '{subcategory}':"
CONFIRM_TRANSACTION_DETAILS = "Пожалуйста, подтвердите вашу транзакцию:\n\n<b>Категория:</b> {category}\n<b>Подкатегория:</b> {subcategory}\n<b>Сумма:</b> {amount} {currency}\n<b>Дата:</b> {date}"
TRANSACTION_CONFIRMED = "Транзакция успешно сохранена!"
MANUAL_SUBCATEGORY_DETECTED = "Я обнаружил подкатегорию '{subcategory}' и сумму {amount}."
NO_SUBCATEGORIES_FOUND = "Подкатегории для этой категории не найдены. Пожалуйста, введите подкатегорию и сумму вручную."

# Transaction edit text strings
EDIT_TRANSACTIONS_PROMPT = "📝 <b>Редактирование транзакций</b>\nИтого: <b>{}</b> {}\nВыберите транзакцию для редактирования:"
TRANSACTION_DETAILS = "<b>Детали транзакции</b>\n\nДата: {timestamp}\nКатегория: {category}\nПодкатегория: {subcategory}\nСумма: {amount} {currency}\n\nВыберите, что вы хотите отредактировать:"
ENTER_NEW_DATE_PROMPT = "Пожалуйста, введите новую дату в формате <code>ДД.ММ</code> или <code>ДД.ММ.ГГГГ</code>:"
SELECT_NEW_CATEGORY = "Пожалуйста, выберите новую категорию:"

ENTER_NEW_SUBCATEGORY = "Пожалуйста, введите новое название подкатегории:"
ENTER_NEW_AMOUNT_PROMPT = "Пожалуйста, введите новую сумму:"
CONFIRM_DELETE_TRANSACTION = "Вы уверены, что хотите удалить эту транзакцию?\n\nДата: {timestamp}\nКатегория: {category}\nПодкатегория: {subcategory}\nСумма: {amount} {currency}"
DATE_UPDATED_SUCCESS = "✅ Дата транзакции обновлена."
CATEGORY_UPDATED_SUCCESS = "✅ Категория транзакции обновлена."
SUBCATEGORY_UPDATED_SUCCESS = "✅ Подкатегория транзакции обновлена."
AMOUNT_UPDATED_SUCCESS = "✅ Сумма транзакции обновлена."
TRANSACTION_DELETED_SUCCESS = "✅ Транзакция удалена."
DELETE_CANCELLED = "❌ Удаление отменено."
INVALID_DATE_FORMAT = "❌ Неверный формат даты. Пожалуйста, используйте формат ДД.ММ или ДД.ММ.ГГГГ."
INVALID_AMOUNT_FORMAT = "❌ Неверный формат суммы. Пожалуйста, введите правильное число."
ERROR_DELETING_TRANSACTION = "❌ Ошибка удаления транзакции. Пожалуйста, попробуйте еще раз."
ERROR_UPDATING_TRANSACTION = "❌ Ошибка обновления транзакции. Пожалуйста, попробуйте еще раз."
ERROR_SELECTING_TRANSACTION = "❌ Ошибка выбора транзакции. Пожалуйста, попробуйте еще раз."

# Button text variables
SKIP_BUTTON = "Пропустить"
CHANGE_LANGUAGE_BUTTON = "🌍 Изменить язык"
CHANGE_CURRENCY_BUTTON = "💱 Изменить валюту"
CHANGE_LIMIT_BUTTON = "💰 Изменить месячный лимит"
BACK_BUTTON = "◀️ Назад"
NEXT_BUTTON = "Вперед ▶️"
PREVIOUS_BUTTON = "⬅️ Предыдущий"
CREATE_CATEGORY_BUTTON = "➕ Создать новую категорию"
CANCEL_BUTTON = "❌ Отмена"
USE_CATEGORY_BUTTON = "✅ Использовать '{}'"
CHOOSE_OTHER_CATEGORY_BUTTON = "🔄 Выбрать другую категорию"
SHOW_ALL_CATEGORIES_BUTTON = "🔄 Показать все категории"
ADD_TRANSACTION_BUTTON = "💰 Добавить транзакцию"
SHOW_TRANSACTIONS_BUTTON = "📊 Показать транзакции"
SETTINGS_BUTTON = "⚙️ Настройки"
EDIT_CATEGORIES_BUTTON = "📝 Редактировать категории"
EDIT_TRANSACTIONS_BUTTON = "✏️ Редактировать транзакции"
HELP_BUTTON = "❓ Помощь"
MONTHLY_SUMMARY_BUTTON = "📊 Месячная сводка"
LAST_MONTH_SUMMARY_BUTTON = "📈 За прошлый месяц"
LAST_TRANSACTIONS_BUTTON = "📋 Последние транзакции"
MONTHLY_CHARTS_BUTTON = "📈 Месячные графики"
DETAILED_STAT_BUTTON = "📊 Детальная статистика"
YEARLY_CHARTS_BUTTON = "📊 Годовые графики"
INCOME_STATS_BUTTON = "💵 Статистика доходов"
BACK_TO_MAIN_MENU_BUTTON = "🔙 Назад в главное меню"
CONFIRM_BUTTON = "✅ Подтвердить"
EDIT_DATE_BUTTON = "📅 Изменить дату"
EDIT_CATEGORY_BUTTON = "📁 Изменить категорию"
EDIT_SUBCATEGORY_BUTTON = "📂 Изменить название"
EDIT_AMOUNT_BUTTON = "💰 Изменить сумму"
DELETE_TRANSACTION_BUTTON = "🗑️ Удалить транзакцию"
DELETE_PROFILE_CONFIRMATION = "Вы уверены, что <b>хотите удалить свой профиль</b>? Это действие нельзя отменить. Пожалуйста, введите <code>Удалить профиль</code> в чате для подтверждения."
ALL_TRANSACTIONS_PROCESSED = "Все транзакции были успешно обработаны!"
ABOUT_BUTTON = "ℹ️ О боте"
SHOW_CATEGORIES_BUTTON = "📋 Показать категории"
ADD_REMOVE_CATEGORY_BUTTON = "➕ Добавить/удалить категорию"
CHANGE_NAME_BUTTON = "✏️ Изменить название"
DELETE_CATEGORY_BUTTON = "🗑️ Удалить категорию"
EDIT_TASKS_BUTTON = "📝 Редактировать траты"
BACK_TO_CATEGORIES_BUTTON = "🔙 Назад к категориям"
ADD_NEW_TASK_BUTTON = "➕ Добавить новую трату"
BACK_TO_CATEGORY_BUTTON = "🔙 Назад к категории"
EDIT_TASK_BUTTON = "✏️ Редактировать трату"
DELETE_TASK_BUTTON = "🗑️ Удалить трату"
BACK_TO_TASKS_BUTTON = "🔙 Назад к тратам"
PROGRESS_MSG = "Транзакция {}/{} сохранена: {} {}"
MULTI_TRANSACTION_START = "Обработка {} транзакций..."
CONFIRM_DELETE_BUTTON = "Подтвердить удаление!"

# New text templates for detailed transactions feature
SELECT_CATEGORIES_TEXT = "📊 <b>Выберите категории</b>\nВыберите категории для включения в детальный отчет. Выбирайте несколько категорий, нажимая на них (они будут отмечены значком ✅)."
SELECT_TIME_PERIOD_TEXT = "⏱️ <b>Выберите период времени</b>\nВыберите период времени для отчета по транзакциям:"
DETAILED_SUMMARY_TEMPLATE = """📊 <b>Детальная сводка за {period}</b>

Общая сумма расходов: <b>{total} {currency}</b>
Количество транзакций: {transaction_count}"""
FILTERED_TRANSACTIONS_TEXT = """📋 <b>Транзакции за {period}</b>
Категории: {categories}

Выберите транзакцию для просмотра деталей:"""
NO_CATEGORIES_FOUND = "❌ В вашей истории расходов не найдено категорий."
NO_TRANSACTIONS_FOUND = "❌ Не найдено транзакций для выбранных категорий и периода времени."

# Button text for detailed transactions
THREE_MONTH_BUTTON = "3 месяца"
SIX_MONTH_BUTTON = "6 месяцев"
TWELVE_MONTH_BUTTON = "12 месяцев"
YEAR_TO_DATE_BUTTON = "С начала года"
SELECT_ALL_BUTTON = "✅ Выбрать все"
CONTINUE_BUTTON = "▶️ Продолжить"
VIEW_TRANSACTIONS_BUTTON = "📋 Просмотр транзакций"

# Detailed transactions view texts
SELECT_TRANSACTION_TO_EDIT = "Нажмите на номер для редактирования соответствующей транзакции."
FILTERED_TRANSACTIONS_TEXT = "📊 <b>Отфильтрованные транзакции</b>\n\nПериод: <b>{period}</b>\nКатегории: <b>{categories}</b>"
SELECT_CATEGORIES_TEXT = "📂 <b>Выберите категории</b>\nВыберите категории для просмотра их транзакций:"
SELECT_TIME_PERIOD_TEXT = "⏱️ <b>Выберите период</b>\nВыберите период для просмотра:"
NO_TRANSACTIONS_FOUND = "Транзакции не найдены для выбранных категорий и периода."
NO_CATEGORIES_FOUND = "Категории не найдены в истории транзакций."
DETAILED_SUMMARY_TEMPLATE = "<b>Детальная сводка</b>\n\nПериод: <b>{period}</b>\nВсего: <b>{total} {currency}</b>\nТранзакций: <b>{transaction_count}</b>"

DETAILED_REPORT_LAST_MONTH_TEXT = "Детальный отчет за прошлый месяц:"
DETAILED_REPORT_TEXT = "Детальный отчет:"

# /ask — AI-вопросы по тратам
ASK_USAGE = "Задайте вопрос о ваших финансах, например:\n/ask сколько я потратил на продукты в прошлом месяце?"
ASK_THINKING = "🤔 Анализирую ваши данные..."
ASK_NOT_ALLOWED = "Команда /ask пока в ограниченном тестировании и недоступна для вашего аккаунта."
ASK_ERROR = "Не удалось получить ответ. Попробуйте позже."
ASK_NO_DATA = "У вас пока нет транзакций — сначала добавьте траты."

# Голосовой ввод и маршрутизация (T-019)
VOICE_TRANSCRIBING = "🎙 Распознаю..."
VOICE_TOO_LONG = "Голосовое сообщение слишком длинное — не более {seconds} секунд."
VOICE_ERROR = "Не удалось распознать голосовое сообщение. Попробуйте ещё раз."
VOICE_NO_SPEECH = "Не удалось расслышать речь в этом сообщении."
VOICE_HEARD = "🎙 Услышал: «{transcript}»"
VOICE_ROUTING = "🤔 Разбираюсь, что вы имели в виду..."
VOICE_CONFIRM_TX = "🎙 Услышал: «{transcript}»\n\nДобавить трату: {transaction}?"
VOICE_TX_CONFIRM_BTN = "✅ Добавить"
VOICE_TX_CANCEL_BTN = "❌ Отмена"
VOICE_TX_ACCEPTED = "Добавляю: {transaction}"
VOICE_TX_CANCELLED = "Отменено — ничего не сохранено."
VOICE_UNKNOWN = (
    "🎙 Услышал: «{transcript}»\n\n"
    "Не понял, что нужно сделать. Можно добавить трату («кофе 4.5»), "
    "задать вопрос через /ask или открыть /help."
)

# Регулярные транзакции (T-026)
RECURRING_BUTTON = "🔁 Регулярные"
RECURRING_USAGE = (
    "Чтобы добавить ежемесячную регулярную транзакцию:\n"
    "/recurring add <название> <сумма> <день>\n"
    "например /recurring add аренда 500 1"
)
RECURRING_LIST_EMPTY = (
    "У вас пока нет регулярных транзакций.\n\n"
    "Чтобы добавить ежемесячную регулярную транзакцию:\n"
    "/recurring add <название> <сумма> <день>\n"
    "например /recurring add аренда 500 1"
)
RECURRING_LIST_HEADER = "🔁 Ваши регулярные транзакции:"
RECURRING_PAUSED_LABEL = "на паузе"
RECURRING_DAY_WORD = "день"
RECURRING_ADDED = "Регулярная транзакция сохранена: {name} — {amount} {currency}, каждый месяц {day}-го числа."
RECURRING_DAY_CLAMP_NOTE = "В коротких месяцах она будет добавляться в последний день месяца."
RECURRING_INVALID_NAME = "Некорректное название: 1-60 символов, не может начинаться с '/'."
RECURRING_INVALID_AMOUNT = "Некорректная сумма: должна быть положительным числом."
RECURRING_INVALID_DAY = "Некорректный день: должно быть число от 1 до 31."
RECURRING_CONFIRM_DELETE = "Удалить регулярную транзакцию «{name}»? Это действие нельзя отменить."
RECURRING_POSTED = "🔁 Добавлена регулярная транзакция: {name} — {amount} {currency} (за {date})."
RECURRING_PAUSE_BTN = "⏸ {}"
RECURRING_RESUME_BTN = "▶️ {}"
RECURRING_DELETE_BTN = "🗑"
RECURRING_CONFIRM_DELETE_BTN = "🗑 Удалить"
RECURRING_BACK_BTN = "◀️ Назад"
# Admin panel commands (T-025)
ADMIN_ONLY = "Эта команда доступна только владельцу бота."
ADMIN_EXPORT_USAGE = "Использование: /admin_export <user_id>"
ADMIN_USER_NOT_FOUND = "Пользователь {user_id} не найден."
ADMIN_NO_TRANSACTIONS = "У пользователя {user_id} нет транзакций."
ADMIN_NO_USERS = "Пользователи не найдены."
ADMIN_USERS_HEADER = "Активных пользователей: {count} из {total} зарегистрированных (по последней активности; /admin_users all — показать всех)"
