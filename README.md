# Meshmash - A Wireguard mesh network manager

This is a simple web API which keeps track of nodes in a Wireguard mesh. Nodes
can register themselves and retreive the Wireguard config with all of the nodes
as peers.

## Flow
1. An operator, with a pre-shared key, makes a request to `/allocation` which
   returns a new allocation token.
2. During node provisioning, the allocation token is injected into the node
   being provisioned
3. The configuration management system running on the new node installs
   Wireguard and generates a keypair.
4. The configuration management system reads the allocation token and makes a
   request to `/register` with its hostname, public IP, and public key. The API
   allocates and returns a private VPN IP address.
5. The configuration management system configures a `wg0` interface with this
   private IP and creates a configuration file with a Wireguard `[Interface]`
   configuration section (with ListenPort and PrivateKey).
6. The configuration management system, using the Wireguard public key as auth,
   makes a request to `/config` to get the config with the `[Peer]` config
   sections and stores that on disk.
