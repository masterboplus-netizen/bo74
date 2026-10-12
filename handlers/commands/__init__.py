"""handlers.commands — пакет."""
from handlers.commands import _legacy
from handlers.commands.start import start, help_command
from handlers.commands.personal import personal_command, format_personal_summary, personal_keyboard
from handlers.commands.receipt import (
    handle_recognize_receipt, handle_receipt_save, handle_receipt_object,
    handle_receipt_category, handle_receipt_show
)
import sys as _sys
_sys.modules[__name__].__dict__.update(_legacy.__dict__)
