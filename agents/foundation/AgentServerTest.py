
import sys
sys.path.append("/home/network_agents_ver2_python/agents/foundation")

sys.path.insert(1,'/home/network_agents_ver2_python/agents')

from Bid import Bid
from ChannelClockServer import Channel_ClockServer
from ChannelMarketplace import Channel_Marketplace
from FoundationException import FoundationException
from Message import Message
from Service import Service
from multiprocessing import Process
from Agent import Agent
from AgentServer import AgentServerHandler
from AgentServer import AgentListener

import AgentServer
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


logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-10s) %(message)s',
                    )
logger = logging.getLogger('agent')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('agentServerTest.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


'''
This method creates the server for listening messages from 
the demand server or the marketplace server.
'''
def start_listening(lock, list_vars):
    logger.debug('Starting listening Id')
    id = list_vars['Id']
    agent_type = list_vars['Type']
    # Start the clock server
    clockPort = agent_properties.l_port_provider + ( id * 3 )
    serverClockServer = AgentListener(agent_properties.addr_agent_clock_server, clockPort, lock, list_vars)
    serverClockServer.start()
    logger.debug('Clock Server started')
    if (agent_type == Agent.PROVIDER_BACKHAUL):
        # Start the transit market place listening server
        logger.debug('Agent type provider backhaul')
        mktPlaceTransit = clockPort + 1
        serverTransitMkrtPlace = AgentListener(agent_properties.addr_agent_mktplace_backhaul, mktPlaceTransit, lock, list_vars)
        serverTransitMkrtPlace.start()
        logger.debug('Server Transit Market place started')
    else:
        logger.debug('Agent type other different from provider backhaul')
        # Start the Isp market place listening server
        mktPlaceIsp = clockPort + 1
        serverISPMkrtPlace = AgentListener(agent_properties.addr_agent_mktplace_isp, mktPlaceIsp, lock, list_vars)
        serverISPMkrtPlace.start()
        logger.debug('Server Isp Market place started')
    
    '''
    This method stops the listening for services
    '''
def stop_listening(lock, list_vars):
    agent_type = list_vars['Type']
    if (agent_type == Agent.PROVIDER_BACKHAUL):
        serverTransitMkrtPlace.stop()
    else:
        serverISPMkrtPlace.stop()
    serverClockServer.stop()


list_vars = {}
list_vars['Id'] = 5
list_vars['strId'] = 'Provider5'
list_vars['Type'] = Agent.PROVIDER_ISP
list_vars['SellingAddres'] = ''
list_vars['BuyingAddres'] = ''
list_vars['Current_Period'] = 0  
list_vars['serviceId'] = '1'
list_vars['capacityControl'] = ''
list_vars['PurchaseServiceId'] = ''
list_vars['Port'] = 1010
list_vars['Parameters'] = {}
list_vars['State'] = AgentServerHandler.IDLE
list_vars['Inactive_Bids'] = {}     # Bids that are no more in use.
list_vars['Bids'] = {}           # Bids in use.
list_vars['Bids_Usage'] = {}
list_vars['Related_Bids'] = {}      # for each bid of the provider lists



lock = threading.Lock()


serverClockServer = None
serverTransitMkrtPlace = None
serverISPMkrtPlace = None
start_listening(lock, list_vars)