from foundation.Bid import Bid
from foundation.ChannelClockServer import Channel_ClockServer
from foundation.ChannelMarketplace import Channel_Marketplace
from foundation.FoundationException import FoundationException
from foundation.Message import Message
from foundation.Service import Service
from multiprocessing import Process
import random
import agent_properties
import asyncore
import logging
import matplotlib.pyplot as plt
import re
import socket
import SocketServer
import threading
import time
import uuid
import xml.dom.minidom


#Explanation of the variables being used.
#
#Bid Usage is a dictionary with the following structure:
#    
#    { Key : Bid Id, Value Period Dictionary }
#    
#    Period Dictionary {Key: Period, Bid Usage Dictionary }
#    
#      Bid Usage Dictionary { key: Bid Id , quantity }. In this case the bid id
#                                                       can be a own bid id or a related 
#                                                       competitor bid.
#
#Related Bids is a dictionary with th list of bids (definitions) from other compatitors
#    {Key : competitor bid Id, competitor bid}


logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)s',
                    )

class AgentServerHandler(asyncore.dispatcher_with_send):
    '''
    The AgentServerHandler class implements methods to deal with the 
    agents basic operations.
    '''

    IDLE = 0
    BID_PERMITED = 2
    TO_BE_ACTIVED = 3
    ACTIVATE = 4
    TERMINATE = 5

    def __init__(self, addr, sock, list_args, strings_received):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self._list_args = list_args
        self._addr_orig = addr
        self._sock_orig = sock
        self._strings_received = strings_received
    
    def end_period_process(self, message):
        pass

    def start_period_process(self, message):
        pass
    
    '''
    This method activates the agent with all its parameters.
    '''
    def activate(self, message):
        logging.debug('Activating the consumer: %s', 
                             str(self._list_args['Id']) )
        if (self._list_args['Type'] == Agent.CONSUMER_TYPE):
            parameters = {}
            serviceId = message.getParameter("Service")
            quantityStr = message.getParameter("Quantity")    
            period = int(message.getParameter("Period"))
            parameters['service'] = serviceId
            parameters['quantity'] = float(quantityStr) 
                
            # set the state to be active.
            self._list_args['State'] = AgentServerHandler.TO_BE_ACTIVED
            self._list_args['Parameters'] = parameters
            self._list_args['Current_Period'] = period
        if (self._list_args['Type'] == Agent.PRESENTER_TYPE):
            logging.info('Activating the Presenter: %s - Period %s', 
                     str(self._list_args['Id']), 
                             str(self._list_args['Current_Period'])  )
            self._list_args['State'] = AgentServerHandler.ACTIVATE        

    '''
    This method transform the object into XML.
    '''
    def getText(self, nodelist):

        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)

    '''
    This method removes ilegal characters.
    '''
    def removeIlegalCharacters(self,xml):
        RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                    u'|' + \
                         u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                          (unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                           unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                           unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff))
        xml = re.sub(RE_XML_ILLEGAL, " ", xml)
        return xml

    '''
    This method addresses the offers from competitors.
    '''
    def handledCompetitorBid(self , bidCompetitor):
        logging.debug('Initiating handle Competitor Bid')
        idElement = bidCompetitor.getElementsByTagName("Id_C")[0]
        bid_competior_id = self.getText(idElement.childNodes)
        quantityElement = bidCompetitor.getElementsByTagName("Q_C")[0]
        quantity_competitor = float(self.getText(quantityElement.childNodes))
        return bid_competior_id, quantity_competitor

    '''
    This method handles the quantity of services sold by competitors,
    aiming to share the market.
    '''
    def handlePurchaseCompetitorBids(self, bidPair, bidCompetitors):
        logging.debug('Initiating handle Bid competitors')
        for bidCompetitor in bidCompetitors:
            bid_competior_id, quantity_competitor = self.handledCompetitorBid(bidCompetitor)
            if bid_competior_id in bidPair:
                bidPair[bid_competior_id] += quantity_competitor
            else:
                bidPair[bid_competior_id] = quantity_competitor
    

    '''
    This method checks if an offer was bought or not. If the offer
    was not bought, the method tries to equal the competitor offer.
    '''
    def handleBid(self,period, bidNode):
        logging.debug('Initiating handle Bid')
        idElement = bidNode.getElementsByTagName("Id")[0]
        bidId = self.getText(idElement.childNodes)
        quantityElement = bidNode.getElementsByTagName("Quantity")[0]
        quantity = float(self.getText(quantityElement.childNodes))
        bidCompetitors = bidNode.getElementsByTagName("Cmp_Bid")
        logging.debug('handled Bid - loaded Id and quantity')
        if (bidId in self._list_args['Bids_Usage']):
            logging.debug('handled Bid - Bid found in bid usage')
            if (period in (self._list_args['Bids_Usage'])[bidId]):
                logging.debug('handled Bid - period found')
                bidPair = ((self._list_args['Bids_Usage'])[bidId])[period] 
                if bidId in bidPair:
                    bidPair[bidId] += quantity
                else:
                    bidPair[bidId] = quantity
                self.handlePurchaseCompetitorBids( bidPair, bidCompetitors)
            else:
                logging.debug('handled Bid - period not found')
                bidPair = {}
                bidPair[bidId] = quantity
                self.handlePurchaseCompetitorBids( bidPair, bidCompetitors)
                ((self._list_args['Bids_Usage'])[bidId])[period] = bidPair
        else:
            logging.debug('handled Bid - Bid not found in bid usage')
            bidPair = {}
            bidPair[bidId] = quantity
            (self._list_args['Bids_Usage'])[bidId] = {}
            logging.debug('handled Bid - Bid not found in bid usage')
            self.handlePurchaseCompetitorBids( bidPair, bidCompetitors)
            logging.debug('handled Bid - Bid not found in bid usage')
            ((self._list_args['Bids_Usage'])[bidId])[period] = bidPair    

    '''
    This method handles the purchase orders sent from the marketplace
    once the offering period is open.
    '''
    def handleReceivePurchases(self,period, purchaseXmlNode):
        logging.debug('Initiating Receive Purchases')
        bids = purchaseXmlNode.getElementsByTagName("Bid")
        for bid in bids:
            self.handleBid(period, bid)
        logging.debug('Ending Receive Purchases')    
        #print  self._list_args['Bids_Usage']  
    

    '''
    This method gets all related competitors offerings and store
    in a list.
    '''
    def handleCompetitorBids(self, period, competitorsXmlNode):
        bids = competitorsXmlNode.getElementsByTagName("Bid")
        if (self._list_args['Type'] == Agent.PRESENTER_TYPE):
            logging.info('Handle competitor bids')
            self._list_args['Current_Bids'] = {}  
            logging.info('clear Handle competitor bids')
            
        logging.info('clear 2 Handle competitor bids')
        for bid in bids:
            logging.debug('We are inside the bid loop')
            competitor_bid = Bid()
            competitor_bid.setFromXmlNode(bid)
            if (competitor_bid.getProvider() != self._list_args['Id']):
                if (competitor_bid.getId() in self._list_args['Related_Bids']):
                    # The bid must be replaced as the provider update it.
                    (self._list_args['Related_Bids'])[competitor_bid.getId()] = competitor_bid
                else:
                    (self._list_args['Related_Bids'])[competitor_bid.getId()] = competitor_bid
                    logging.debug('Inserting competitor bid:' + competitor_bid.getId())
                
                # Inserts on exchanged bids
                if (self._list_args['Type'] == Agent.PRESENTER_TYPE):
                    (self._list_args['Current_Bids'])[competitor_bid.getId()] = competitor_bid
            
        if (self._list_args['Type'] == Agent.PRESENTER_TYPE):
            logging.info('End Handle competitor bids - num exchanged:' + 
                      str(len(self._list_args['Current_Bids'])))
        logging.info('clear 3 Handle competitor bids')
        logging.debug('Ending handled bid competitors for agent is:' + self._list_args['Id'])
    
    '''
    This method receives the offer information from competitors
    '''
    def receive_bid_information(self, message):
        logging.debug('Initiating Receive bid information')
        if ((self._list_args['Type'] == Agent.PROVIDER_TYPE) or 
             (self._list_args['Type'] == Agent.PRESENTER_TYPE)):
            period = int(message.getParameter("Period"))
            document = self.removeIlegalCharacters(message.getBody())
            try:
                dom = xml.dom.minidom.parseString(document)
                competitorsXmlNodes = dom.getElementsByTagName("New_Bids")
                for competitorsXmlNode in competitorsXmlNodes:
                    self.handleCompetitorBids(period, competitorsXmlNode)
                logging.debug('Competitor bids Loaded')
            except Exception as e: 
                raise FoundationException(str(e))

    '''
    This method receives purchase statistics from providers. For each 
    offer we receive its neigborhood offers.
    '''
    def receive_purchase_feedback(self, message):
        logging.debug('Initiating Receive Purchase feedback')
        if ((self._list_args['Type'] == Agent.PROVIDER_TYPE) or 
            (self._list_args['Type'] == Agent.PRESENTER_TYPE)):
            period = int(message.getParameter("Period"))
            self._list_args['Current_Period'] = period
            document = self.removeIlegalCharacters(message.getBody())
            #print document
            try:
                dom = xml.dom.minidom.parseString(document)
                # receive purchase statistics
                purchaseXmlNodes = dom.getElementsByTagName("Receive_Purchases")        
                for purchaseXmlNode in purchaseXmlNodes:
                    self.handleReceivePurchases(period, purchaseXmlNode)
                logging.debug('Purchase statistics Loaded')
                # After receiving the purchase information the provider can 
                # start to create new bids.
                if self._list_args['Type'] == Agent.PROVIDER_TYPE:
                    self._list_args['State'] = AgentServerHandler.BID_PERMITED    
                if self._list_args['Type'] == Agent.PRESENTER_TYPE:
                    logging.info('Receive Purchase feedback - Period: %s', 
                             str(self._list_args['Current_Period'] ))        
            except Exception as e: 
                raise FoundationException(str(e))
        

    '''
    This method terminates the agent processing state.
    '''
    def disconnect_process(self):
        self._list_args['State'] = AgentServerHandler.TERMINATE
        logging.debug('Terminate processing, the state is now in: %s', 
                     str(self._list_args['State']) )

    def process_getUnitaryCost(self, message):
        logging.debug('Initiating process GetUnitaryCost')
        bid = None
        if (self._list_args['Type'] == Agent.PROVIDER_TYPE):
            bidId = message.getParameter("BidId")
            if bidId in self._list_args['Bids']:
                bid = (self._list_args['Bids']).get(bidId)
            if bidId in self._list_args['Inactive_Bids']:
                bid = (self._list_args['Inactive_Bids']).get(bidId)
            if (bid is not None):
                unitary_cost = bid.getUnitaryCost()
                message = Message('')
                message.setMethod(Message.GET_UNITARY_COST)
                message.setMessageStatusOk()
                message.setParameter("UnitaryCost", str(unitary_cost))
            else:
                message = Message('')
                message.setMethod(Message.GET_UNITARY_COST)
                message.setParameter("Status_Code", "310")
                messageResponse.setParameter("Status_Description", "Bid is not from the provider")
        else:
            message = Message('')
            message.setMethod(Message.GET_UNITARY_COST)
            message.setParameter("Status_Code", "330")
            messageResponse.setParameter("Status_Description", "The agent is not a provider")
        self.send(message.__str__())
        logging.debug('Ending process GetUnitaryCost')

    '''
    This method returns the message parameters.
    '''
    def getMessage(self, string_key):
        foundIdx =  (self._strings_received[string_key]).find("Method")
        if (foundIdx == 0):
            foundIdx2 =  (self._strings_received[string_key]).find("Method", foundIdx + 1)
            if (foundIdx2 != -1):
                message = Message( (self._strings_received[string_key])[foundIdx : foundIdx2 - 1])
                # Even that the message could have errors is complete
                self._strings_received[string_key] = (self._strings_received[string_key])[foundIdx2 : ]
            else:
                message = Message((self._strings_received[string_key]))
                try:
                    isComplete = message.isComplete( len(self._strings_received[string_key]) )
                    if (isComplete):
                        (self._strings_received[string_key]) = ''
                    else:
                        message = None
                except FoundationException as e:
                    message = None
        else:
            if (len(self._strings_received[string_key]) == 0):
                message = None
            else:
                # The message is not well formed, so we create a message with method not specified
                message = Message('')
                message.setMethod(Message.UNDEFINED)
                (self._strings_received[string_key])[foundIdx : ]
        return message

    '''
    This method implements the message status, such as start and end
    period, disconnect, receive purchase and purchase feedback, and
    activate the consumer.
    '''
    def do_processing(self, message):
        if (message.getMethod() == Message.END_PERIOD):
             self.end_period_process(message)
        elif (message.getMethod() == Message.START_PERIOD):
             self.start_period_process(message)
        elif (message.getMethod() == Message.DISCONNECT):
             self.disconnect_process()
        elif (message.getMethod() == Message.RECEIVE_PURCHASE):
             self.receive_purchase(message)
        elif (message.getMethod() == Message.ACTIVATE_CONSUMER):
             self.activate(message)
        elif (message.getMethod() == Message.RECEIVE_BID_INFORMATION):
             self.receive_bid_information(message)
        elif (message.getMethod() == Message.RECEIVE_PURCHASE_FEEDBACK):
             self.receive_purchase_feedback(message)
        elif (message.getMethod() == Message.GET_UNITARY_COST):
             self.process_getUnitaryCost(message)
        elif (message.getMethod() == Message.ACTIVATE_PRESENTER):
             self.activate(message)
        else:
            logging.error('Message for parent %s with request method not handled: %s',
                  self._list_args['Id'], message.getStringMethod() )

            
    '''
    This method reads data from the socket until a complete 
    message is received
    '''
    def handle_read(self):
        # Reads data from the socket until a complete message is received
        string_key = repr(self._addr_orig) + repr(self._sock_orig)
        message = None
        data = self.recv(1024)
        self._strings_received[string_key] += data
        message = self.getMessage(string_key)
        while (message is not None):
            logging.debug('Message for parent %s message: %s',
                               self._list_args['Id'], message.__str__() )    
            self.do_processing(message)
            message = self.getMessage(string_key)

