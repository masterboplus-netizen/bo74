"""handlers.commands — пакет. Реэкспорт из _legacy."""
from handlers.commands import _legacy
import sys as _sys
_sys.modules[__name__].__dict__.update(_legacy.__dict__)
