"""
Single source of truth for bot commands (T-021).

One registry drives three consumers:
  a) handler registration in src/core.py main() — loop over COMMANDS,
  b) /help rendering (build_help_text) in EN and RU,
  c) Telegram menu sync (sync_bot_commands) on post_init.

CommandSpec.handler is the *name* of the handler callable in src/core.py's
module globals (string, not the callable — avoids a circular import, since
several handlers are defined in core.py itself). handler=None marks
ConversationHandler entry points (leave, income, upload, start, menu,
change_cat): they are listed in the menu and /help but must NEVER be
loop-registered as plain CommandHandlers, or every such command would
dispatch twice.

Descriptions must be <= 256 chars (Telegram BotCommand limit) and HTML-free:
one /help call site renders with HTML parse mode, two render plain text.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from src.config import ADMIN_USER_ID


@dataclass(frozen=True)
class CommandSpec:
    name: str
    handler: Optional[str]  # core.py global name; None = ConversationHandler entry point
    desc_en: str
    desc_ru: str
    admin_only: bool = False
    in_menu: bool = True


# Registry order == menu order == /help order.
COMMANDS: Tuple[CommandSpec, ...] = (
    CommandSpec(
        "menu", None,
        "Open the interactive menu",
        "Открыть интерактивное меню",
    ),
    CommandSpec(
        "start", None,
        "Create your profile or reset language, currency and monthly limit",
        "Создать профиль или изменить язык, валюту и месячный лимит",
    ),
    CommandSpec(
        "show", "show_records",
        "Current month spendings per category with daily average",
        "Расходы за текущий месяц по категориям и в среднем за день",
    ),
    CommandSpec(
        "show_last", "latest_records",
        "Show last transactions, e.g. /show_last 10 or /show_last transport",
        "Показать последние транзакции, например /show_last 10 или /show_last транспорт",
    ),
    CommandSpec(
        "show_ext", "show_detailed",
        "Detailed spendings list with top-3 subcategories",
        "Подробный список расходов с топ-3 подкатегориями",
    ),
    CommandSpec(
        "delete", "delete_records",
        "Delete a transaction by its number from /show_last",
        "Удалить транзакцию по номеру из /show_last",
    ),
    CommandSpec(
        "income", None,
        "Add an income record",
        "Добавить доход",
    ),
    CommandSpec(
        "show_income", "show_records",
        "Current month income per category",
        "Доход за текущий месяц по категориям",
    ),
    CommandSpec(
        "delete_income", "delete_records",
        "Delete an income record by its number",
        "Удалить запись о доходе по номеру",
    ),
    CommandSpec(
        "monthly_stat", "send_chart",
        "Monthly spending chart and heatmap",
        "Месячный график расходов и тепловая карта",
    ),
    CommandSpec(
        "monthly_ext_stat", "send_ext_chart",
        "Monthly heatmap per subcategory for the current year",
        "Тепловая карта по подкатегориям за текущий год",
    ),
    CommandSpec(
        "yearly_stat", "send_yearly_piechart",
        "Yearly pie chart of your spendings",
        "Годовая круговая диаграмма расходов",
    ),
    CommandSpec(
        "show_cat", "show_cat",
        "Show your category dictionary",
        "Показать ваш словарь категорий",
    ),
    CommandSpec(
        "change_cat", None,
        "Add, rename or delete categories",
        "Добавить, переименовать или удалить категории",
    ),
    CommandSpec(
        "ask", "ask",
        "Ask AI a question about your spendings",
        "Задать ИИ вопрос о ваших расходах",
    ),
    CommandSpec(
        "download", "download_spendings",
        "Download your transactions as a CSV file",
        "Скачать ваши транзакции в формате CSV",
    ),
    CommandSpec(
        "upload", None,
        "Upload a spendings CSV file",
        "Загрузить файл расходов в формате CSV",
    ),
    CommandSpec(
        "about", "about",
        "Your profile and settings",
        "Ваш профиль и настройки",
    ),
    CommandSpec(
        "help", "help",
        "List all available commands",
        "Список всех доступных команд",
    ),
    # Functional but hidden from the menu — still listed in /help.
    CommandSpec(
        "cancel", "cancel",
        "Cancel the current action and return to the main menu",
        "Отменить текущее действие и вернуться в главное меню",
        in_menu=False,
    ),
    CommandSpec(
        "leave", None,
        "Delete your profile and all data. Cannot be undone",
        "Удалить профиль и все данные. Действие нельзя отменить",
        in_menu=False,
    ),
    # Admin-only: shown in the admin chat scope and admin /help.
    CommandSpec(
        "debug", "toggle_debug",
        "Toggle debug logging (admin)",
        "Переключить режим отладки (админ)",
        admin_only=True,
    ),
    CommandSpec(
        "show_log_chart", "show_log_chart",
        "Usage statistics charts (admin)",
        "Графики статистики использования (админ)",
        admin_only=True,
    ),
    CommandSpec(
        "admin_users", "admin_users",
        "List users with transaction counts and last activity (admin)",
        "Список пользователей с числом транзакций и последней активностью (админ)",
        admin_only=True,
    ),
    CommandSpec(
        "admin_export", "admin_export",
        "Export a user's transactions as CSV: /admin_export <user_id> (admin)",
        "Экспорт транзакций пользователя в CSV: /admin_export <user_id> (админ)",
        admin_only=True,
    ),
    CommandSpec(
        "admin_stats", "admin_stats",
        "Usage stats: DAU/WAU/MAU, new users, AI calls. Optional days: /admin_stats 7 (admin)",
        "Статистика: DAU/WAU/MAU, новые пользователи, вызовы ИИ. Дни опционально: /admin_stats 7 (админ)",
        admin_only=True,
    ),
)


def menu_commands(lang: str = "en", include_admin: bool = False) -> List[BotCommand]:
    """BotCommand list for set_my_commands, in registry order."""
    return [
        BotCommand(spec.name, spec.desc_ru if lang == "ru" else spec.desc_en)
        for spec in COMMANDS
        if spec.in_menu and (include_admin or not spec.admin_only)
    ]


def build_help_text(texts, is_admin: bool = False) -> str:
    """Render /help from the registry: HELP_INTRO + one line per command.

    `texts` is the src.texts / src.texts_ru module picked by check_language.
    Output is plain text (HTML-free) — call sites render it both with and
    without HTML parse mode.
    """
    lang = getattr(texts, "LANG", "en")
    lines = [texts.HELP_INTRO]
    for spec in COMMANDS:
        if spec.admin_only and not is_admin:
            continue
        desc = spec.desc_ru if lang == "ru" else spec.desc_en
        lines.append(f"/{spec.name} - {desc}")
    return "\n".join(lines)


async def sync_bot_commands(application) -> None:
    """Set the Telegram command menu from the registry (post_init callback).

    Default scope gets user commands (EN + ru language_code); the admin chat
    scope additionally gets admin-only commands. The admin call fails with
    "chat not found" if the admin never messaged the bot — that must not
    kill startup, so it is only logged.
    """
    bot = application.bot
    await bot.set_my_commands(menu_commands("en"), scope=BotCommandScopeDefault())
    await bot.set_my_commands(
        menu_commands("ru"), scope=BotCommandScopeDefault(), language_code="ru"
    )
    logging.info("Synced %d user commands to the default menu scope", len(menu_commands("en")))

    if not ADMIN_USER_ID:
        return
    admin_scope = BotCommandScopeChat(chat_id=ADMIN_USER_ID)
    try:
        await bot.set_my_commands(menu_commands("en", include_admin=True), scope=admin_scope)
        await bot.set_my_commands(
            menu_commands("ru", include_admin=True), scope=admin_scope, language_code="ru"
        )
    except Exception as exc:
        logging.warning(
            "Could not set admin-scope commands for chat %s: %s", ADMIN_USER_ID, exc
        )
