"""Registry of all model modules (used by Alembic ``env.py`` and tests).

When you create ``src/<domain>/models.py`` - add one import line here,
otherwise Alembic will not see your tables.
"""

import src.movies.models  # noqa: F401
import src.accounts.models  # noqa: F401       (P2)
import src.interactions.models  # noqa: F401   (P5)
import src.cart.models  # noqa: F401         (P6)
import src.orders.models  # noqa: F401       (P6)

# import src.payments.models  # noqa: F401     (P7)
import src.notifications.models  # noqa: F401  (P3)
