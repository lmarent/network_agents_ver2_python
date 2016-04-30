from __future__ import division
from foundation.Message import Message
from foundation.Bid import Bid
from foundation.Agent import Agent
from foundation.FoundationException import FoundationException
from foundation.Agent import AgentServerHandler
from foundation.DecisionVariable import DecisionVariable
from foundation.ChannelProvider import ChannelProvider
from ProviderAgentException import ProviderException
from PresenterAgentException import PresenterException
import foundation.agent_properties
import logging
import math
import operator
import random
import time
import uuid
import xml.dom.minidom
import os
import inspect

logger = logging.getLogger('presenter_application')


class Presenter(Agent):
    '''
    The Provider class defines methods to be used by the service
    provider agent. It includes methods for pricing and quality
    strategies, place offerings into the marketplace, get other 
    providers offerings and determine the best strategy to capture 
    more market share.    
    '''

    def __init__(self, strID, Id, serviceId, graphics):
	try:
	    super(Presenter, self).__init__(strID, Id, 'presenter', serviceId, 0) 
	    self._provider_colors = {}   # maintains the colors used for providers.
	    self._graphics = graphics
	    self._provider_channels = {}
	    logger.debug('Initializing the agent:' + strID )
	    logger.info(self._graphics )

	except FoundationException as e:
	    raise ProviderException(e.__str__())

    def connectToProvider(self, providerId):
	logger.debug('Initializing connectToProvider')
	message = Message('')
	message.setMethod(Message.GET_PROVIDER_CHANNEL)
	message.setParameter('ProviderId', providerId)
	messageResult = self._channelMarketPlace.sendMessage(message)
	if messageResult.isMessageStatusOk():
	    address = messageResult.getParameter("Address")
	    port = int(messageResult.getParameter("Port"))
	    print 'provider address:' + address + ' ' + 'port' + str(port)
	    channelProvider = ChannelProvider(address, port)
	    self._provider_channels[providerId] = channelProvider
	    print "Connection with provider finished"
	else:
	    logger.error('The provider is not listening')
	    raise PresenterException('The provider is not listening')
	logger.debug('Ending connectToProvider' )
    
    def obtainDecisionParameters(self,decisionVariable):
	logger.info('Initializing obtainDecisionParameters:' + decisionVariable )
	min_value = ((self._service)._decision_variables[decisionVariable]).getMinValue()
	max_value = ((self._service)._decision_variables[decisionVariable]).getMaxValue()
	label = ((self._service)._decision_variables[decisionVariable]).getName()
	logger.info('Ending obtainDecisionParameters:' + label + str(min_value) + str(max_value) )
	return label, min_value, max_value
    
    def setHeaderLine(self, decisionVariableX, decisionVariableY):
	logger.debug('Initializing setHeaderLine' )
	line ='period,'
	if (decisionVariableX.get('type') == 'D'):
	    idVariable = decisionVariableX.get('decision_variable')
	    label, min_value, max_value = self.obtainDecisionParameters(idVariable)
	    line = line + label + ',' + '{0}'.format(min_value) 
	    line = line + ',' + '{0}'.format(max_value) 
	else:
	    line = line + decisionVariableX.get('name') + ',' '{0}'.format(0)
	    line = line + ',' + '{0}'.format(0)
	
	if  (decisionVariableY.get('type') == 'D'):
	    idVariable = decisionVariableY.get('decision_variable')
	    label, min_value, max_value = self.obtainDecisionParameters(idVariable)
	    line = line + ',' + label + ',' + '{0}'.format(min_value) 
	    line = line + ',' + '{0}'.format(max_value)	    
	else:
	    line = line + ',' + decisionVariableY.get('name') + ',' '{0}'.format(0)
	    line = line + ',' + '{0}'.format(0)
	line = line + '\n'	    
	logger.debug('Ending setHeaderLine:' + line)
	return line
    
    def getQuantity(self, bid ):
	logger.debug('Initializing getQuantity' + bid.getId() )
	quantity = 0
	if bid.getId() in self._list_vars['Bids_Usage'].keys():
	    bidData = (self._list_vars['Bids_Usage'])[bid.getId()]
	    if self._list_vars['Current_Period'] in bidData:
		periodData = bidData[self._list_vars['Current_Period']]
		quantity = periodData[bid.getId()]
	logger.debug('Ending getQuantity' + str(quantity) )
	return quantity
    
    def getUnitaryCost(self, bid):
	logger.debug('Initializing getUnitaryCost' + bid.getId() )
	cost = 0
	messageCost = Message('')
	messageCost.setMethod(Message.GET_UNITARY_COST)
	messageCost.setParameter('BidId', bid.getId())
	if bid.getProvider() not in self._provider_channels:
	    try:
		self.connectToProvider(bid.getProvider())
	    except PresenterException as e:
		pass 
	if bid.getProvider() in self._provider_channels:
	    messageRes = (self._provider_channels[bid.getProvider()]).sendMessage(messageCost)
	    if messageRes.isMessageStatusOk():
		cost = float(messageRes.getParameter("UnitaryCost"))
	    else:
		raise PresenterException('The offering cost could not be calculated')
	else:
	    raise PresenterException('The offering cost could not be calculated')
	logger.debug('Ending getUnitaryCost:' + str(cost) )
	return cost
    
    def getPrice(self, bid):
	logger.debug('Initializing getPrice' + bid.getId() )
	price = 0
	decisionVariable = (self._service).getPriceDecisionVariable()
	if decisionVariable is not None:
	    price = bid.getDecisionVariable(decisionVariable)
	logger.debug('Ending getPrice' + str(price) )
	return price
    
    def getProfit(self, bid):
	logger.debug('Initializing getProfit' + bid.getId() )
	quantity = self.getQuantity(bid)
	try:
	    cost = self.getUnitaryCost(bid)
	    price = self.getPrice(bid)
	    profit = quantity * (price - cost)
	except PresenterException as e:
	    profit = 0
	logger.debug('Ending getProfit' + str(profit) )
	return profit
    
    def getIncome(self, bid):
	logger.debug('Initializing getIncome' + bid.getId() )
	quantity = self.getQuantity(bid)
	price = self.getPrice(bid)
	income = quantity * price
	logger.debug('Ending getIncome' + str(income) )
	return income
    
    def getProvider(self,bid):
	return bid._provider
    
    def getId(self,bid):
	return bid.getId()
    
    def obtainOfferedValue(self, bid, offeredValue):
	logger.debug('Initializing obtainOfferedValue' + offeredValue.__str__())
	# The offered value could not be defined by users.
	if ('type' in offeredValue):
	    if (offeredValue['type'] == 'D'): 
		value = bid.getDecisionVariable(offeredValue['decision_variable'])
	    else:
		value = getattr(self, offeredValue['function'])(bid)
	    
	else:
	    value = None
	logger.debug('End obtainOfferedValue' + str(value) )
	return value
    
    def setBidInformationToShow(self, bid, graphDict):
	logger.debug('Initializing setBidInformationToShow')
	xValue = None
	yValue = None
	colorValue = None
	labelValue  = None
	column1Value = None
	column2Value = None
	column3Value = None
	column4Value = None	    
	if bid.getId() in self._list_vars['Bids_Usage'].keys():
	    line = ''
	    # Establish the value of the X variable
	    offeredValue = graphDict.get('x_axis')
	    xValue = self.obtainOfferedValue(bid, offeredValue)
	    # Establish the value of the Y value
	    offeredValue = graphDict.get('y_axis')
	    yValue = self.obtainOfferedValue(bid, offeredValue)
	    # Establish the value for color
	    offeredValue = graphDict.get('color')
	    if (offeredValue is not None):
		colorValueOrig = self.obtainOfferedValue(bid, offeredValue)
		if colorValueOrig in graphDict['instance_colors']:
		    colorValue = (graphDict['instance_colors']).get(colorValueOrig)
		else:
		    colorValue = random.uniform(0,1)
		    (graphDict['instance_colors'])[colorValueOrig] = colorValue
	    else:
		colorValue = None
	    # Establish the value for label
	    offeredValue = graphDict.get('label')
	    if (offeredValue is not None):
		labelValue = self.obtainOfferedValue(bid, offeredValue)
	    else:
		labelValue = None
	    # Establish the value of the column1
	    offeredValue = graphDict.get('column1')
	    if (offeredValue is not None):
		column1Value = self.obtainOfferedValue(bid, offeredValue)
	    else:
		column1Value = None
	    # Establish the value of the column2
	    offeredValue = graphDict.get('column2')
	    if (offeredValue is not None):
		column2Value = self.obtainOfferedValue(bid, offeredValue)
	    else:
		column2Value = None
	    # Establish the value of the column3
	    offeredValue = graphDict.get('column3')
	    if (offeredValue is not None):
		column3Value = self.obtainOfferedValue(bid, offeredValue)
	    else:
		column3Value = None
	    # Establish the value of the column4
	    offeredValue = graphDict.get('column4')
	    if (offeredValue is not None):
		column4Value = self.obtainOfferedValue(bid, offeredValue)
	    else:
		column4Value = None
	else:
	    logger.error('The bid id not exist in bidUsage' + bid.getId() ) 
	    if (bid.getId() in self._list_vars['Bids_Usage']):
		logger.error('The bid id not exist in bidUsage - but exists' + bid.getId() ) 
	logger.debug('Ending setBidInformationToShow' + str(xValue) + str(yValue)
		       + str(colorValue) + str(labelValue) + str(column1Value) 
		       + str(column2Value) + str(column3Value) + str(column4Value) ) 
	return  xValue, yValue, colorValue, labelValue, column1Value, column2Value, column3Value, column4Value
    
    def contructOldName(self, name):
	name = name.replace(" ","_")
	name = name + str(self._list_vars['Current_Period'] -1) 
	name = name + '.txt'
	return name
    
    def contructNewName(self, name):
	name = name.replace(" ","_")
	name = name + '.txt'
	return name
    
    def constructLineDetail(self, xValue, yValue, colorValue, labelValue, 
		            column1, column2, column3, column4):
	line = str(self._list_vars['Current_Period']) + ','
	printed = False
	if xValue is not None:
	    line = line + str(xValue) + ',' 
	    printed = True
	else:
	    line = line + ',' 
	
	if yValue is not None:
	    line = line + str(yValue) + ',' 
	    printed = True
	else:
	    line = line + ','  
	
	if labelValue is not None:
	    line = line + str(labelValue) + ',' 
	    printed = True
	else:
	    line = line + ','   
	
	if colorValue is not None:
	    line = line + str(colorValue) + ','
	    printed = True
	else:
	    line = line + ','   

	if column1 is not None:
	    line = line + str(column1) + ','
	    printed = True
	else:
	    line = line + ','   

	if column2 is not None:
	    line = line + str(column2) + ','
	    printed = True
	else:
	    line = line + ','   

	if column3 is not None:
	    line = line + str(column3) + ','
	    printed = True
	else:
	    line = line + ','   

	if column4 is not None:
	    line = line + str(column4) + ','
	    printed = True
	else:
	    line = line + ','   
	logger.debug('Ending constructLineDetail' + line)
	return line, printed
   
    def initializeFileResults(self):
	currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	currentdir = currentdir + '/' + foundation.agent_properties.result_directory
	print currentdir
	for graphic in self._graphics:
	    filenameNew = self.contructNewName( (self._graphics[graphic]).get('name') )
	    filenameNew = currentdir + filenameNew
	    try:
		fileResult = open(filenameNew,"w")
		# Establish the file header.
		variable_x = (self._graphics[graphic]).get('x_axis')
		variable_y = (self._graphics[graphic]).get('y_axis')
		line = self.setHeaderLine( variable_x, variable_y )
		fileResult.write(line)
	    except FoundationException as e:
		print e.__str__()
	    except Exception as e:
		print e.__str__()
	    finally:
		fileResult.close();
    		            			
    def animate(self):
	currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	currentdir = currentdir + '/' + foundation.agent_properties.result_directory
	print currentdir
	for graphic in self._graphics:
	    filenameNew = self.contructNewName( (self._graphics[graphic]).get('name') )
	    filenameNew = currentdir + filenameNew
	    fileResult = open(filenameNew,"a")
	    try: 
		if ((self._graphics[graphic]).get('detail') == True):
		    # Establish the file content when the user wants the detail
		    for bidId in self._list_vars['Related_Bids']:
			bid = (self._list_vars['Related_Bids'])[bidId]
			if (bid._status == Bid.ACTIVE):
			    xValue, yValue, colorValue, labelValue, column1, column2, column3, column4 = self.setBidInformationToShow(bid, self._graphics[graphic])
			    line, printed = self.constructLineDetail(xValue, yValue, colorValue, labelValue, 
							    column1, column2, column3, column4)
			    if printed == False:
				logger.debug('bid: %s - data could not printed:' + bidId )
			    fileResult.write(line + os.linesep)
		    
		    # Look for bids exchanged in inactive status that have been used for purchases
		    for bidId in self._list_vars['Current_Bids']:
			bid = (self._list_vars['Current_Bids'])[bidId]
			if (bid._status == Bid.INACTIVE):
			    xValue, yValue, colorValue, labelValue, column1, column2, column3, column4 = self.setBidInformationToShow(bid, self._graphics[graphic])
			    line, printed = self.constructLineDetail(xValue, yValue, colorValue, labelValue, 
							    column1, column2, column3, column4)
			    if printed == False:
				logger.debug('bid: %s - data could not printed:' + bidId )
			    fileResult.write(line + os.linesep)
			    
		else:
		    # Establish the file content when the user wants aggregate
		    aggregation = {}
		    for bidId in self._list_vars['Related_Bids']:
			bid = (self._list_vars['Related_Bids'])[bidId]
			if (bid._status == Bid.ACTIVE):
			    xValue, yValue, colorValue, labelValue, column1, column2, column3, column4 = self.setBidInformationToShow(bid, self._graphics[graphic])
			    if ((xValue is not None) and (yValue is not None)):
				aggregation.setdefault(xValue,0)
				aggregation[xValue] += yValue
		    
		    # Look for bids exchanged in inactive status that have been used for purchases
		    for bidId in self._list_vars['Current_Bids']:
			bid = (self._list_vars['Current_Bids'])[bidId]
			if (bid._status == Bid.INACTIVE):
			    xValue, yValue, colorValue, labelValue, column1, column2, column3, column4 = self.setBidInformationToShow(bid, self._graphics[graphic])
			    if ((xValue is not None) and (yValue is not None)):
				aggregation.setdefault(xValue,0)
				aggregation[xValue] += yValue
		    
		    # Print aggregations.
		    for xValue in aggregation:
			line, printed = self.constructLineDetail(xValue, aggregation[xValue], 0, '', '','','','')
			fileResult.write(line + os.linesep)
	    except FoundationException as e:
		print e.__str__()
	    except Exception as e:
		print e.__str__()
	    finally:
		fileResult.close();
	    logger.debug('filenameNew:' + filenameNew )
							    	 
    def exec_algorithm(self):
        '''
	This method checks if the service provider is able to place an 
	offer in the marketplace, i.e. if the offering period is open.
	If this is the case, it will place the offer at the best position
	possible.
	'''
        logger.debug('The state for agent %s is %s', 
			self._list_vars['Id'], str(self._list_vars['State']))
        if (self._list_vars['State'] == AgentServerHandler.ACTIVATE):
	    logger.info('Plotting information in agent %s in the period %s', 
			   self._list_vars['Id'], 
			   str(self._list_vars['Current_Period']))

	    logger.debug('Number of bids: %s ',	
			len(self._list_vars['Related_Bids']) )
	    
	    if (self._list_vars['Related_Bids'] == 0):
		logger.debug('Nothing to present' )
	    else:
		# By assumption providers at this point have the bid usage updated.
		self.animate()

	self._list_vars['State'] = AgentServerHandler.IDLE
	logger.info('Ending exec_algorithm in agent %s in the period %s', 
		    self._list_vars['Id'], 
		    str(self._list_vars['Current_Period']))

    def run(self):
	'''
	The run method is responsible for activate the socket to send 
	the offer to the marketplace. Then, close down the sockets
	to the marketplace and the simulation environment (demand server).
	'''
        proc_name = self.name
        self.start_listening()
	self.initializeFileResults()
	print 'Go to exec_algorithm, state:' + str(self._list_vars['State'])
	try:
	    while (self._list_vars['State'] != AgentServerHandler.TERMINATE):
		if self._list_vars['State'] == AgentServerHandler.ACTIVATE:
		    self.exec_algorithm()
		time.sleep(0.01)
		print 'Come from exec_algorithm, state:' + str(self._list_vars['State'])
	except FoundationException as e:
	    print e.__str__()
	except ProviderException as e:
	    print e.__str__()
	except Exception as e:
	    print e.message

	finally:
	    # Close the sockets
	    self._server.stop()
	    self._channelMarketPlace.close()
	    self._channelClockServer.close()
	    for provider in self._provider_channels:
		print 'Shutdown Provider:' + provider
		(self._provider_channels[provider]).close()
	    return		
		
	
	
# End of Provider class
