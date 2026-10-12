"""handlers.commands — пакет. Реэкспорт из _legacy + start."""
from handlers.commands import _legacy
from handlers.commands.start import start, help_command
import sys as _sys
_sys.modules[__name__].__dict__.update(_legacy.__dict__)
