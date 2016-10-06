from foundation.Bid import Bid
from foundation.ChannelClockServer import Channel_ClockServer
from foundation.ChannelMarketplace import Channel_Marketplace
from foundation.FoundationException import FoundationException
from foundation.Message import Message
from foundation.Service import Service
from AgentType import AgentType

import random
import agent_properties
import logging
import re
import socket
import SocketServer
import threading
import time
import uuid
import xml.dom.minidom

logger = logging.getLogger('agent')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('agent_logs.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('format="%(threadName)s:-%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

class AgentClient:

    def __init__(self, list_vars):
        self._list_vars = list_vars
        self._channelMarketPlace = None
        self._channelMarketPlaceBuy =None
        self._channelClockServer =None

    def create_connect_message(self, strID):
        connect = Message("")
        connect.setMethod(Message.CONNECT)
        connect.setParameter("Agent",strID)
        return connect

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
    This function connects the agent to servers ( clock server and markets places)
    '''
    def connect_servers(self, agent_type, strID, sellingAddress, buyingAddress, capacityControl):
        logger.debug('Starting connect servers agent %s selling Address:%s buyingAddress:%s', strID, sellingAddress, buyingAddress) 
        if (agent_type.getType() == AgentType.PROVIDER_ISP):
            logger.debug('Agent Provider ISP %s', strID) 
            port = agent_properties.mkt_place_listening_port
            address = sellingAddress
            # This will be the channel to put bids.
            self._channelMarketPlace = Channel_Marketplace(address, port)
            address = buyingAddress
            # This will be the channel to buy resources.
            self._channelMarketPlaceBuy = Channel_Marketplace(address, port)
        elif (agent_type.getType() == AgentType.PROVIDER_BACKHAUL):
            logger.debug('Agent Provider Backhaul %s', strID) 
            port = agent_properties.mkt_place_listening_port
            address = sellingAddress
            # This will be the channel to put bids.                
            self._channelMarketPlace = Channel_Marketplace(address, port)
        else:
            logger.debug('Agent Other %s', strID)
            port = agent_properties.mkt_place_listening_port
            address = agent_properties.addr_mktplace_isp                
            self._channelMarketPlace = Channel_Marketplace(address, port)
        self._channelClockServer = Channel_ClockServer()
            
        # Send the Connect message to ClockServer
        connect = self.create_connect_message(strID)
        response1 = (self._channelClockServer).sendMessage(connect)
        if (response1.isMessageStatusOk() == False):
            raise FoundationException("Agent: It could not connect to clock server")
            
        # Send the Connect message to MarketPlace 
        if (agent_type.getType() == AgentType.PROVIDER_ISP):
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

    def disconnect_servers(self, agent_type):
        logger.debug('Disconnect Servers Id:%s', self._list_vars['Id']) 
        if (agent_type.getType() == AgentType.PROVIDER_ISP):
            logger.debug('Disconnect provider isp') 
            self._channelMarketPlace.close()
            self._channelMarketPlaceBuy.close()
        elif (agent_type.getType() == AgentType.PROVIDER_BACKHAUL):
            # This will be the channel to put bids.                
            logger.debug('Disconnect provider backhaul') 
            self._channelMarketPlace.close()
        else:
            logger.debug('Disconnect other different from provider')
            self._channelMarketPlace.close()
        self._channelClockServer.close()
        logger.debug('Ending Diconnect servers agent %s', self._list_vars['Id']) 
        

    def sendMessageClock(self,message):
        response = Message('')
        if self._channelClockServer != None:
            response = (self._channelClockServer).sendMessage(message)
        return response

    def sendMessageMarket(self , message):
        response = Message('')
        if self._channelMarketPlace != None:
            response = (self._channelMarketPlace).sendMessage(message)
        return response

    def sendMessageMarketBuy(self , message):
        response = Message('')
        if self._channelMarketPlaceBuy != None:
            response = (self._channelMarketPlaceBuy).sendMessage(message)            
        return response

    '''
    This method handles the GetService function. It checks if the 
    server has sent more than one message.
    '''
    def handleGetService(self, document):
        logger.debug('Starting get service handler Id:%s', self._list_vars['Id'])
        document = self.removeIlegalCharacters(document)
        logger.debug('document:%s', document)
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

    def getServiceFromServer(self, serviceId):
        logger.debug('Starting getServiceFromServer Id:%s', self._list_vars['Id'])
        try: 
            connect = Message("")
            connect.setMethod(Message.GET_SERVICES)
            connect.setParameter("Service",serviceId)
            response = self.sendMessageClock(connect)
            if (response.isMessageStatusOk() ):
                logger.debug('ending  getServiceFromServer')
                return self.handleGetService(response.getBody())
        except FoundationException as e:
            raise FoundationException(e.__str__())

    '''
    This method returns the available services.
    '''
    def getServices(self):
        logger.debug('Starting get services Id:%s', self._list_vars['Id'])
        messageAsk = Message('')
        messageAsk.setMethod(Message.GET_SERVICES)
        messageResult = self.sendMessageClock(messageAsk)
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
        messageResult = self.sendMessageMarket(messageAsk)
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
	

    '''
    This method creates the query for the Marketplace asking 
    other providers' offers.
    '''
    def AskBackhaulBids(self, serviceId):
        messageAsk = Message('')
        messageAsk.setMethod(Message.GET_BEST_BIDS)
        messageAsk.setParameter('Provider', self._list_vars['strId'])
        messageAsk.setParameter('Service', serviceId)
        messageResult = self.sendMessageMarketBuy(messageAsk)
        if messageResult.isMessageStatusOk():
            document = self.removeIlegalCharacters(messageResult.getBody())
            try:
                dom = xml.dom.minidom.parseString(document)
                return self.handleBestBids(dom)
            except Exception as e: 
                raise FoundationException(str(e))
        else:
            raise FoundationException("Best bids not received")
