import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

import app


def test_db_connection_wrapper_uses_env_defaults():
    wrapper = app.MSSQLConnectionWrapper()
    assert wrapper is not None
