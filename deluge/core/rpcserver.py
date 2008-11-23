#
# rpcserver.py
#
# Copyright (C) 2008 Andrew Resch <andrewresch@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA    02110-1301, USA.
#


import gobject

import deluge.SimpleXMLRPCServer as SimpleXMLRPCServer
from SocketServer import ThreadingMixIn

from deluge.log import LOG as log
import deluge.component as component
import deluge.configmanager

def export(func):
    func._rpcserver_export = True
    return func

class RPCServer(ThreadingMixIn, SimpleXMLRPCServer.SimpleXMLRPCServer, component.Component):
    def __init__(self, port):
        component.Component.__init__(self, "RPCServer")

        # Get config
        self.config = deluge.configmanager.ConfigManager("core.conf")

        if port == None:
            port = self.config["daemon_port"]

        if self.config["allow_remote"]:
            hostname = ""
        else:
            hostname = "localhost"

        # Setup the xmlrpc server
        try:
            log.info("Starting XMLRPC server on port %s", port)
            SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(
                self, (hostname, port), logRequests=False, allow_none=True)
        except:
            log.info("Daemon already running or port not available..")
            sys.exit(0)

        self.register_multicall_functions()
        self.register_introspection_functions()

        self.socket.setblocking(False)

        gobject.io_add_watch(self.socket.fileno(), gobject.IO_IN | gobject.IO_OUT | gobject.IO_PRI | gobject.IO_ERR | gobject.IO_HUP, self._on_socket_activity)

    def _on_socket_activity(self, source, condition):
        """This gets called when there is activity on the socket, ie, data to read
        or to write."""
        self.handle_request()
        return True

    def register_object(self, obj, name=None):
        if not name:
            name = obj.__class__.__name__

        for d in dir(obj):
            if d[0] == "_":
                continue
            if getattr(getattr(obj, d), '_rpcserver_export', False):
                log.debug("Registering method: %s", name + "." + d)
                self.register_function(getattr(obj, d), name + "." + d)

    def get_request(self):
        """Get the request and client address from the socket.
            We override this so that we can get the ip address of the client.
        """
        request, client_address = self.socket.accept()
        self.client_address = client_address[0]
        return (request, client_address)