'''
The AgentServer class initializes the socket communication and 
handles the incoming connections.
'''
class AgentServer(asyncore.dispatcher):

    def __init__(self, list_args):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((list_args['Address'], list_args['Port']))
        self.listen(4)
        self._list_args = list_args
        self._strings_received = {}

    '''
    This method handles the acceptance of incoming socket connection.
    '''
    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            logging.debug('Incoming connection from %s', repr(addr))
            string_pair = repr(addr) + repr(sock)
            self._strings_received[string_pair] = ''
            handler = AgentServerHandler( addr, sock, self._list_args, self._strings_received)

'''
The class AgentListener defines the methods for listening the port.
'''
class AgentListener(threading.Thread):
    
    def __init__(self, list_args, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self._stop = threading.Event()
        logging.debug('initiating with %s and %s', args, kwargs)
        self._server = AgentServer(list_args)
        return
    
    '''
    This method starts listening the port.
    '''
    def run(self):
        asyncore.loop()
        return

    '''
    This method stops listening the port.
    '''
    def stop(self):
        self._stop.set()

    '''
    This method stops listening the port.
    '''
    def stopped(self):
        return self._stop.isSet()        

'''
The class Agent defines methods required for the operation of the 
consumer agent and service provider agent.
'''
class Agent(Process):

    CONSUMER_TYPE = "consumer"
    PROVIDER_ISP = "provider_isp"
    PROVIDER_BACKHAUL = "Provider_backhaul"
    PRESENTER_TYPE = "presenter"

    def __init__(self, strID, Id, agent_type, serviceId, agent_seed):
        Process.__init__(self)
        # state means: 0 can not create bids, 
        #              1 the process can create and ask for bids.
        #              2 disconnect
        logging.debug('Init agent %s', strID) 
        self._used_variables = {}
        self._list_vars = {}
        self._list_vars['Id'] = strID                                
        self._list_vars['Type'] = agent_type                   
        self._list_vars['Address'] = agent_properties.addr_agent
        self._list_vars['Current_Period'] = 0  
        randomGenerator = random.Random()
        randomGenerator.seed(agent_seed)
        self._list_vars['Random'] = randomGenerator
        if (agent_type == Agent.CONSUMER_TYPE):
            port = agent_properties.l_port_consumer + Id
            self._list_vars['Port'] = port
            self._list_vars['Parameters'] = {}
            self._list_vars['State'] = AgentServerHandler.IDLE         
        
        if ((agent_type == Agent.PROVIDER_ISP) or 
             (agent_type == Agent.PROVIDER_BACKHAUL) or
                 (agent_type == Agent.PRESENTER_TYPE)):
            self._list_vars['Inactive_Bids'] = {}     # Bids that are no more in use.
            self._list_vars['Bids'] = {}           # Bids in use.
            self._list_vars['Bids_Usage'] = {}
            self._list_vars['Related_Bids'] = {}      # for each bid of the provider lists
                              # competitor bids close it. (List)
        if ((agent_type == Agent.PROVIDER_ISP) or 
             (agent_type == Agent.PROVIDER_BACKHAUL)):
            port = agent_properties.l_port_provider + Id
            self._list_vars['Port'] = port
            self._list_vars['State'] = AgentServerHandler.BID_PERMITED
        
        if (agent_type == Agent.PRESENTER_TYPE):
            port = agent_properties.l_port_presenter + Id
            self._list_vars['Port'] = port
            self._list_vars['State'] = AgentServerHandler.IDLE 
            self._list_vars['Current_Bids'] = {}
        logging.info('Agent created with arguments %s', self._list_vars) 
        try:
            # Connect to servers.            
            self.connect_servers(agent_type)
            # Request the definition of the service
            connect = Message("")
            connect.setMethod(Message.GET_SERVICES)
            connect.setParameter("Service",serviceId)
            response = (self._channelClockServer).sendMessage(connect)
            if (response.isMessageStatusOk() ):
                self._service = self.handleGetService(response.getBody())
                logging.debug('service:' + self._service.__str__())
                logging.debug('init consumer- finish service retrieve')
        
        except FoundationException as e:
            raise FoundationException(e.__str__())

    ''' 
    This function connects the agent to servers ( clock server and markets places)
    '''
    def connect_servers(self, agent_type):
        if (agent_type == Agent.PROVIDER_ISP):
            port = agent_properties.mkt_place_listening_port
            address = agent_properties.addr_mktplace_isp
            # This will be the channel to put bids.                
            self._channelMarketPlace = Channel_Marketplace(address, port)
            address = agent_properties.addr_mktplace_backhaul
            # This will be the channel to buy resources.
            self._channelMarketPlaceBuy = Channel_Marketplace()
        else:
            port = agent_properties.mkt_place_listening_port
            address = agent_properties.addr_mktplace_isp                
            self._channelMarketPlace = Channel_Marketplace(address, port)
        self._channelClockServer = Channel_ClockServer()
            
        # Send the Connect message to ClockServer
        connect = Message("")
        connect.setMethod(Message.CONNECT)
        connect.setParameter("Provider",strID)
        response1 = (self._channelClockServer).sendMessage(connect)
            
        # Send the Connect message to MarketPlace 
        if (agent_type == Agent.PROVIDER_ISP):
            response2 = (self._channelMarketPlace).sendMessage(connect)
            if (response1.isMessageStatusOk() and response2.isMessageStatusOk() ):
                response3 = (self._channelMarketPlaceBuy).sendMessage(connect)
                if (response3.isMessageStatusOk() ):
                    logging.debug('We could connect to servers')
                else:
                    raise FoundationException("It could not connect to servers")
            else:
                logging.error('The agent could not connect to servers')
                raise FoundationException("It could not connect to servers")
        else:
            response2 = (self._channelMarketPlace).sendMessage(connect)
            if ( response1.isMessageStatusOk() and response2.isMessageStatusOk() ):
                logging.debug('We could connect to both servers')
            else:
                logging.error('The agent could not connect to servers')
                raise FoundationException("It could not connect to servers")
        

    '''
    This method creates the server for listening messages from 
    the demand server or the marketplace server.
    '''
    def start_listening(self):
        self._server = AgentListener(self._list_vars)
        self._server.start()
        port = self._list_vars['Port']
        logging.debug('Announcing port %s to servers', str(port))
        port_message = Message("")
        port_message.setMethod(Message.SEND_PORT)
        port_message.setParameter("Port", str(port))
        logging.debug('Announcing type %s to servers', self._list_vars['Type'])
        port_message.setParameter("Type", self._list_vars['Type'])
        response3 = (self._channelClockServer).sendMessage(port_message)
        response4 = (self._channelMarketPlace).sendMessage(port_message)
        if (response3.isMessageStatusOk() 
            and response4.isMessageStatusOk() ):
            logging.info('Servers connected')
        else:
            logging.error('One of the servers could not establish the connection')


    '''
    This method removes ilegal characters from the XML messages.
    '''
    def removeIlegalCharacters(self,xml):
            RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                    u'|' + \
                         u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                          (unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                           unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                           unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff))
            xml = re.sub(RE_XML_ILLEGAL, " ", xml)
            return xml

    '''
    This method handles the GetService function. It checks if the 
    server has sent more than one message.
    '''
    def handleGetService(self, document):
        logging.debug('Starting get service handler')
        document = self.removeIlegalCharacters(document)
        try:
            dom = xml.dom.minidom.parseString(document)
            servicesXml = dom.getElementsByTagName("Service")
            if (len(servicesXml) > 1):
                raise FoundationException("The server sent more than one service")
            else:
                service = Service()
                for servicexml in servicesXml:
                    service.setFromXmlNode(servicexml)
                logging.debug('Ending get service handler')
                return service
        except Exception as e:
            raise FoundationException(str(e))
    

    '''
    This method handles the GetServices function. It removes ilegal
    characters and get the service statement.
    '''
    def handleGetServices(self, document):
        document = self.removeIlegalCharacters(document)
        try:
            dom = xml.dom.minidom.parseString(document)
            servicesXml = dom.getElementsByTagName("Service")
            services = {}
            for servicexml in servicesXml:
                service = Service()
                service.setFromXmlNode(servicexml)
                services[service.getId()] = service
            return services
        except Exception as e: 
            raise FoundationException(str(e))


    '''
    This method returns the available services.
    '''
    def getServices(self):
        messageAsk = Message('')
        messageAsk.setMethod(Message.GET_SERVICES)
        messageResult = self._channelClockServer.sendMessage(messageAsk)
        if messageResult.isMessageStatusOk():
            return self.handleGetServices(messageResult.getBody())
        else:
            raise FoundationException('Services not received! Communication failed')

    '''
    This method handles the best offers on the Pareto Front.
    '''
    def handleBestBids(self, docum):
        logging.debug('Starting handleBestBids')
        fronts = docum.getElementsByTagName("Front")
        val_return = self.handleFronts(fronts)
        logging.debug('Ending handleBestBids')
        return val_return

    '''
    This method handles the Pareto Fronts.
    '''
    def handleFronts(self, fronts):
        logging.debug('Starting handleFronts')
        dic_return = {}
        for front in fronts:
            parNbrElement = front.getElementsByTagName("Pareto_Number")[0]
            parNbr = int((parNbrElement.childNodes[0]).data)
            dic_return[parNbr] = self.handleFront(front)
        logging.debug('Ending handleFronts')
        return dic_return

    '''
    This method handles the Pareto Front of offerings.
    '''
    def handleFront(self, front):
        logging.debug('Starting handleFront')
        val_return = []
        bidXmLNodes = front.getElementsByTagName("Bid")
        for bidXmlNode in bidXmLNodes:
            bid = Bid()
            bid.setFromXmlNode(bidXmlNode)
            val_return.append(bid)
        logging.debug('Ending handleFront' + str(len(val_return)))
        return val_return
         
    '''
    This method creates the query for the Marketplace asking 
    other providers' offers.
    '''
    def createAskBids(self, serviceId):
        messageAsk = Message('')
        messageAsk.setMethod(Message.GET_BEST_BIDS)
        messageAsk.setParameter('Provider', self._list_vars['Id'])
        messageAsk.setParameter('Service', serviceId)
        messageResult = self._channelMarketPlace.sendMessage(messageAsk)
        if messageResult.isMessageStatusOk():
            #print 'Best bids' + messageResult.__str__()
            document = self.removeIlegalCharacters(messageResult.getBody())
            try:
                dom = xml.dom.minidom.parseString(document)
                return self.handleBestBids(dom)
            except Exception as e: 
                raise FoundationException(str(e))
        else:
            raise FoundationException("Best bids not received")
            

# End of Agent class
