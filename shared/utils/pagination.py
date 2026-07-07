"""
Pagination utilities for keyboard navigation.

Provides reusable pagination logic for Telegram inline keyboards.
"""

from typing import List, Tuple, Any, Optional
from telegram import InlineKeyboardButton


def get_page_slice(items: List[Any], page: int, items_per_page: int = 10) -> Tuple[List[Any], int, int]:
    """
    Get a slice of items for the current page.

    Args:
        items: Full list of items to paginate
        page: Current page number (0-indexed)
        items_per_page: Number of items per page

    Returns:
        Tuple of (page_items, start_idx, end_idx)
    """
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(items))
    return items[start_idx:end_idx], start_idx, end_idx


def has_previous_page(page: int) -> bool:
    """Check if there's a previous page."""
    return page > 0


def has_next_page(page: int, total_items: int, items_per_page: int) -> bool:
    """Check if there's a next page."""
    return (page + 1) * items_per_page < total_items


def get_total_pages(total_items: int, items_per_page: int) -> int:
    """Calculate total number of pages."""
    if total_items == 0:
        return 1
    return (total_items - 1) // items_per_page + 1


def create_nav_buttons(
    page: int,
    total_items: int,
    items_per_page: int,
    texts,
    prev_callback: str = "page_prev",
    next_callback: str = "page_next",
) -> List[InlineKeyboardButton]:
    """
    Create navigation buttons for pagination.

    Args:
        page: Current page number (0-indexed)
        total_items: Total number of items
        items_per_page: Number of items per page
        texts: Texts object with PREVIOUS_BUTTON and NEXT_BUTTON
        prev_callback: Callback data for previous button
        next_callback: Callback data for next button

    Returns:
        List of navigation buttons (may be empty, 1, or 2 buttons)
    """
    nav_buttons = []

    if has_previous_page(page):
        prev_text = getattr(texts, 'PREVIOUS_BUTTON', getattr(texts, 'BACK_BUTTON', '⬅️'))
        nav_buttons.append(InlineKeyboardButton(prev_text, callback_data=prev_callback))

    if has_next_page(page, total_items, items_per_page):
        next_text = getattr(texts, 'NEXT_BUTTON', '➡️')
        nav_buttons.append(InlineKeyboardButton(next_text, callback_data=next_callback))

    return nav_buttons


def paginate(
    items: List[Any],
    page: int,
    texts,
    items_per_page: int = 10,
    prev_callback: str = "page_prev",
    next_callback: str = "page_next",
) -> Tuple[List[Any], List[InlineKeyboardButton]]:
    """
    All-in-one pagination helper.

    Args:
        items: Full list of items to paginate
        page: Current page number (0-indexed)
        texts: Texts object with button labels
        items_per_page: Number of items per page
        prev_callback: Callback data for previous button
        next_callback: Callback data for next button

    Returns:
        Tuple of (page_items, nav_buttons)

    Example:
        categories_page, nav_buttons = paginate(
            categories, page=2, texts=texts,
            items_per_page=8,
            prev_callback="catpage_prev",
            next_callback="catpage_next"
        )
    """
    page_items, _, _ = get_page_slice(items, page, items_per_page)
    nav_buttons = create_nav_buttons(
        page, len(items), items_per_page, texts, prev_callback, next_callback
    )
    return page_items, nav_buttons
