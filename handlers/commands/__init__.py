"""handlers.commands — пакет."""
from handlers.commands import _legacy
from handlers.commands.start import start, help_command
from handlers.commands.personal import personal_command, format_personal_summary, personal_keyboard
from handlers.commands.receipt import (
    handle_recognize_receipt, handle_receipt_save, handle_receipt_object,
    handle_receipt_category, handle_receipt_show
)
from handlers.commands.photos import (
    photos_command, _show_photos_batch, handle_photo_filter, handle_photo_page,
    handle_photo, handle_photo_stage, handle_photo_task, handle_photo_save
)
from handlers.commands.crm import (
    clients_command, deals_command, handle_crm_menu, _finalize_new_client
)
from handlers.commands.finance import (
    finance_command, add_expense_command, finance_keyboard,
    format_finance_summary, show_finance_summary, format_money
)
from handlers.commands.objects import (
    add_object_command, objects_command, objects_keyboard, object_detail_keyboard,
    choose_object_for_task_keyboard, choose_object_for_expense_keyboard,
    choose_object_for_expense_keyboard_amount
)
from handlers.commands.tasks import (
    add_task_command, format_tasks_block, tasks_command, done_command,
    handle_skip_photo, tasks_keyboard, tasks_keyboard_by_object,
    task_card_keyboard, task_date_keyboard, task_priority_keyboard,
    show_task_card, handle_task_action, build_calendar,
    auto_confirm_date, handle_confirm_date
)
from handlers.commands.choose_expense import (
    handle_choose_object, make_choose_keyboard,
    expense_category_keyboard, handle_category
)
from handlers.commands.document import handle_document
import sys as _sys
_sys.modules[__name__].__dict__.update(_legacy.__dict__)
