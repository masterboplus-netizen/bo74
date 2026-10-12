"""handlers.commands — пакет."""
from handlers.commands import _legacy
from handlers.commands.start import start, help_command
from handlers.commands.personal import personal_command, format_personal_summary, personal_keyboard
import sys as _sys
_sys.modules[__name__].__dict__.update(_legacy.__dict__)
