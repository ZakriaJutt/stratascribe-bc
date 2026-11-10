"""``python -m api``: serve on API_PORT (8106 locally)."""

import uvicorn

from api.app import create_app
from core import config
from core import logging as clog

clog.configure()
uvicorn.run(create_app(), host="127.0.0.1", port=config.settings().api_port, log_config=None, access_log=False)
