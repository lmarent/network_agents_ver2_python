

import sys
import os
syspath = os.path.dirname(os.path.abspath(__file__))
parent_path = os.path.abspath(os.path.join(syspath, os.pardir))
found_path = parent_path + "/foundation"
sys.path.append(found_path)
sys.path.insert(1,parent_path)

from Bid import Bid
from ChannelClockServer import Channel_ClockServer
from ChannelMarketplace import Channel_Marketplace
from FoundationException import FoundationException
from Message import Message
from Service import Service
from multiprocessing import Process
from AgentServer import AgentServerHandler
from AgentServer import AgentListener
from AgentType import AgentType
from AgentClient import AgentClient

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
def start_provider_isp(agntClientVect):
    logger.debug('Starting start perovider isp')
    id = 5
    strID = 'Provider5'
    agent_type = AgentType(AgentType.PROVIDER_ISP)
    sellingAddress = agent_properties.addr_mktplace_isp
    buyingAddress = agent_properties.addr_mktplace_backhaul
    capacityControl = ''
    serviceId = '1'
    
    # Start the Agent Client
    list_vars = {}
    list_vars['Id'] = 5
    list_vars['strId'] = strID
    list_vars['Type'] = agent_type
    list_vars['SellingAddres'] = agent_properties.addr_mktplace_isp
    list_vars['BuyingAddres'] = agent_properties.addr_mktplace_backhaul
    list_vars['Current_Period'] = 0  
    list_vars['serviceId'] = 1
    list_vars['capacityControl'] = ''
    list_vars['PurchaseServiceId'] = ''
    agntClient = AgentClient(list_vars)
    agntClient.connect_servers(agent_type, strID, sellingAddress, buyingAddress, capacityControl)
    agntClient.getServiceFromServer(serviceId)
    agntClient.createAskBids(serviceId)
    agntClientVect[0] = agntClient
    
def stop_provider_isp(agntClientVect):
    agent_type = AgentType(AgentType.PROVIDER_ISP)
    agntClient = agntClientVect[0]
    agntClient.disconnect_servers(agent_type)
    
def start_provider_backhaul(agntClientVect):
    logger.debug('Starting start provider backhaul')
    id = 5
    strID = 'Provider5'
    agent_type = AgentType(AgentType.PROVIDER_BACKHAUL)
    sellingAddress = agent_properties.addr_mktplace_isp
    buyingAddress = agent_properties.addr_mktplace_backhaul
    capacityControl = ''
    serviceId = '1'
    
    # Start the Agent Client
    list_vars = {}
    list_vars['Id'] = 5
    list_vars['strId'] = strID
    list_vars['Type'] = agent_type
    list_vars['SellingAddres'] = agent_properties.addr_mktplace_backhaul
    list_vars['BuyingAddres'] = ''
    list_vars['Current_Period'] = 0  
    list_vars['serviceId'] = 1
    list_vars['capacityControl'] = ''
    list_vars['PurchaseServiceId'] = ''
    agntClient = AgentClient(list_vars)
    agntClient.connect_servers(agent_type, strID, sellingAddress, buyingAddress, capacityControl)
    agntClient.getServiceFromServer(serviceId)
    agntClient.createAskBids(serviceId)
    agntClientVect[0] = agntClient

def stop_provider_backhaul(agntClientVect):
    agent_type = AgentType(AgentType.PROVIDER_BACKHAUL)
    agntClient = agntClientVect[0]
    agntClient.disconnect_servers(agent_type)

def start_customer(agntClientVect):
    logger.debug('Starting start customer')
    id = 5
    strID = 'Provider5'
    agent_type = AgentType(AgentType.CONSUMER_TYPE)
    sellingAddress = ''
    buyingAddress = agent_properties.addr_mktplace_isp
    capacityControl = ''
    serviceId = '1'
    
    # Start the Agent Client
    list_vars = {}
    list_vars['Id'] = 5
    list_vars['strId'] = strID
    list_vars['Type'] = agent_type
    list_vars['SellingAddres'] = agent_properties.addr_mktplace_isp
    list_vars['BuyingAddres'] = agent_properties.addr_mktplace_backhaul
    list_vars['Current_Period'] = 0  
    list_vars['serviceId'] = 1
    list_vars['capacityControl'] = ''
    list_vars['PurchaseServiceId'] = ''
    agntClient = AgentClient(list_vars)
    agntClient.connect_servers(agent_type, strID, sellingAddress, buyingAddress, capacityControl)
    agntClient.getServiceFromServer(serviceId)
    agntClient.createAskBids(serviceId)
    agntClientVect[0] = agntClient

def stop_customer(agntClientVect):
    agent_type = AgentType(AgentType.CONSUMER_TYPE)
    agntClient = agntClientVect[0]
    agntClient.disconnect_servers(agent_type)


agntClientVect = []
agntClientVect.append(None)
start_provider_isp(agntClientVect)
if agntClientVect[0] == None:
    print 'Error the agent client is None'
else:
    stop_provider_isp(agntClientVect)

agntClientVect[0] = None
start_provider_backhaul(agntClientVect)
if agntClientVect[0] == None:
    print 'Error the agent client is None'
else:
    stop_provider_backhaul(agntClientVect)


agntClientVect[0] = None
start_customer(agntClientVect)
if agntClientVect[0] == None:
    print 'Error the agent client is None'
else:
    stop_customer(agntClientVect)

print 'Ending Test'
