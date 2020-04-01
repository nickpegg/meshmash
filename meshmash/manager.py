import json
import logging
import os
import shutil
from dataclasses import asdict, dataclass, field
from ipaddress import ip_network
from secrets import token_urlsafe
from threading import Lock
from time import time
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


TOKEN_LIFETIME_MIN = 30
MANAGER_LOCK = Lock()


@dataclass
class Config:
    # Pre-shared key, operators use this when cutting allocation tokens
    psk: str

    # Private IP subnet to allocate VPN IPs from, e.g. "10.0.0.0/24"
    subnet: str

    # Path to the state file. This should be protected and only writablle by the service
    state_path: str

    @classmethod
    def from_yaml(cls, filename: str) -> "Config":
        conf = yaml.safe_load(open(filename))
        if conf is None:
            raise RuntimeError(f"Config at {filename} is empty")
        return cls(**conf)

    @classmethod
    def from_env(cls) -> "Config":
        """
        Build a config object from environment variables
        """
        for key in ("psk", "subnet", "state_path"):
            env_var = f"MESHMASH_{key.upper()}"
            if env_var not in os.environ:
                raise RuntimeError(f"Missing environment var: {env_var}")

        return cls(
            psk=os.environ["MESHMASH_PSK"],
            subnet=os.environ["MESHMASH_SUBNET"],
            state_path=os.environ["MESHMASH_STATE_PATH"],
        )


@dataclass
class Token:
    value: str = field(default_factory=token_urlsafe)
    expiry_ts: float = field(default_factory=lambda: time() + 60 * TOKEN_LIFETIME_MIN)

    def is_valid(self) -> bool:
        return time() < self.expiry_ts


@dataclass
class Node:
    hostname: str
    public_ip: str
    public_key: str
    private_ip: str = ""


@dataclass
class Manager:
    config: Config
    tokens: List[Token] = field(default_factory=list)
    nodes: Dict[str, Node] = field(default_factory=dict)

    def load_state(self) -> None:
        logger.info(f"Loading state from {self.config.state_path}")
        with MANAGER_LOCK:
            if os.path.exists(self.config.state_path):
                state = json.load(open(self.config.state_path))
                logger.debug(f"got state: {state}")
                for token in state.get("alloc_tokens", []):
                    if time() < token["expiry_ts"]:
                        self.tokens.append(Token(**token))
                    else:
                        logger.info(f"Ignoring stale token {token['value']}")

                for node_dict in state.get("nodes", []):
                    node = Node(**node_dict)
                    self.nodes[node.hostname] = node

    def save_state(self) -> None:
        logger.info(f"Saving state to {self.config.state_path}")
        bkup_file = self.config.state_path + ".bkup"
        do_backup = os.path.exists(self.config.state_path)

        with MANAGER_LOCK:
            if do_backup:
                shutil.copyfile(self.config.state_path, bkup_file)
            try:
                state = {
                    "alloc_tokens": [],
                    "nodes": [],
                }  # type: Dict[str, List[Any]]
                for token in self.tokens:
                    state["alloc_tokens"].append(asdict(token))
                for node in self.nodes.values():
                    state["nodes"].append(asdict(node))

                with open(self.config.state_path, "w") as f:
                    f.write(json.dumps(state))
            except:
                # Restore the backup and re-raise the exception
                if do_backup:
                    os.rename(bkup_file, self.config.state_path)
                raise

    def psk_is_valid(self, psk: Optional[str]) -> bool:
        return bool(psk and psk == self.config.psk)

    def create_token(self) -> Token:
        with MANAGER_LOCK:
            token = Token()
            self.tokens.append(token)
        self.save_state()
        return token

    def token_is_valid(self, token_value: Optional[str]) -> bool:
        for token in self.tokens:
            if token_value and token.value == token_value and token.is_valid():
                return True
        return False

    def pubkey_is_valid(self, pubkey: Optional[str]) -> bool:
        for node in self.nodes.values():
            if node.public_key == pubkey:
                return True
        return False

    def invalidate_token(self, token_value: Optional[str]) -> None:
        token = None
        for t in self.tokens:
            if t.value == token_value:
                token = t

        if token:
            self.tokens.remove(token)

    def register_node(self, node: Node) -> str:
        """
        Register a node and allocate it a private IP address. Returns the allocated IP.
        """
        if node.hostname in self.nodes:
            return self.nodes[node.hostname].private_ip

        node.private_ip = self.next_available_ip()
        self.nodes[node.hostname] = node

        return node.private_ip

    def next_available_ip(self) -> str:
        """
        Get the next available private IP
        """
        node_addrs = {node.private_ip for node in self.nodes.values()}
        network = ip_network(self.config.subnet)
        host_addrs = network.hosts()

        # skip the first address, reserved for a gateway maybe
        next(host_addrs)

        for candidate_addr in host_addrs:
            if str(candidate_addr) not in node_addrs:
                return str(candidate_addr)

        # If we get here, we've exhausted our subnet
        raise RuntimeError(f"Subnet {self.config.subnet} exhausted of free IPs")
