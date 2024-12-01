SELECT_LANGUAGE = "Пожалуйста, выберите язык словаря, который вы хотите использовать:"
LANGUAGE_REPLY = "Язык словаря установлен на {}."
CHOOSE_CURRENCY_TEXT = "Теперь, пожалуйста, выберите предпочтительную валюту:"
CURRENCY_REPLY = "Валюта сохранена как {}"
CHOOSE_LIMIT_TEXT = "Пожалуйста, установите ваш ожидаемый месячный лимит расходов или нажмите Пропустить"
NO_LIMIT = "Лимит не установлен!"
LIMIT_SET = "Лимит успешно установлен!"
TRANSACTION_START_TEXT = """Лимит успешно сохранен. Теперь вы можете отправлять транзакции. Возможны 3 формата: \n
Полный: <code>дата категория подкатегория сумма</code>
С категорией: <code>транспорт такси 5</code>
Без категории: <code>такси 5</code>

Последний пример будет сохранен с <b>текущей датой и временем</b> и использовать категорию из словаря - <b>транспорт</b>\n
Поддерживаются несколько строк и строки, разделенные запятыми, например, такси 4, еда 5\nкрасота 10

Введите /show_cat, чтобы получить предопределенный словарь категорий, или /change_cat, чтобы изменить его.
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
START_COMMAND_PROMPT = (
    "Пожалуйста, введите /start для начала или /help для получения помощи."
)
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
HELP_TEXT = """
О проекте☝🏼 Новый релиз 0.0.6 от 24.02.24. 👌🏼
Были добавлены новые функции. 🎉
Возможность установить ежемесячный лимит и отслеживать ежедневно. Пожалуйста, рассмотрите возможность повторного запуска /start, чтобы установить лимит.
Категории аренды и инвестирования исключены из среднего дневного значения.
Сообщение о начале адаптации исправлено. Рассмотрите возможность отправки /start, чтобы проверить это.

Ниже список доступных команд. Мы постоянно работаем над продуктом, поэтому если вы заметили какие-либо проблемы или 
хотите добавить дополнительные функции, свяжитесь с @dy0r2 

<b>/start</b> - Создать профиль или перезаписать текущие настройки. Будет запрошен язык словаря, валюта, месячный лимит
<b>/show</b> - Показать текущие месячные расходы по категориям и среднее.
<b>/show_last N</b> - Показать N последних сохраненных транзакций (по умолчанию 5) или транзакции для определенной категории (/show_last транспорт)
<b>/show_ext</b> - Подробный список расходов с топ-3 подкатегориями
<b>/income</b> - Добавить ваш доход. 🆕
<b>/show_income</b> - Показать текущий месячный доход по категориям и среднее.🆕
<b>/monthly_stat</b> - Показать месячную диаграмму и тепловую карту ваших расходов.🆕
<b>/monthly_ext_stat</b> - Показать месячную тепловую карту для каждой подкатегории.🆕
<b>/show_cat</b> - Показать используемый в настоящее время словарь.
<b>/change_cat</b> - Изменить существующий словарь, добавить или удалить категорию.  
<b>/delete N</b> - Удалить транзакцию с номером = N. Номер указан в команде /show_last. По умолчанию 1.
<b>/cancel</b> - Вернуться в главное меню, ожидая команды /start или записи транзакции.
<b>/download</b> - Скачать файл текущих расходов.
<b>/upload</b> - Загрузить новый файл расходов.
<b>/help</b> - Показать это меню.
<b>/leave</> - Удаление профиля. Данное действие нельзя отменить!


"""
UPLOADING_FINISHED = "Файл расходов обновлен!"
INCOME_TYPE1 = "доход"
INCOME_TYPE2 = "заработок"
SPENDINGS_TYPE1 = "расходы"
SPENDINGS_TYPE2 = "потрачено"
CANCEL_TEXT = "Отменено. Теперь вы можете ввести новую команду."
CONFIRM_SAVE_CAT = "Категория '<code>{}</code>' была выбрана для подкатегории '<code>{}</code>' и сохранена в словаре."
REQUEST_CAT = "Пожалуйста, отправьте мне категорию, которую вы хотите использовать для '<code>{}</code>'. Она будет добавлена в ваш словарь, и в следующий раз будет автоматически выбрана для <i>'{}'</i>:"
SPECIFY_MANUALLY_PROMPT = "Указать вручную"
CHOOSE_CATEGORY_PROMPT = """Я не смог найти категорию для '<code>{}</code>' в вашем словаре.
Пожалуйста, выберите одну из недавно использованных или <b>введите новую вручную</b>:"""
NOTIFY_OTHER_CAT = """Ваши транзакции для '<code>{}</code>' были сохранены в категории 'другое', так как я не смог найти подходящей категории в словаре.
Если вы знаете, какую категорию использовать, пожалуйста, добавьте её в словарь через /change_cat, или добавьте другую транзакцию в формате <code>категория подкатегория сумма</code>, и она будет автоматически обновлена в базе данных."""
LAST_RECORDS = "Список транзакций с индексным номером.\nОбщая сумма: <b>{}</b> \n\n{} \n\nЧтобы удалить, введите /delete с последующим индексом транзакции."
ABOUT = 'Привет, {}!\nВаша текущая валюта - <b>{}</b>, язык - <b>{}</b>, и\nМесячный лимит - <b>{}</b>\nТекущая версия 0.1.2 от 1.12.24'

