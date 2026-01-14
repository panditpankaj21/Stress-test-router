import os
from lib.router_ssh_manager import RouterSSHManager


def create_router_ssh():
    return RouterSSHManager(
        host=os.getenv("HOST"),
        username=os.getenv("USERNAME"),
        password=os.getenv("PASSWORD"),
        timeout=int(os.getenv("SSH_TIMEOUT", 10)),
    )
