# pylint: disable=redefined-outer-name
# import shutil
# import subprocess
import time
from pathlib import Path
import pytest

# import redis
import requests

from tenacity import retry, stop_after_delay

from document import config

pytest.register_assert_rewrite("tests.e2e.api_client")


@retry(stop=stop_after_delay(10))
def wait_for_webapp_to_come_up():
    return requests.get(config.get_api_url())


# @retry(stop=stop_after_delay(10))
# def wait_for_redis_to_come_up():
#     r = redis.Redis(**config.get_redis_host_and_port())
#     return r.ping()


@pytest.fixture
def restart_api():
    (Path(__file__).parent / "../src/document/entrypoints/flask_app.py").touch()
    time.sleep(0.5)
    wait_for_webapp_to_come_up()


# @pytest.fixture
# def restart_redis_pubsub():
#     wait_for_redis_to_come_up()
#     if not shutil.which("docker-compose"):
#         print("skipping restart, assumes running in container")
#         return
#     subprocess.run(
#         ["docker-compose", "restart", "-t", "0", "redis_pubsub"], check=True,
#     )