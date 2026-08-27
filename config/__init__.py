"""Backward-compatible facade for TRION configuration domains.

New code should import directly from the responsibility-specific subpackage.
"""

from config.autonomy import *  # noqa: F401,F403
from config.context import *  # noqa: F401,F403
from config.digest import *  # noqa: F401,F403
from config.features import *  # noqa: F401,F403
from config.infra import *  # noqa: F401,F403
from config.models import *  # noqa: F401,F403
from config.output import *  # noqa: F401,F403
from config.pipeline import *  # noqa: F401,F403
from config.skills import *  # noqa: F401,F403
