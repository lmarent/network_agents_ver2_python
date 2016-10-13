from foundation.Bid import Bid
from foundation.ChannelClockServer import Channel_ClockServer
from foundation.ChannelMarketplace import Channel_Marketplace
from foundation.FoundationException import FoundationException
from foundation.Message import Message
from foundation.Service import Service
from multiprocessing import Process
from AgentServer import AgentServerHandler
from AgentServer import AgentListener
from AgentType import AgentType
from AgentClient import AgentClient


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
import threading




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


logger = logging.getLogger('agent')
fh = logging.FileHandler('agent_logs.log')
fh.setLevel(logging.INFO)
formatter = logging.Formatter('(%(threadName)-10s) %(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)



'''
The class Agent defines methods required for the operation of the 
consumer agent and service provider agent.
'''
class Agent(Process):



    def __init__(self, strID, Id, agent_type, serviceId, agent_seed, sellingAddress, buyingAddress, capacityControl, purchaseServiceId, lock, testThread=False):
        Process.__init__(self)
        # state means: 0 can not create bids, 
        #              1 the process can create and ask for bids.
        #              2 disconnect
        logger.debug('Init agent %s Agent Type:%s', strID, agent_type.getType()) 
        self._used_variables = {}
        self._list_vars = {}
        self._list_vars['Id'] = Id
        self._list_vars['strId'] = strID
        self._list_vars['Type'] = agent_type
        self._list_vars['SellingAddres'] = sellingAddress
        self._list_vars['BuyingAddres'] = buyingAddress
        self._list_vars['Current_Period'] = 0  
        self._list_vars['serviceId'] = serviceId
        self._list_vars['capacityControl'] = capacityControl
        self._list_vars['PurchaseServiceId'] = purchaseServiceId
        self._lock = lock
        self._testThread = testThread
        self._services = {}
        randomGenerator = random.Random()
        randomGenerator.seed(agent_seed)
        self._list_vars['Random'] = randomGenerator
        if (agent_type.getType() == AgentType.CONSUMER_TYPE):
            logger.debug('Starting customer - Agent:%s Agent Type:%s', strID, agent_type.getType()) 
            port = agent_properties.l_port_consumer + Id
            self._list_vars['Port'] = port
            self._list_vars['Parameters'] = {}
            self._list_vars['State'] = AgentServerHandler.IDLE         
        
        if ((agent_type.getType() == AgentType.PROVIDER_ISP) or 
             (agent_type.getType() == AgentType.PROVIDER_BACKHAUL) or
                 (agent_type.getType() == AgentType.PRESENTER_TYPE)):
            self._list_vars['Inactive_Bids'] = {}     # Bids that are no more in use.
            self._list_vars['Bids'] = {}           # Bids in use.
            self._list_vars['Bids_Usage'] = {}
            self._list_vars['Related_Bids'] = {}      # for each bid of the provider lists
                              # competitor bids close it. (List)
        if ((agent_type.getType() == AgentType.PROVIDER_ISP) or 
             (agent_type.getType() == AgentType.PROVIDER_BACKHAUL)):
            port = agent_properties.l_port_provider + Id
            self._list_vars['Port'] = port
            self._list_vars['State'] = AgentServerHandler.IDLE
        
        if (agent_type.getType() == AgentType.PRESENTER_TYPE):
            port = agent_properties.l_port_presenter + Id
            self._list_vars['Port'] = port
            self._list_vars['State'] = AgentServerHandler.IDLE 
            self._list_vars['Current_Bids'] = {}
        
        self._agntClient = AgentClient(self._list_vars)
        logger.info('Agent created with arguments %s', self._list_vars) 

    '''
    This function connect the agent with all the servers
    '''
    def connect(self):
        try:
            strID = self._list_vars['strId']
            agent_type = self._list_vars['Type']
            sellingAddress = self._list_vars['SellingAddres']
            buyingAddress = self._list_vars['BuyingAddres']
            capacityControl = self._list_vars['capacityControl']
                        
            # Connect to servers.            
            self._agntClient.connect_servers(agent_type, strID, sellingAddress, buyingAddress, capacityControl)
            # Request the definition of the service
        except FoundationException as e:
            raise FoundationException(e.__str__())
            

    ''' 
    This method builds the message to start listening based on parameters for the agent.
    '''
    def build_message(self, port):
        logger.debug('Build messsage Id: %s', self._list_vars['Id'])
        port_message = Message("")
        port_message.setMethod(Message.SEND_PORT)
        port_message.setParameter("Port", str(port))
        agent_type = self._list_vars['Type']
        port_message.setParameter("Type", agent_type.getInterfaceName())
        logger.debug('Announcing type %s to servers', agent_type.getType())
        if ( (agent_type.getType() == AgentType.PROVIDER_ISP) 
            or (agent_type.getType() == AgentType.PROVIDER_BACKHAUL) ):
            capacityType = self._list_vars['capacityControl']
            if (capacityType == 'B'):
               port_message.setParameter("CapacityType","bid")
            else:
               port_message.setParameter("CapacityType","bulk")
        return port_message

    '''
    This method verifies the results from the servers for the start listening messages
    '''
    def is_correct_start(self, result_clock, result_mkt_place):
        self.lock.acquire()
        try:
        
            logger.debug('response from the clock server: %s', result_clock.__str__())
            logger.debug('response from the market place: %s', result_mkt_place.__str__())
            if (result_clock.isMessageStatusOk() and result_mkt_place.isMessageStatusOk() ):
                periodStr = result_mkt_place.getParameter("Period")
                self._list_vars['Current_Period'] = int(periodStr)
                logger.info('Servers connected ' + str(periodStr))
                return int(periodStr)
            else:
                logger.error('One of the servers could not establish the connection')
                logger.debug('Ending listening Id: %s', self._list_vars['Id'])
                return -1 # Error
        finally:
            self.lock.release()
    

    '''
    This method creates the server for listening messages from 
    the demand server or the marketplace server.
    '''
    def start_agent(self):
        logger.debug('Starting agent Id: %s Type:%s', self._list_vars['Id'], (self._list_vars['Type']).getType()) 
        self.connect()

        # Bring the service for purchasing(customer) or selling(provider)
        serviceId = self._list_vars['serviceId']
        self.getServiceFromServer(serviceId)
        self._service = self._services[serviceId]

        agent_type = self._list_vars['Type']
        
        # Given the agent type, the software chooses the port to listen.
        if (agent_type.getType() == AgentType.CONSUMER_TYPE):
            clockPort = agent_properties.l_port_consumer + ( self._list_vars['Id'] * 3 )
        elif (agent_type.getType() == AgentType.PRESENTER_TYPE):
            clockPort = agent_properties.l_port_presenter + ( self._list_vars['Id'] * 3 )
        else:
            clockPort = agent_properties.l_port_provider + ( self._list_vars['Id'] * 3 )
            
        # Start the clock server
        self._serverClockServer = AgentListener(agent_properties.addr_agent_clock_server, clockPort, self._lock, self._testThread, self._list_vars)
        self._serverClockServer.start()
                
        if (agent_type.getType() == AgentType.PROVIDER_BACKHAUL):
            # Start the transit market place listening server
            mktPlaceTransit = clockPort + 1
            self._serverTransitMkrtPlace = AgentListener(agent_properties.addr_agent_mktplace_backhaul, mktPlaceTransit, self._lock, self._testThread, self._list_vars)
            self._serverTransitMkrtPlace.start()
        else:
            # Start the Isp market place listening server
            mktPlaceIsp = clockPort + 1
            self._serverISPMkrtPlace = AgentListener(agent_properties.addr_agent_mktplace_isp, mktPlaceIsp, self._lock, self._testThread, self._list_vars)
            self._serverISPMkrtPlace.start()
        # Send the announce the port for the clock server.
        response3 = ''
        port_message = self.build_message(clockPort)
        response3 = self._agntClient.sendMessageClock(port_message)
        
        response4 = ''
        if (agent_type.getType() == AgentType.PROVIDER_BACKHAUL):
            # send the message to announce the port for the transit market place.
            port_message = self.build_message(mktPlaceTransit)
            logger.debug('port message to the market transit: %s', port_message.__str__())
            response4 = self._agntClient.sendMessageMarket(port_message)
            logger.debug('response from the market transit: %s', response4.__str__())
        else:
            # send the message to announce the port for the isp market place.
            port_message = self.build_message(mktPlaceIsp)
            logger.debug('port message to the market isp: %s', port_message.__str__())
            response4 = self._agntClient.sendMessageMarket(port_message)
        period = self.is_correct_start(response3, response4)
        
        # An error occur, so we have to stop the provider.
        if (period < 0):
            self.stop()
        
        logger.debug('Ending listening Id: %s', self._list_vars['Id']) 
        return period

    '''
    This method stops the listening for services
    '''
    def stop_agent(self):
        logger.debug('Stop agent Id: %s name:%s', self._list_vars['Id'], self._list_vars['strId']) 
        self.lock.acquire()
        logger.debug('Stop agent lock adquired: %s name:%s', self._list_vars['Id'], self._list_vars['strId'])
        try:    
            # Disconnect from servers.
            agent_type = self._list_vars['Type']
            self._agntClient.disconnect_servers(agent_type)

            # Stop listeners.
            logger.debug('Starting stop Id: %s', self._list_vars['Id']) 
            logger.debug('Stoping clockServer Listener Id: %s', self._list_vars['Id']) 
            self._serverClockServer.stop()
            logger.debug('Stoping market Place Listener Id: %s', self._list_vars['Id']) 
            if (agent_type.getType() == AgentType.PROVIDER_BACKHAUL):
                self._serverTransitMkrtPlace.stop()
            else:
                self._serverISPMkrtPlace.stop()
            logger.debug('Ending stop Id: %s', self._list_vars['Id']) 
        finally:
            self.lock.release()

    
    def getServiceFromServer(self, serviceId):
        logger.debug('Starting getServiceFromServer Id: %s', self._list_vars['Id']) 
        try: 
            if (str(serviceId) not in (self._services).keys()):
                service = self._agntClient.getServiceFromServer(str(serviceId))
                self._services[serviceId] = service
                logger.debug('Ending getServiceFromServer Id: %s', self._list_vars['Id']) 
        except FoundationException as e:
            logger.error('exception Id:%s - Message:%s', self._list_vars['Id'], e.__str__()) 
            raise FoundationException(e.__str__())

    def sendMessageMarket(self, message):
        return self._agntClient.sendMessageMarket(message)

    def sendMessageMarketBuy(self, message):
        return self._agntClient.sendMessageMarketBuy(message)

    def createAskBids(self,serviceId):
        return self._agntClient.createAskBids(serviceId)
    
    def AskBackhaulBids(self, serviceId):
        return self._agntClient.AskBackhaulBids(serviceId)

# End of Agent class
