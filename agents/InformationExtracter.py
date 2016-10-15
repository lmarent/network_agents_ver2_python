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
import MySQLdb

logger = logging.getLogger('presenter')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('presenter.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

class InformationExtracter:
    '''
    The Provider class defines methods to be used by the service
    provider agent. It includes methods for pricing and quality
    strategies, place offerings into the marketplace, get other 
    providers offerings and determine the best strategy to capture 
    more market share.    
    '''

    def __init__(self, execution_count, graphics):
        try:

            self._provider_colors = {}   # maintains the colors used for providers.
            self._graphics = graphics
            self._provider_channels = {}
            self._execution_count = execution_count
            
            self._db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
                    foundation.agent_properties.user_password,foundation.agent_properties.database_name )
                
            self._db.autocommit(1)

        except FoundationException as e:
            raise ProviderException(e.__str__())

    def obtainDecisionParameters(self, decisionVariable):
        logger.info('Initializing obtainDecisionParameters:' + decisionVariable )
        label = None
        min_value = 0
        max_value = 0
        cursor = self._db.cursor() 
        sql = 'select a.name, a.min_value, a.max_value \
                from simulation_decisionvariable a \
                where a.id = %s'
        cursor.execute(sql, (decisionVariable))
        results = cursor.fetchall()
        period = 0
        for row in results:
            label = row[0]
            min_value = row[1]
            max_value = row[2]
            break
        logger.info('Ending obtainDecisionParameters:' + label + str(min_value) + str(max_value) )
        return label, min_value, max_value

    def setHeaderLine(self, decisionVariableX, decisionVariableY):
        logger.debug('Initializing setHeaderLine' )
        line ='period,'
        if (decisionVariableX.get('type') == 'D'):
            idVariable = decisionVariableX.get('decision_variable')
            label, min_value, max_value = self.obtainDecisionParameters(cursor, idVariable)
            if (label == None): # The decision variable is not configured in the DB server
                return None
            line = line + label + ',' + '{0}'.format(min_value) 
            line = line + ',' + '{0}'.format(max_value) 
        else:
            line = line + decisionVariableX.get('name') + ',' '{0}'.format(0)
            line = line + ',' + '{0}'.format(0)

        if  (decisionVariableY.get('type') == 'D'):
            idVariable = decisionVariableY.get('decision_variable')
            label, min_value, max_value = self.obtainDecisionParameters(cursor, idVariable)
            if (label == None): # The decision variable is not configured in the DB server
                return None
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
        cursor = self._db.cursor()
        quantity = 0
        sql = 'select a.quantity, a.qty_backlog \
                from simulation_bid_purchases a \
               where a.execution_count = %s \
                 and a.period = %s and a.bidId = %s' 
        cursor.execute(sql, (self._execution_count, bid.getCreationPeriod(), bid.getId() ))
        results = cursor.fetchall()
        totQuantity = 0
        for row in results:
            totQuantity = totQuantity + float(row[0])
        logger.debug('Ending getQuantity' + str(quantity) )
        return totQuantity

    def getUnitaryCost(self, bid):
        logger.debug('Initializing getUnitaryCost' + bid.getId() )
        cost = bid.getUnitaryCost()
        logger.debug('Ending getUnitaryCost:' + str(cost) )
        return cost

    def getPrice(self, bid):
        logger.debug('Initializing getPrice' + bid.getId() )
        print 'aqui vamos ----------------------------------------'
        cursor = self._db.cursor()
        price = 0
        sql = 'select distinct b.value \
                from simulation_bid a, \
                     simulation_bid_decision_variable b, \
                     simulation_decisionvariable c \
               where a.execution_count = %s \
                 and a.status = %s \
                 and a.bidId = parentId \
                 and a.execution_count = b.execution_count \
                 and c.id = b.decisionVariableName \
                 and a.bidId = %s \
                 and c.modeling = %s'
        print sql
        cursor.execute(sql, (self._execution_count, 1, bid.getId(), 'P'))
        results = cursor.fetchall()
        for row in results:
            price = price + float(row[0])
        logger.debug('Ending getPrice' + str(price) )
        return price

    def getDecisionVariable(self, bid, decisionVariable):
        logger.debug('Initializing getDecisionVariable' + bid.getId() + 'Decision Variable:' + decisionVariable)
        cursor = self._db.cursor()
        value = 0
        sql = 'select distinct b.value \
                from simulation_bid a, \
                     simulation_bid_decision_variable b, \
                     simulation_decisionvariable c \
                where a.execution_count = %s \
                  and a.status = %s \
                  and a.bidId = parentId \
                  and a.execution_count = b.execution_count \
                  and c.id = b.decisionVariableName \
                  and a.bidId = %s \
                  and c.id = %s'
        cursor.execute(sql, (self._execution_count, 1, bid.getId(), decisionVariable))
        results = cursor.fetchall()
        for row in results:
            print 'here we are'
            value = value + float(row[0])
        logger.debug('Ending getDecisionVariable' + str(value) )
        return value

    def getProfit(self, bid):
        logger.debug('Initializing getProfit' + bid.getId() )
        profit = bid.getUnitaryProfit()
        totQuantity = self.getQuantity(bid)
        profit = profit * totQuantity
        logger.debug('Ending getProfit' + str(profit) )
        return profit

    def getIncome(self, bid):
        logger.debug('Initializing getIncome' + bid.getId() )
        quantity = self.getQuantity(bid)
        price = self.getPrice(bid)
        income = quantity * price
        logger.debug('Ending getIncome' + str(income) )
        return income

    def getProvider(self, bid):
        return bid.getProvider()

    def getId(self, bid):
        return bid.getId()

    def obtainOfferedValue(self, bid, offeredValue):
        logger.debug('Initializing obtainOfferedValue' + offeredValue.__str__())
        # The offered value could not be defined by users.
        if ('type' in offeredValue):
            if (offeredValue['type'] == 'D'): 
                value = self.getDecisionVariable(bid, offeredValue['decision_variable'])
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

    def constructLineDetail(self, period, xValue, yValue, colorValue, labelValue, 
                            column1, column2, column3, column4):
        line = str(period) + ','
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
        logger.debug('Starting initializeFileResults')
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
                fileResult.close()
        logger.debug('Starting initializeFileResults')

    def createBid(self, bidId, strProv, serviceId, period, unitary_cost, unitary_profit, capacity ):
        bid = Bid()
        bid.setValues(bidId, strProv, serviceId)
        bid.setStatus(Bid.ACTIVE)
        bid.setUnitaryProfit(unitary_profit)
        bid.setUnitaryCost(unitary_cost)
        bid.setCreationPeriod(period)
        bid.setCapacity(capacity)
        return bid        

    def animate_detail(self, graphic, fileResult):
        logger.debug('Starting animate_detail')
        cursor = self._db.cursor()
        sql =  'select a.period, a.providerId, a.bidId, a.unitary_profit, \
                       a.parentBidId, a.unitary_cost, a.init_capacity \
                  from simulation_bid a \
                  where a.execution_count = %s \
                    and a.status = %s \
                    and a.bidId = %s\
                  order by a.period'
        cursor.execute(sql, (self._execution_count, '1','da3b04e8-922d-11e6-a762-02cc991d7c17'))
        results = cursor.fetchall()
        for row in results:
            period = int(row[0]) 
            providerId = row[1]
            bidId = row[2]
            unitary_profit = float(row[3])
            parentBidId = row[4]
            unitary_cost = row[5]
            init_capacity = float(row[5])
            bid = self.createBid(bidId, providerId, '', period, unitary_cost, unitary_profit, init_capacity )
            xValue, yValue, colorValue, labelValue, column1, column2, column3, column4 = self.setBidInformationToShow(bid, self._graphics[graphic])
            line, printed = self.constructLineDetail(period,xValue, yValue, colorValue, labelValue, column1, column2, column3, column4)
            if printed == False:
                logger.debug('bid: %s - data could not printed:' + bidId )
            fileResult.write(line + os.linesep)
        logger.debug('Ending animate_detail')

    def animate_aggregate(self, graphic, fileResult):
        logger.debug('Starting animate_aggregate')
        cursor = self._db.cursor()
        sql =  'select a.period, a.providerId, a.bidId, a.unitary_profit, \
                       a.parentBidId, a.unitary_cost, a.init_capacity \
                  from simulation_bid a \
                  where a.execution_count = %s \
                    and a.status = %s \
                    and a.bidId = %s'
        cursor.execute(sql, (self._execution_count, '1','da3b04e8-922d-11e6-a762-02cc991d7c17'))
        results = cursor.fetchall()
        for row in results:
            period = int(row[0]) 
            providerId = row[1]
            bidId = row[2]
            unitary_profit = float(row[3])
            parentBidId = row[4]
            unitary_cost = row[5]
            init_capacity = float(row[5])
            bid = self.createBid(bidId, providerId, '', period, unitary_cost, unitary_profit, init_capacity )
            aggregation = {}
            xValue, yValue, colorValue, labelValue, column1, column2, column3, column4 = self.setBidInformationToShow(bid, self._graphics[graphic])
            if ((xValue is not None) and (yValue is not None)):
                aggregation.setdefault(xValue,0)
                aggregation[xValue] += yValue

            # Print aggregations.
            for xValue in aggregation:
                line, printed = self.constructLineDetail(0, xValue, aggregation[xValue], 0, '', '','','','')
            fileResult.write(line + os.linesep)
        logger.debug('Ending animate_aggregate')

    def animate(self):
        logger.debug('Starting animate')
        currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        currentdir = currentdir + '/' + foundation.agent_properties.result_directory
        print currentdir
        for graphic in self._graphics:
            filenameNew = self.contructNewName( (self._graphics[graphic]).get('name') )
            filenameNew = currentdir + filenameNew
            fileResult = open(filenameNew,"a")
            try: 
                if ((self._graphics[graphic]).get('detail') == True):
                    self.animate_detail(graphic, fileResult)
                else:
                    self.animate_aggregate(graphic, fileResult)
            except FoundationException as e:
                print e.__str__()
            except Exception as e:
                print e.__str__()
            finally:
                fileResult.close();
            logger.debug('filenameNew:' + filenameNew )
        logger.debug('Ending animate')

# End of Information Extracter class