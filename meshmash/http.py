from typing import Any, Dict, Optional, Tuple, Union

from flask import Flask, Request, g, request

from .manager import Config, Manager, Node

app = Flask(__name__)


@app.route("/allocation", methods=["GET"])
def allocation() -> Union[Tuple[str, int], Dict[str, Any]]:
    """
    Get a new allocation token, such as for allocating a new node.
    """
    manager = get_manager()
    psk = header_token(request)
    if manager.psk_is_valid(psk):
        return {"alloc_token": manager.create_token().value}
    else:
        return "Not authorized", 403


@app.route("/register", methods=["POST"])
def register() -> Union[Tuple[str, int], Dict[str, Any]]:
    """
    Register a new node into the network
    """
    manager = get_manager()
    token = header_token(request)

    if not manager.token_is_valid(token):
        return "Not authorized", 403

    for field in ("hostname", "public_ip", "public_key"):
        if field not in request.form:
            return f"Missing field: {field}", 400

    node = Node(**request.form)
    private_ip = manager.register_node(node)
    manager.invalidate_token(token)
    return {"private_ip": private_ip}


@app.route("/config", methods=["GET"])
def config() -> Union[Tuple[str, int], str]:
    """
    Returns the Wireguard config with all of the nodes that have been registered
    """
    manager = get_manager()
    pubkey = header_token(request)

    if not manager.pubkey_is_valid(pubkey):
        return "Not authorized", 403

    peer_config = ""
    for node in manager.nodes.values():
        peer_config += "[Peer]\n"
        peer_config += f"# Host: {node.hostname}\n"
        peer_config += f"PublicKey = {node.public_key}\n"
        peer_config += f"AllowedIPs = {node.public_ip}/32\n"
        peer_config += f"Endpoint = {node.public_ip}:51280\n\n"

    return peer_config


def header_token(request: Request) -> Optional[str]:
    """
    Get the token from a request.headers object
    """
    token = None

    value = request.headers.get("Authorization", "")
    if value.startswith("Bearer "):
        token = value.replace("Bearer ", "")
    return token


def get_manager() -> Manager:
    # TODO: get YAML path from config var
    if "manager" not in g:
        app.logger.info("creating Manager")
        g.manager = Manager(Config.from_env())
        g.manager.load_state()
    assert isinstance(g.manager, Manager)
    return g.manager


@app.teardown_appcontext
def teardown_manager(*args: Any) -> None:
    app.logger.info("Tearing down manager")
    manager = g.pop("manager", None)
    if manager is not None:
        manager.save_state()
