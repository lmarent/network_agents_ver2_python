import SocketServer
import sys
sys.path.append("/home/network_agents_ver2_python/agents/foundation")
import agent_properties

class MyTCPHandler(SocketServer.BaseRequestHandler):
    """
The RequestHandler class for our server.

It is instantiated once per connection to the server, and must
override the handle() method to implement communication to the
client.
"""

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(16666).strip()
        print "{} wrote:".format(self.client_address[0])
        print self.data
        # just send back the same data, but upper-cased
        #self.request.sendall(self.data.upper())

if __name__ == "__main__":
    print 'Number of arguments:', len(sys.argv), 'arguments.'
    print 'Argument List:', str(sys.argv)
    if (len(sys.argv) == 3):
        HOST = sys.argv[1]
        PORT = int(sys.argv[2])
    else:
    	print 'Host:', agent_properties.addr_agent_mktplace_isp, ' port:', agent_properties.l_port_provider
        HOST, PORT = agent_properties.addr_agent_mktplace_isp, agent_properties.l_port_provider

    # Create the server, binding to localhost on port 9999
    server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
