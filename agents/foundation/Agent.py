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


logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-10s) %(message)s',
                    )
logger = logging.getLogger('agent')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('agent_logs.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


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
        logger.debug('Activating the consumer: %s', str(self._list_args['Id']) )
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
            logger.info('Activating the Presenter: %s - Period %s', 
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
        logger.debug('Initiating handle Competitor Bid')
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
        logger.debug('Initiating handle Bid competitors')
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
        logger.debug('Initiating handle Bid')
        idElement = bidNode.getElementsByTagName("Id")[0]
        bidId = self.getText(idElement.childNodes)
        quantityElement = bidNode.getElementsByTagName("Quantity")[0]
        quantity = float(self.getText(quantityElement.childNodes))
        bidCompetitors = bidNode.getElementsByTagName("Cmp_Bid")
        logger.debug('handled Bid - loaded Id and quantity')
        if (bidId in self._list_args['Bids_Usage']):
            logger.debug('handled Bid - Bid found in bid usage')
            if (period in (self._list_args['Bids_Usage'])[bidId]):
                logger.debug('handled Bid - period found')
                bidPair = ((self._list_args['Bids_Usage'])[bidId])[period] 
                if bidId in bidPair:
                    bidPair[bidId] += quantity
                else:
                    bidPair[bidId] = quantity
                self.handlePurchaseCompetitorBids( bidPair, bidCompetitors)
            else:
                logger.debug('handled Bid - period not found')
                bidPair = {}
                bidPair[bidId] = quantity
                self.handlePurchaseCompetitorBids( bidPair, bidCompetitors)
                ((self._list_args['Bids_Usage'])[bidId])[period] = bidPair
        else:
            logger.debug('handled Bid - Bid not found in bid usage')
            bidPair = {}
            bidPair[bidId] = quantity
            (self._list_args['Bids_Usage'])[bidId] = {}
            logger.debug('handled Bid - Bid not found in bid usage')
            self.handlePurchaseCompetitorBids( bidPair, bidCompetitors)
            logger.debug('handled Bid - Bid not found in bid usage')
            ((self._list_args['Bids_Usage'])[bidId])[period] = bidPair    

    '''
    This method handles the purchase orders sent from the marketplace
    once the offering period is open.
    '''
    def handleReceivePurchases(self,period, purchaseXmlNode):
        logger.debug('Initiating Receive Purchases')
        bids = purchaseXmlNode.getElementsByTagName("Bid")
        for bid in bids:
            self.handleBid(period, bid)
        logger.debug('Ending Receive Purchases')    
        #print  self._list_args['Bids_Usage']  
    

    '''
    This method gets all related competitors offerings and store
    in a list.
    '''
    def handleCompetitorBids(self, period, competitorsXmlNode):
        bids = competitorsXmlNode.getElementsByTagName("Bid")
        try:
            if (self._list_args['Type'] == Agent.PRESENTER_TYPE):
                logger.info('Handle competitor bids')
                self._list_args['Current_Bids'] = {}  
                logger.info('clear Handle competitor bids')
                
            logger.info('clear 2 Handle competitor bids')
            for bid in bids:
                logger.debug('We are inside the bid loop')
                competitor_bid = Bid()
                competitor_bid.setFromXmlNode(bid)                
                if (competitor_bid.getProvider() != self._list_args['strId']):
                    if (competitor_bid.getService() == (self._list_args['serviceId'])):                        
                        if (competitor_bid.getId() in self._list_args['Related_Bids']):
                            # The bid must be replaced as the provider update it.
                            oldCompetitorBid = (self._list_args['Related_Bids'])[competitor_bid.getId()]
                            competitor_bid.setCreationPeriod(oldCompetitorBid.getCreationPeriod())  
                            (self._list_args['Related_Bids'])[competitor_bid.getId()] = competitor_bid
                        else:
                            if (competitor_bid.isActive() == True):
                                competitor_bid.setCreationPeriod(period)
                            (self._list_args['Related_Bids'])[competitor_bid.getId()] = competitor_bid
                            #logger.debug('Inserting competitor bid:' + competitor_bid.__str__())
                        
                        # Inserts on exchanged bids
                        if (self._list_args['Type'] == Agent.PRESENTER_TYPE):
                            (self._list_args['Current_Bids'])[competitor_bid.getId()] = competitor_bid
                                    
            if (self._list_args['Type'] == Agent.PRESENTER_TYPE):
                logger.info('End Handle competitor bids - num exchanged:' + str(len(self._list_args['Current_Bids'])))
            logger.info('clear 3 Handle competitor bids')
            logger.debug('Ending handled bid competitors for agent is:' + str(self._list_args['Id']))
        except Exception as e:
            raise FoundationException(str(e))
    
    '''
    This method receives the offer information from competitors
    '''
    def receive_bid_information(self, message):
        logger.debug('Initiating Receive bid information')
        if ((self._list_args['Type'] == Agent.PROVIDER_ISP) or (self._list_args['Type'] == Agent.PROVIDER_BACKHAUL) or (self._list_args['Type'] == Agent.PRESENTER_TYPE)):
            period = int(message.getParameter("Period"))
            document = self.removeIlegalCharacters(message.getBody())
            try:
                dom = xml.dom.minidom.parseString(document)
                competitorsXmlNodes = dom.getElementsByTagName("New_Bids")
                for competitorsXmlNode in competitorsXmlNodes:
                    self.handleCompetitorBids(period, competitorsXmlNode)
                logger.debug('Competitor bids Loaded')
            except Exception as e: 
                raise FoundationException(str(e))

    '''
    This method receives purchase statistics from providers. For each 
    offer we receive its neigborhood offers.
    '''
    def receive_purchase_feedback(self, message):
        logger.debug('Initiating Receive Purchase feedback')
        if ((self._list_args['Type'] == Agent.PROVIDER_ISP) or (self._list_args['Type'] == Agent.PROVIDER_BACKHAUL) or (self._list_args['Type'] == Agent.PRESENTER_TYPE)):
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
                # After receiving the purchase information the provider can 
                # start to create new bids.
                if ((self._list_args['Type'] == Agent.PROVIDER_ISP) or (self._list_args['Type'] == Agent.PROVIDER_BACKHAUL)):
                    self._list_args['State'] = AgentServerHandler.BID_PERMITED    
                if self._list_args['Type'] == Agent.PRESENTER_TYPE:
                    logger.info('Receive Purchase feedback - Period: %s', 
                             str(self._list_args['Current_Period'] ))        
                logger.debug('Purchase statistics Loaded')
            except Exception as e: 
                raise FoundationException(str(e))
        

    '''
    This method terminates the agent processing state.
    '''
    def disconnect_process(self):
        self._list_args['State'] = AgentServerHandler.TERMINATE
        logger.debug('Terminate processing, the state is now in: %s', 
                     str(self._list_args['State']) )

    def process_getUnitaryCost(self, message):
        logger.debug('Initiating process GetUnitaryCost')
        bid = None
        if ((self._list_args['Type'] == Agent.PROVIDER_ISP) or (self._list_args['Type'] == Agent.PROVIDER_BACKHAUL)):
            
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
        logger.debug('Ending process GetUnitaryCost')

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
            logger.error('Message for parent %s with request method not handled: %s',
                  self._list_args['Id'], message.getStringMethod() )

            
    '''
    This method reads data from the socket until a complete 
    message is received
    '''
    def handle_read(self):
        # Reads data from the socket until a complete message is received
        try:
            string_key = repr(self._addr_orig) + repr(self._sock_orig)
            message = None
            data = self.recv(1024)
            self._strings_received[string_key] += data
            message = self.getMessage(string_key)
            while (message is not None):
                logger.debug('Message for parent %s message: %s',self._list_args['Id'], message.__str__() )    
                self.do_processing(message)
                message = self.getMessage(string_key)
        except Exception as e:
            raise FoundationException("Error in reading the socket for agent:" + str(self._list_args['Id']) + 'read the data:' + data)

'''
The AgentServer class initializes the socket communication and 
handles the incoming connections.
'''
class AgentServer(asyncore.dispatcher):

    def __init__(self, list_args):
        logger.debug('starting AgentServer Id: %s address:%s port:%s', list_args['Id'], list_args['Address'], list_args['Port'])
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((list_args['Address'], list_args['Port']))
        self.listen(4)
        self._list_args = list_args
        self._strings_received = {}
        logger.debug('starting AgentServer Id: %s address:%s port:%s', list_args['Id'], list_args['Address'], list_args['Port'])

    '''
    This method handles the acceptance of incoming socket connection.
    '''
    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            logger.debug('handle Accept Id: %s address:%s port:%s', self._list_args['Id'], self._list_args['Address'], self._list_args['Port'])
            sock, addr = pair
            logger.debug('Incoming connection from %s', repr(addr))
            string_pair = repr(addr) + repr(sock)
            self._strings_received[string_pair] = ''
            handler = AgentServerHandler( addr, sock, self._list_args, self._strings_received)
            logger.debug('Ending handle Accept Id: %s address:%s port:%s', self._list_args['Id'], self._list_args['Address'], self._list_args['Port'])

'''
The class AgentListener defines the methods for listening the port.
'''
class AgentListener(threading.Thread):
    
    def __init__(self, list_args, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self._stop = threading.Event()
        logger.debug('initiating with %s and %s', list_args, kwargs)
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
    PROVIDER_BACKHAUL = "provider_backhaul"
    PRESENTER_TYPE = "presenter"

    def __init__(self, strID, Id, agent_type, serviceId, agent_seed, sellingAddress, buyingAddress, capacityControl):
        Process.__init__(self)
        # state means: 0 can not create bids, 
        #              1 the process can create and ask for bids.
        #              2 disconnect
        logger.debug('Init agent %s', strID) 
        self._used_variables = {}
        self._list_vars = {}
        self._list_vars['Id'] = Id
        self._list_vars['strId'] = strID
        self._list_vars['Type'] = agent_type
        self._list_vars['Address'] = agent_properties.addr_agent
        self._list_vars['Current_Period'] = 0  
        self._list_vars['serviceId'] = serviceId
        self._list_vars['capacityControl'] = capacityControl
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
        logger.info('Agent created with arguments %s', self._list_vars) 
        try:
            # Connect to servers.            
            self.connect_servers(agent_type, strID, sellingAddress, buyingAddress, capacityControl)
            # Request the definition of the service
            connect = Message("")
            connect.setMethod(Message.GET_SERVICES)
            connect.setParameter("Service",serviceId)
            response = (self._channelClockServer).sendMessage(connect)
            if (response.isMessageStatusOk() ):
                self._service = self.handleGetService(response.getBody())
                self._services = {}
                self._services[serviceId] = self.handleGetService(response.getBody())
                logger.debug('service:' + self._service.__str__())
                logger.debug('init consumer- finish service retrieve')
        
        except FoundationException as e:
            raise FoundationException(e.__str__())

    ''' 
    This function connects the agent to servers ( clock server and markets places)
    '''
    def connect_servers(self, agent_type, strID, sellingAddress, buyingAddress, capacityControl):
        logger.debug('Starting connect servers agent %s', strID) 
        if (agent_type == Agent.PROVIDER_ISP):
            port = agent_properties.mkt_place_listening_port
            address = sellingAddress
            # This will be the channel to put bids.                
            self._channelMarketPlace = Channel_Marketplace(address, port)
            address = buyingAddress
            # This will be the channel to buy resources.
            self._channelMarketPlaceBuy = Channel_Marketplace(address, port)
        elif (agent_type == Agent.PROVIDER_BACKHAUL):
            port = agent_properties.mkt_place_listening_port
            address = sellingAddress
            # This will be the channel to put bids.                
            self._channelMarketPlace = Channel_Marketplace(address, port)
        else:
            port = agent_properties.mkt_place_listening_port
            address = agent_properties.addr_mktplace_isp                
            self._channelMarketPlace = Channel_Marketplace(address, port)
        self._channelClockServer = Channel_ClockServer()
            
        # Send the Connect message to ClockServer
        connect = Message("")
        connect.setMethod(Message.CONNECT)
        connect.setParameter("Agent",strID)
        response1 = (self._channelClockServer).sendMessage(connect)
        if (response1.isMessageStatusOk() == False):
            raise FoundationException("Agent: It could not connect to clock server")
            
        # Send the Connect message to MarketPlace 
        if (agent_type == Agent.PROVIDER_ISP):
            response2 = (self._channelMarketPlace).sendMessage(connect)
            if (response2.isMessageStatusOk()):
                response3 = (self._channelMarketPlaceBuy).sendMessage(connect)
                if (response3.isMessageStatusOk() ):
                    logger.debug('We could connect to servers')
                else:
                    logger.error('Provider ISP: It could not connect to the market place to Buy')
                    raise FoundationException("Provider ISP: It could not connect to the market place to Buy")
            else:
                logger.error('Provider ISP: It could not connect to market place to sell')
                raise FoundationException("Provider ISP: It could not connect to market place to sell")
        else:
            response2 = (self._channelMarketPlace).sendMessage(connect)
            if ( response2.isMessageStatusOk() ):
                logger.debug('We could connect to both servers')
            else:
                logger.error('The agent could not connect to market place')
                raise FoundationException("Agent: It could not connect to market place")
        logger.debug('Ending connect servers agent %s', strID) 
        

    '''
    This method creates the server for listening messages from 
    the demand server or the marketplace server.
    '''
    def start_listening(self):
        logger.debug('Starting listening Id: %s', self._list_vars['Id']) 
        self._server = AgentListener(self._list_vars)
        self._server.start()
        port = self._list_vars['Port']
        logger.debug('Announcing port %s to servers', str(port))
        port_message = Message("")
        port_message.setMethod(Message.SEND_PORT)
        port_message.setParameter("Port", str(port))            
        logger.debug('Announcing type %s to servers', self._list_vars['Type'])
        if ((self._list_vars['Type'] == Agent.PROVIDER_ISP) or (self._list_vars['Type'] == Agent.PROVIDER_BACKHAUL)):
            port_message.setParameter("Type", "provider")
            capacityType = self._list_vars['capacityControl']
            if capacityType == 'B':
                port_message.setParameter("CapacityType","bid")
            else:
                port_message.setParameter("CapacityType","bulk")
        else:
            port_message.setParameter("Type", self._list_vars['Type'])
        response3 = (self._channelClockServer).sendMessage(port_message)
        response4 = (self._channelMarketPlace).sendMessage(port_message)
        if (response3.isMessageStatusOk() 
            and response4.isMessageStatusOk() ):
            logger.info('Servers connected')
        else:
            logger.error('One of the servers could not establish the connection')
        logger.debug('Ending listening Id: %s', self._list_vars['Id'])


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
        logger.debug('Starting get service handler Id:%s', self._list_vars['Id'])
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
                logger.debug('Ending get service handler')
                return service
        except Exception as e:
            raise FoundationException(str(e))
        logger.debug('Ending get service handler Id:%s', self._list_vars['Id'])
    

    '''
    This method handles the GetServices function. It removes ilegal
    characters and get the service statement.
    '''
    def handleGetServices(self, document):
        logger.debug('Starting get service Id:%s', self._list_vars['Id'])
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
        logger.debug('Ending get service Id:%s', self._list_vars['Id'])

    '''
    This method returns the available services.
    '''
    def getServices(self):
        logger.debug('Starting get services Id:%s', self._list_vars['Id'])
        messageAsk = Message('')
        messageAsk.setMethod(Message.GET_SERVICES)
        messageResult = self._channelClockServer.sendMessage(messageAsk)
        if messageResult.isMessageStatusOk():
            return self.handleGetServices(messageResult.getBody())
        else:
            raise FoundationException('Services not received! Communication failed')
        logger.debug('Ending get services Id:%s', self._list_vars['Id'])

    '''
    This method handles the best offers on the Pareto Front.
    '''
    def handleBestBids(self, docum):
        logger.debug('Starting handleBestBids')
        fronts = docum.getElementsByTagName("Front")
        val_return = self.handleFronts(fronts)
        logger.debug('Ending handleBestBids')
        return val_return

    '''
    This method handles the Pareto Fronts.
    '''
    def handleFronts(self, fronts):
        logger.debug('Starting handleFronts')
        dic_return = {}
        for front in fronts:
            parNbrElement = front.getElementsByTagName("Pareto_Number")[0]
            parNbr = int((parNbrElement.childNodes[0]).data)
            dic_return[parNbr] = self.handleFront(front)
        logger.debug('Ending handleFronts')
        return dic_return

    '''
    This method handles the Pareto Front of offerings.
    '''
    def handleFront(self, front):
        logger.debug('Starting handleFront')
        val_return = []
        bidXmLNodes = front.getElementsByTagName("Bid")
        for bidXmlNode in bidXmLNodes:
            bid = Bid()
            bid.setFromXmlNode(bidXmlNode)
            val_return.append(bid)
        logger.debug('Ending handleFront' + str(len(val_return)))
        return val_return
         
    '''
    This method creates the query for the Marketplace asking 
    other providers' offers.
    '''
    def createAskBids(self, serviceId):
        messageAsk = Message('')
        messageAsk.setMethod(Message.GET_BEST_BIDS)
        messageAsk.setParameter('Provider', self._list_vars['strId'])
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
