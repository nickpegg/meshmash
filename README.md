# Meshmash - A Wireguard mesh network manager

This is a simple web service which keeps track of nodes in a Wireguard mesh.
Nodes can register themselves and retreive the Wireguard config with all of the
nodes as peers.

Warning: This is for my personal use and hasn't been battle-tested in a
production enviornment.

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

## Caveats
Authenticating to `/config` with a public key like this is pretty weak.  This
is really only to stop drive-by people from reading your peer config and
learning your network topology. If you have access to one of these public keys,
you're likely already trusted to be on the network.

The persistence for Meshmash is currently a JSON file on disk, which makes it
hard to run it in a highly-available way. When the complexity is warranted,
meaning I don't want Chef runs to fail if Meshmash is down, I'll add
persistence to some data store (database? Consul? etcd?).
