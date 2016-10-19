import multiprocessing
from Provider import Provider
from ProviderAgentException import ProviderException
from foundation.FoundationException import FoundationException
import foundation.agent_properties
import MySQLdb
import logging
import datetime
import os
import sys
import re
import inspect
from foundation.Bid import Bid
import uuid
from foundation.Agent import Agent
from foundation.AgentType import AgentType
from foundation.DecisionVariable import DecisionVariable




logger = logging.getLogger('provider_application')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('providers_test.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def createBid(strProv, serviceId, delay, price):
    '''
    Create an edge provider bid
    '''
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("1", price)  #Price
    bid.setDecisionVariable("2", delay)     # Delay
    bid.setStatus(Bid.ACTIVE)
    return bid

def createBidService2(strProv, serviceId, quality, price):
    '''
    Create a transit provider bid
    '''
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("3", quality)  # quality
    bid.setDecisionVariable("4", price)     # Price
    bid.setStatus(Bid.ACTIVE)
    return bid


def load_classes(list_classes):
    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    sys.path.append(currentdir)
    agents_directory = currentdir
    black_list = ['ProviderExecution', 'ProviderAgentException','ProviderExecutionTest', 'ProviderEdgeTest', 'ProviderPublicTest']
    for filename in os.listdir (agents_directory):
        	# Ignore subfolders
        	if os.path.isdir (os.path.join(agents_directory, filename)):
        	    continue
        	else:
        	    if re.match(r"Provider.*?\.py$", filename):
        		classname = re.sub(r".py", r"", filename)
        		if (classname not in black_list):
        		    module = __import__(classname)
        		    targetClass = getattr(module, classname)
        		    list_classes[classname] = targetClass   
    logging.debug('Load Providers Classes initialized')


def getGeneralConfigurationParameters(cursor):
    sql = "SELECT bid_periods, initial_offer_number, \
		  num_periods_market_share \
	     FROM simulation_generalparameters limit 1" 
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
        	bidPeriods = row[0]
        	numberOffers = row[1]
        	numAccumPeriods = row[2]
        	break
    return bidPeriods, numberOffers, numAccumPeriods

def getSeed(seed, year, month, day, hour, minute, second, microsecond):
    if (seed == 1):
        	# the seed for random numbers was defined, therefore we use it.
        	dtime = datetime.datetime(year,month,day,hour,minute,second,microsecond)
    else:
        dtime = datetime.datetime.now()		
    return dtime

def create(list_classes, typ, providerName, providerId, serviceId, providerSeed, marketPositon, 
	    adaptationFactor, monopolistPosition, debug, resources, numberOffers, 
        numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, 
        capacityControl, purchase_service):
    print 'In create provider - Class requested:' + str(typ)
    print list_classes
    if typ in list_classes:
        	targetClass = list_classes[typ]
        	return targetClass(providerName, providerId, serviceId, providerSeed, 
        			   marketPositon, adaptationFactor, monopolistPosition, 
        			   debug, resources, numberOffers, numAccumPeriods, 
        			   numAncestors, startFromPeriod, sellingAddress, buyingAddress, 
                    capacityControl, str(purchase_service))
    else:
        err = 'Class' + typ + 'not found to be loaded'
        raise ProviderException(err)

def getExecutionCount(cursor):
    executionCount = 0    
    sql = "select execution_count from Network_Simulation.simulation_generalparameters limit 1"
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
        executionCount = int(row[0])
        break
    if (executionCount == 0):
        raise FoundationException("execution count not defined")
    return executionCount


def insertDBBid(cursor, period, executionCount, bid):
    sql = "insert into Network_Simulation.simulation_bid (period, bidId, providerId, \
            status, paretoStatus,dominatedCount, execution_count) \
                values (%s, %s, %s, %s, %s, %s, %s)"    
    args = (period, bid.getId(), bid.getProvider(), 1, 0, 0, executionCount)
    cursor.execute(sql, args )

def insertDBBidPurchase(cursor, period, serviceId, executionCount, bidId, quantity):
    sql = "insert into Network_Simulation.simulation_bid_purchases(period, \
            serviceId,bidId,quantity, execution_count) values (%s, %s, %s, %s, %s)"    
    args = (period, serviceId, bidId, quantity, executionCount)
    cursor.execute(sql, args )

def sendBid(bid, action, provider):
    bid.setStatus(action)
    message = bid.to_message()
    messageResult = provider.sendMessageMarket(message)
    if messageResult.isMessageStatusOk():
        pass

def test_initialization(provider):
    provider.start_agent()
    provider.initialize()
    
    if ((provider._list_vars['Type']).getType() != AgentType.PROVIDER_BACKHAUL):
        raise FoundationException("error in test_initialization, we are expecting a backhaul provider")        
                
'''
The ProviderExecution starts the threads for the service provider agents.
'''    
if __name__ == '__main__':

    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    # Open database connection
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database, \
                           foundation.agent_properties.user_password,foundation.agent_properties.database_name)
        
    db.autocommit(1)    
    
    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # Brings the general parameters from the database
    bidPeriods, numberOffers, numAccumPeriods = getGeneralConfigurationParameters(cursor)
    
    # Verifies if they were configured, otherwise brings them from the agent properties.
    if (numberOffers == 0):
        numberOffers = foundation.agent_properties.initial_number_bids
    
    if (numAccumPeriods == 0):
        numAccumPeriods = foundation.agent_properties.num_periods_market_share

    # Prepare SQL query to SELECT providers from the database.
    sql = "SELECT id, name, market_position, adaptation_factor \
                  , monopolist_position, service_id, num_ancestors, debug \
		  , seed, year, month, day, hour, minute, second \
		  , microsecond, class_name, start_from_period, buying_marketplace_address \
          , selling_marketplace_address, capacity_controlled_at, purchase_service_id \
	     FROM simulation_provider \
	     WHERE id = 2"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()
        i = 1
        for row in results:
            providerId = row[0]
            providerName = row[1]
            marketPositon = row[2] 
            adaptationFactor = row[3] 
            monopolistPosition = row[4] 
            serviceId = str(row[5])
            numAncestors = row[6]
            if (row[7] == 1):
                debug = True
            else:
                debug = False
            seed = row[8]
            year = row[9]
            month = row[10]
            day = row[11]
            hour = row[12]
            minute = row[13]
            second = row[14]
            microsecond = row[15]
            class_name = 'ProviderPublic'
            startFromPeriod = row[17]
            buyingAddress = row[18]
            sellingAddress = row[19]
            capacityControl = 'G' # Bulk Capacity.
            providerSeed = getSeed(seed, year, month, day, hour, minute, second, microsecond)
            purchase_service = row[21]
            # Brings resources definition
            cursor2 = db.cursor()
            sql_resources = "SELECT resource_id, capacity, cost \
        			       FROM simulation_provider_resource \
        			      WHERE provider_id = '%d'" % (providerId)
            cursor2.execute(sql_resources)
            resourceRows = cursor2.fetchall()
            resources = {}
            for resourceRow in resourceRows:
                resources[str(resourceRow[0])] = {'Capacity': resourceRow[1], 'Cost' : resourceRow[2]}
        	    
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceId, 
        			      providerSeed, marketPositon, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, 
                       buyingAddress, capacityControl, purchase_service)
            providers.append(provider)
            i = i + 1

        logger.info('Starting test public provider')
            
        # Test providers' initialization.
        provider1 = providers[0] # Public provider
        
        fileResult1 = open(provider1.getProviderId() + '.log',"a")
        
        test_initialization(provider1)
        radius = 0.05
        output = provider1.initializeBidParameters(radius, fileResult1)
        if len(output) != 20:
            raise FoundationException("We expect 20 outputs - numCalculated:" + str(len(output)))
        
        # The following code verifies some of the outputs. The decision variables are 3 and 4.
                
        if ((output[0])['3'] != 0):
            raise FoundationException("We expect quality 0 for output 0 - numCalculated:" + str((output[0])['3']))

        print 'Here we are'
        quality = (output[3])['3']
        if ( round(quality,2) != 0.15):
            raise FoundationException("We expect quality 0.15 for output 3 - numCalculated:" + str(quality))

        quality = (output[6])['3']
        if ( round(quality,1) != 0.3):
            raise FoundationException("We expect quality 0.3 for output 6 - numCalculated:" + str(quality))

        quality = (output[7])['3']
        if ( round(quality,2) != 0.35):
            raise FoundationException("We expect quality 0.35 for output 7 - numCalculated:" + str(quality))
        
        quality = (output[15])['3']
        if ( round(quality,2) != 0.75):
            raise FoundationException("We expect quality 0.75 for output 15 - numCalculated:" + str(quality))

        print 'Here we are'
        
        # cost function is equal to : 1 + 0.5(x), where x is the quality.
        # The unitary cost by resource is 9.
        # So the total cost is 9 * (1 + 0.5(x))

        price = (output[0])['4']
        if ( round(price, 0) != 9):
            raise FoundationException("We expect price 9 for output 0 - numCalculated:" + str(price) )

        price = (output[3])['4']
        if ( round(price,3) != 9.675):
            raise FoundationException("We expect price 9.675 for output 3 - numCalculated:" + str(price) )

        price = (output[6])['4']
        if ( round(price,2) != 10.35):
            raise FoundationException("We expect price 10.35 for output 4 - numCalculated:" + str(price) )

        price = (output[7])['4']
        if ( round(price,3) != 10.575):
            raise FoundationException("We expect price 10.575 for output 7 - numCalculated:" + str(price) )
        
        price = (output[15])['4']
        if ( round(price,3) != 12.375):
            raise FoundationException("We expect price 12.375 for output 15 - numCalculated:" + str(price) )
        
        staged_bids = provider1.initializeBids(radius, fileResult1)
        if len(staged_bids) != 20:
            raise FoundationException("We expect 20 bids - numCalculated:" + str(len(staged_bids)))
        
        # The following lines test the maintain bis. 

        provider1.sendBids(staged_bids, fileResult1) #Pending the status of the bid.
        
        bidId1 = ''
        bid1 = None
        bidId2 = ''
        bid2 = None
        bidId3 = ''
        bid3 = None
        bidId4 = ''
        bid4 = None
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            quality = bid.getDecisionVariable('3')
            if (round(quality,2) == 0.05):
                bidId1 = bidId
                bid1 = bid
            elif (round(quality,2) == 0.15):
                bidId2 = bidId
                bid2 = bid
            elif (round(quality,2) == 0.45):
                bidId3 = bidId
                bid3 = bid
            elif (round(quality,2) == 0.0):
                bidId4 = bidId
                bid4 = bid
        
        distance = provider1.distance((staged_bids[bidId4])['Object'], (staged_bids[bidId1])['Object'], fileResult1)
        
        logger.info('distance bid 0' + bidId4 )   
        logger.info('distance bid 0.05' + bidId1 )   
        logger.info('distance bid 0.15' + bidId2 )   
        logger.info('distance bid 0.45' + bidId3 )   
        
        logger.info('distance bid0-bid1' + str(distance) )   
        
        provider1.purgeBids(staged_bids, fileResult1)
        
        period = 1
        executionCount = getExecutionCount(db.cursor())
        insertDBBidPurchase(db.cursor(), period, provider1.getServiceId(), executionCount, bidId1, 5)        
        insertDBBidPurchase(db.cursor(), period, provider1.getServiceId(), executionCount, bidId1, 6)        
        insertDBBidPurchase(db.cursor(), period, provider1.getServiceId(), executionCount, bidId1, 3)        
        
        insertDBBidPurchase(db.cursor(), period, provider1.getServiceId(), executionCount, bidId2, 4)        
        insertDBBidPurchase(db.cursor(), period, provider1.getServiceId(), executionCount, bidId2, 5)        
        insertDBBidPurchase(db.cursor(), period, provider1.getServiceId(), executionCount, bidId2, 2)        

        insertDBBidPurchase(db.cursor(), period, provider1.getServiceId(), executionCount, bidId3, 3)        
        insertDBBidPurchase(db.cursor(), period, provider1.getServiceId(), executionCount, bidId3, 4)        
        insertDBBidPurchase(db.cursor(), period, provider1.getServiceId(), executionCount, bidId3, 1)        
        
        
        staged_bids = {}
        provider1.maintainBids(2, radius, provider1.getServiceId(), staged_bids, fileResult1)
        
        if len(staged_bids) != 40:
            raise FoundationException("We expect 40 bids - numCalculated:" + str(provider1.countByStatus(staged_bids)))
        
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            quality = bid.getDecisionVariable('3')
            status = (staged_bids[bidId])['Action']
            forecast = (staged_bids[bidId])['Forecast']
            orientation = Provider.MARKET_SHARE_ORIENTED
            if round(quality,2) == 0.05:
                marketZoneDemand, totForecast = provider1.calculateMovedBidForecast(2, radius, bid1, bid, orientation, fileResult1)
                logger.info('Forecast new bid0' + str(totForecast) ) 
                
        for bidId in staged_bids:
            bid = (staged_bids[bidId])['Object']
            quality = bid.getDecisionVariable('3')
            status = (staged_bids[bidId])['Action']
            forecast = (staged_bids[bidId])['Forecast']
            if status == Bid.ACTIVE:
                if (round(quality,2) == 0.05):
                    if (forecast != 14):
                        raise FoundationException("We expect a forecast of 14 - found:" + str(forecast))
                    
                elif (round(quality,2) == 0.15):
                    if (forecast != 11):
                        raise FoundationException("We expect a forecast of 11 - found:" + str(forecast))
                    
                elif (round(quality,2) == 0.45):
                    if (forecast != 8):
                        raise FoundationException("We expect a forecast of 8 - found:" + str(forecast))
                    
                
        provider1.eliminateNeighborhoodBid(staged_bids, fileResult1)
        if len(staged_bids) != 40:
            raise FoundationException("We expect 40 bids - numCalculated:" + str(provider1.countByStatus(staged_bids)))
        
        
        logger.info('Ending test public provider')
                                     
        pass        
	
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        # disconnect from server
        db.close()
        provider1.stop_agent() # Edge provider
        fileResult1.close()
