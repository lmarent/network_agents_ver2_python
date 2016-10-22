from foundation.Bid import Bid
from foundation.ChannelClockServer import Channel_ClockServer
from foundation.ChannelMarketplace import Channel_Marketplace
from foundation.FoundationException import FoundationException
from foundation.Message import Message
from foundation.Service import Service
from multiprocessing import Process
from AgentType import AgentType

import random
import agent_properties
import asyncore
import logging
import re
import socket
import SocketServer
import threading
import time
import uuid
import xml.dom.minidom
import threading


logger = logging.getLogger('agent_server')
logger.setLevel(logging.INFO)
fh = logging.FileHandler('agent_server_logs.log', mode='w')
formatter = logging.Formatter('format="%(threadName)s:-%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


class AgentServerHandler(asyncore.dispatcher):
    '''
    The AgentServerHandler class implements methods to deal with the 
    agents basic operations.
    '''

    IDLE = 0
    BID_PERMITED = 2
    TO_BE_ACTIVED = 3
    ACTIVATE = 4
    TERMINATE = 5

    def __init__(self, addr, sock, thread_sockets, lock, testThread, list_args, strings_received):
        asyncore.dispatcher.__init__(self, sock=sock, map=thread_sockets)
        self._list_args = list_args
        self._addr_orig = addr
        self._sock_orig = sock
        self._strings_received = strings_received
        self.lock = lock
        self.testThread = testThread
        logger.debug('Nbr sockets being track: %d', len(thread_sockets))
    
    def end_period_process(self, message):    
        pass

    def start_period_process(self, message):
        pass
    
    '''
    This method activates the agent with all its parameters.
    '''
    def activate(self, message):
        logger.debug('Activating the consumer: %s', str(self._list_args['Id']) )
        self.lock.acquire()
        try: 
           agent_type = self._list_args['Type']
           if ( agent_type.getType() == AgentType.CONSUMER_TYPE):
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
           if (agent_type.getType() == AgentType.PRESENTER_TYPE):
                logger.info('Activating the Presenter: %s - Period %s', 
                     str(self._list_args['Id']), 
                             str(self._list_args['Current_Period'])  )
                self._list_args['State'] = AgentServerHandler.ACTIVATE
        finally:
           if self.testThread == True:
               time.sleep(2)
           self.lock.release()

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
        self.lock.acquire()
        try: 
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
        finally:
           if self.testThread == True:
               time.sleep(2)
           self.lock.release()

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
            agent_type = self._list_args['Type']
            if ( agent_type.getType() == AgentType.PRESENTER_TYPE):
                logger.debug('Handle competitor bids')
                self._list_args['Current_Bids'] = {}  
                logger.debug('clear Handle competitor bids')
                
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

                            # Replace the parent bid, looking for the actual one already in the dictionary 
                            if (competitor_bid.getParentBid() != None):
                                parentBidId = competitor_bid.getParentBid().getId() 
                                if parentBidId not in self._list_args['Related_Bids']:
                                    logger.error('Parent BidId %s not found in related bids', parentBidId)
                                else:
                                    parentBid = (self._list_args['Related_Bids'])[parentBidId]
                                    competitor_bid.insertParentBid(parentBid)
                                
                            #logger.debug('Inserting competitor bid:' + competitor_bid.__str__())
                            (self._list_args['Related_Bids'])[competitor_bid.getId()] = competitor_bid
                        
                        # Inserts on exchanged bids
                        if (agent_type.getType() == AgentType.PRESENTER_TYPE):
                            (self._list_args['Current_Bids'])[competitor_bid.getId()] = competitor_bid
                                    
            if (agent_type.getType() == AgentType.PRESENTER_TYPE):
                logger.debug('End Handle competitor bids - num exchanged:' + str(len(self._list_args['Current_Bids'])))
            logger.debug('clear 3 Handle competitor bids')
            logger.debug('Ending handled bid competitors for agent is:' + str(self._list_args['Id']))
            
        except Exception as e:
            raise FoundationException(str(e))
            
    '''
    This method receives the offer information from competitors
    '''
    def receive_bid_information(self, message):
        self.lock.acquire()
        if self.testThread == True:
            logger.debug('Acquire the lock')
        try:
            logger.debug('Initiating competitor bid information - Agent:%s', str(self._list_args['Id']) )
            agent_type = self._list_args['Type']
            if (( agent_type.getType() == AgentType.PROVIDER_ISP) or 
                 (agent_type.getType() == AgentType.PROVIDER_BACKHAUL) or 
                  (agent_type.getType() == AgentType.PRESENTER_TYPE)):
                period = int(message.getParameter("Period"))
                period = period - 1 # The server sends the information tagged with the next period.
                                    # TODO: Change the Market Place Server to send the correct period.
                document = self.removeIlegalCharacters(message.getBody())
                logger.info('Period' + str(period) + 'bid document' + str(document))
                dom = xml.dom.minidom.parseString(document)
                competitorsXmlNodes = dom.getElementsByTagName("New_Bids")
                for competitorsXmlNode in competitorsXmlNodes:
                    self.handleCompetitorBids(period, competitorsXmlNode)
            logger.debug('Competitor bids Loaded Agent: %s', str(self._list_args['Id']))
        except Exception as e: 
            logger.debug('Exception raised' + str(e) ) 
            raise FoundationException(str(e))
        finally:
           if self.testThread == True:
               logger.info('Going to sleep')
               time.sleep(2)
               logger.info('After sleep')
           self.lock.release()
            
        

    '''
    This method receives purchase statistics from providers. For each 
    offer we receive its neigborhood offers.
    '''
    def receive_purchase_feedback(self, message):
        self.lock.acquire()
        try:
            logger.debug('Initiating Receive Purchase feedback Agent:%s', str(self._list_args['Id']))
            agent_type = self._list_args['Type']
            if (( agent_type.getType() == AgentType.PROVIDER_ISP) 
               or ( agent_type.getType() == AgentType.PROVIDER_BACKHAUL) 
                  or ( agent_type.getType() == AgentType.PRESENTER_TYPE)):
                period = int(message.getParameter("Period"))
                self._list_args['Current_Period'] = period
                document = self.removeIlegalCharacters(message.getBody())
                #print document
                dom = xml.dom.minidom.parseString(document)
                # receive purchase statistics
                purchaseXmlNodes = dom.getElementsByTagName("Receive_Purchases")        
                for purchaseXmlNode in purchaseXmlNodes:
                    self.handleReceivePurchases(period, purchaseXmlNode)
                # After receiving the purchase information the provider can 
                # start to create new bids.
                if (( agent_type.getType() == AgentType.PROVIDER_ISP) 
                    or (agent_type.getType() == AgentType.PROVIDER_BACKHAUL)):
                    self._list_args['State'] = AgentServerHandler.BID_PERMITED    
                logger.debug('Receive Purchase feedback - Agent:%s Period: %s ', str(self._list_args['Id']), str(self._list_args['Current_Period'] ))        
        except Exception as e: 
           raise FoundationException(str(e))
        finally:
           if self.testThread == True:
               time.sleep(2)
           self.lock.release()
        

    '''
    This method terminates the agent processing state.
    '''
    def disconnect_process(self):
        self.lock.acquire()
        try: 
            self._list_args['State'] = AgentServerHandler.TERMINATE
            logger.debug('Terminate processing, the state is now in: %s', 
                     str(self._list_args['State']) )
        finally:
            self.lock.release()

    def process_getUnitaryCost(self, message):
        logger.debug('Initiating process GetUnitaryCost')
        self.lock.acquire()
        try:
            bid = None
            agent_type = self._list_args['Type']
            if (( agent_type.getType() == AgentType.PROVIDER_ISP) 
               or ( agent_type.getType() == AgentType.PROVIDER_BACKHAUL)):
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
        finally:
           if self.testThread == True:
               time.sleep(2)
           self.lock.release()

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
        logger.debug('Initiating do_processing %s', message.getStringMethod())
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
            logger.debug('Message for parent %s from:%s, character received:%s', self._list_args['Id'], string_key, str(len(self._strings_received[string_key])) )
            # We need to do a while because more than one message could arrive almost at the same time for the agent.
            while (message is not None):
                logger.debug('Message for parent %s message: %d',self._list_args['Id'], len(message.__str__()) )
                self.do_processing(message)
                message = self.getMessage(string_key)
        except Exception as e:
            raise asyncore.ExitNow('Server is quitting!')

    def handle_close(self):
        #Flush the buffer
        print self._sock_orig.getsockname()
        logger.debug('closing connection host:%s  port:%s',self._addr_orig, (self._sock_orig.getsockname(),))
        self.close()            
            
    def handle_expt(self):
        print self._sock_orig.getsockname()
        logger.debug('Handle except host:%s  port:%s',self._addr_orig, (self._sock_orig.getsockname(),))
        self.close() # connection failed, shutdown

    def writable(self):
        return 0 # don't have anything to write

class AgentDispacher(asyncore.dispatcher):
    def __init__(self, address, port, lock, testThread, thread_sockets, list_args):
        asyncore.dispatcher.__init__(self, map=thread_sockets)
        self._address = address
        self._port = port
        self._strings_received = {}
        self._list_args = list_args
        self._lock = lock
        self._testThread = testThread
        self._thread_sockets = thread_sockets
        
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((self._address, self._port))
        self.listen(4)
        logger.debug("Server Listening on {h}:{p}".format(h=self._address, p=self._port))

    '''
    This method handles the acceptance of incoming socket connection.
    '''
    def handle_accept(self):
        logger.debug('handle Accept Id: %s', self._list_args['Id'])
        pair = self.accept()
        if pair is not None:
            logger.debug('handle Accept Id: %s address:%s port:%s', self._list_args['Id'], self._address, self._port)
            sock, addr = pair
            logger.debug('Incoming connection from %s', repr(addr))
            string_pair = repr(addr) + repr(sock)
            self._strings_received[string_pair] = ''
            try:
                handler = AgentServerHandler( addr, sock, self._thread_sockets, self._lock, self._testThread, self._list_args, self._strings_received)
            except asyncore.ExitNow, e:
                raise FoundationException(str(e))
            logger.debug('Ending handle Accept Id: %s address:%s port:%s', self._list_args['Id'], self._address, self._port)

    def handle_close(self):
        self.close()

'''
The class AgentListener defines the methods for listening the port.
'''
class AgentListener(threading.Thread):

    
    def __init__(self, address, port, lock, testThread, list_args, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group=group, target=target, name=name,
                                  verbose=verbose)
        self._stop = threading.Event()
        self._thread_sockets = dict()
        self._lock = lock
        self._address = address
        self._port = port
        self._testThread = testThread
        self._list_args = list_args
        self._agentDispacher = AgentDispacher(self._address, self._port, self._lock, self._testThread, self._thread_sockets, self._list_args)
        logger.info('initiating with address:%s port:%d arg:%s', address, port, list_args)
        return
    
    '''
    This method starts listening the port.
    '''
    def run(self):
        asyncore.loop(map=self._thread_sockets)
        logger.info('asyncore ends Agent:%s address:%s port:%s', self._list_args['Id'], self._address, self._port)
        return

    def stop(self):
        logger.debug('Start Stop thread address:%s port:%s', self._address, self._port)
        self._agentDispacher.close()
        logger.info('close the dispatcher Agent Id:%s - Address:%s port:%s', self._list_args['Id'], self._address, self._port)

    '''
    This method stops listening the port.
    '''
    def stopped(self):
        return self._stop.isSet()        
