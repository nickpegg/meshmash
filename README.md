# Meshmash - A Wireguard mesh network manager

This is a simple web API which keeps track of nodes in a Wireguard mesh. Nodes can
register themselves and retreive the Wireguard config with all of the nodes as peers.

## Flow
1. An operator, with a pre-shared key, makes a request to `/allocation` which returns a
   new allocation token.
2. During node provisioning, the allocation token is injected into the node being
   provisioned
3. The configuration management system installs Wireguard and generates a keypair
4. The configuration management system reads this allocation token and makes a request
   to `/register` with its hostname, public IP, and public key. The API allocates a
   private VPN IP address and returns that in the response to this call.
5. The configuration management system configures a `wg0` interface with this private
   IP and creates a `[Interface]` configuration file (with ListenPort and PrivateKey)
6. The configuration management system, using the Wireguard public key as auth, makes a
   request to `/config` to get the config with the `[Peer]` config sections and stores
   that on disk.
