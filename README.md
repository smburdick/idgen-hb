# idgen-hb
## System design
The system comprises 3 processes: a client, a primary server, and a heartbeat (backup) server).
* Primary: generates a ID and returns it upon request, and saves that ID to a file.
* Heartbeat: periodically send messages to the primary server. If it times out, it will assume its responsibilities (send IDs starting from last written one)
* Client: Will ping the primary node for an ID, and will ping the hearbeat node if the request times out (and switch to heartbeat node for future requests)

## Notes
* The first time the heartbeat node recieves a `getID()` request, it will ensure that the primary node is dead -- if it's not, it will return an error. If it is, it will read the last sent ID from the file, increment, and return it to the user.

* The primary process should terminate itself after a random amount of time.
