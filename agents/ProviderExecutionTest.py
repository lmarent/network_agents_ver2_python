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



logger = logging.getLogger('provider_application')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('providers_logs.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def createBid(strProv, serviceId, delay, price):
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("1", delay)  # Delay
    bid.setDecisionVariable("2", price)     # Price
    bid.setStatus(Bid.ACTIVE)
    return bid


def load_classes(list_classes):
    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    sys.path.append(currentdir)
    agents_directory = currentdir
    black_list = ['ProviderExecution', 'ProviderAgentException','ProviderExecutionTest']
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
	    adaptationFactor, monopolistPosition, debug, 
	    resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod):
    print 'In create provider - Class requested:' + str(typ)
    print list_classes
    if typ in list_classes:
        	targetClass = list_classes[typ]
        	return targetClass(providerName, providerId, serviceId, providerSeed, 
        			   marketPositon, adaptationFactor, monopolistPosition, 
        			   debug, resources, numberOffers, numAccumPeriods, 
        			   numAncestors, startFromPeriod)
    else:
        err = 'Class' + typ + 'not found to be loaded'
        raise ProviderException(err)

def deleteDBPreviousInformation(cursor):
    # Delete all the data for the current execution in the database.
    sql = "delete from Network_Simulation.simulation_bid \
            where execution_count in ( select b.execution_count  \
              from Network_Simulation.simulation_generalparameters b )"    
    cursor.execute(sql)
    
    sql = "delete from Network_Simulation.simulation_bid_purchases \
            where execution_count in ( select b.execution_count  \
              from Network_Simulation.simulation_generalparameters b )"
    cursor.execute(sql)

    sql = "delete from Network_Simulation.simulation_bid_decision_variable \
            where execution_count in ( select b.execution_count  \
              from Network_Simulation.simulation_generalparameters b )"
    cursor.execute(sql)

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

def insertDBBidPurchase(cursor, period, serviceId, executionCount, bid, quantity):
    sql = "insert into Network_Simulation.simulation_bid_purchases(period, \
            serviceId,bidId,quantity, execution_count) values (%s, %s, %s, %s, %s)"    
    args = (period, serviceId, bid.getId(), quantity, executionCount)
    cursor.execute(sql, args )
            

'''
The ProviderExecution starts the threads for the service provider agents.
'''    
if __name__ == '__main__':
    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    # Open database connection
    db = MySQLdb.connect("localhost","root","password","Network_Simulation" )
    
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
		  , microsecond, class_name, start_from_period \
	     FROM simulation_provider \
	    WHERE status = 'A' AND id = 1"

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
            class_name = row[16]
            startFromPeriod = row[17]
            providerSeed = getSeed(seed, year, month, day, hour, minute, second, microsecond)
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
        			      numAccumPeriods, numAncestors, startFromPeriod)
            providers.append(provider)
            i = i + 1
            break
        # start the providers
        provider = providers[0]
                
        deleteDBPreviousInformation(cursor)
        serviceId = '2'        
        delay = 20
        price = 0.14 
        executionCount = getExecutionCount(cursor)         
                
        bid = createBid( provider.getProviderId(), serviceId, delay, price)
        bid.setId('bf6632ce-1c7a-11e6-acae-080027fc03c6')
        bid.setCreationPeriod(3)
        insertDBBid(cursor, 3, executionCount, bid)
        insertDBBidPurchase(cursor, 3, serviceId, executionCount, bid, 10)
        insertDBBidPurchase(cursor, 4, serviceId, executionCount, bid, 7)
        
        bid2 = provider.copyBid(bid)
        if (bid2.isEqual(bid) == False):
            raise FoundationException("copyBid Function Error")
                            
        competitor_bids = {}
        bid2 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid2.setId('bf679646-1c7a-11e6-acae-080027fc03c6')
        bid2.setCreationPeriod(5)
        insertDBBid(cursor, 5, executionCount, bid2)
        insertDBBidPurchase(cursor, 5, serviceId, executionCount, bid2, 6)
        insertDBBidPurchase(cursor, 6, serviceId, executionCount, bid2, 5)
        
        competitor_bids[bid2.getId()] = bid2
        bid3 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid3.setId('bf692efc-1c7a-11e6-acae-080027fc03c6')
        bid3.setCreationPeriod(7)
        insertDBBid(cursor, 7, executionCount, bid3)
        insertDBBidPurchase(cursor, 7, serviceId, executionCount, bid3, 7)
        insertDBBidPurchase(cursor, 8, serviceId, executionCount, bid3, 3)
        
        competitor_bids[bid3.getId()] = bid3
        bid4 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid4.setId('bf695e04-1c7a-11e6-acae-080027fc03c6')
        bid4.setCreationPeriod(9)
        insertDBBid(cursor, 9, executionCount, bid4)
        insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid4, 7)
        
        competitor_bids[bid4.getId()] = bid4
        bid5 = createBid( provider.getProviderId(), serviceId, delay, price)                
        bid5.setId('bf697f4c-1c7a-11e6-acae-080027fc03c6')
        bid5.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid5)
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid5, 5)
        
        competitor_bids[bid5.getId()] = bid5
        marketZoneDemand, totQuantity = provider.getDBMarketShareZone(bid,competitor_bids,3,1)

        # Verifies the number of ancestors.
        numAncestor = provider.getNumAncestors()
        
        # Verifies bids are Neighborhood Bids
        delay = 19.9
        bid6 = createBid( provider.getProviderId(), serviceId, delay, price)
        valReturn = provider.areNeighborhoodBids(bid, bid6)
        if (valReturn != True):
            raise FoundationException("Bids are not close")
        
        delay = 18
        price = 0.3
        bid7 = createBid( provider.getProviderId(), serviceId, delay, price)
        valReturn = provider.areNeighborhoodBids(bid, bid7)
        if (valReturn != False):
            raise FoundationException("Bids are not close")
                        
        # verifies getDBBidMarketShare
        bidDemand, totQuantity = provider.getDBBidMarketShare(bid5.getId(),  10, 1)
        if (totQuantity != 5):
            raise FoundationException("error in getDBBidMarketShare")
                
        # verifies getDBBidAncestorsMarketShare
        bid5.insertParentBid(bid4)
        bid4.insertParentBid(bid3)
        bid3.insertParentBid(bid2)
        bid2.insertParentBid(bid)

        bidDemand2, totQuantity2 = provider.getDBBidAncestorsMarketShare(bid5, 10, 4)
        if (totQuantity2 != 22):
            raise FoundationException("error in getDBBidAncestorsMarketShare")
        
        provider._list_vars['Current_Period'] = 11        
        
        bid6.insertParentBid(bid5)

        delay = 20
        price = 0.14 
        # include a lot of related bids in order to test the function getRelatedBids
        bid7 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid7.setCreationPeriod(7)        
        (provider._list_vars['Related_Bids'])[bid7.getId()] = bid7
        bid8 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid8.setCreationPeriod(7)
        (provider._list_vars['Related_Bids'])[bid8.getId()] = bid8
        bid9 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid9.setCreationPeriod(8)
        (provider._list_vars['Related_Bids'])[bid9.getId()] = bid9
        bid10 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid10.setCreationPeriod(8)        
        (provider._list_vars['Related_Bids'])[bid10.getId()] = bid10
        bid11 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid11.setCreationPeriod(9)        
        (provider._list_vars['Related_Bids'])[bid11.getId()] = bid11

        insertDBBid(cursor, 9, executionCount, bid11)
        insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid11, 9)

        bid12 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid12.setCreationPeriod(9)
        (provider._list_vars['Related_Bids'])[bid12.getId()] = bid12

        insertDBBid(cursor, 9, executionCount, bid12)
        insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid12, 8)

        bid13 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid13.setCreationPeriod(10)        
        (provider._list_vars['Related_Bids'])[bid13.getId()] = bid13

        insertDBBid(cursor, 10, executionCount, bid13)
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid13, 7)

        bid14 = createBid( provider.getProviderId(), serviceId, delay, price)
        bid14.setCreationPeriod(10)
        (provider._list_vars['Related_Bids'])[bid14.getId()] = bid14

        insertDBBid(cursor, 10, executionCount, bid14)
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid14, 7)
                        
        # verifies calculateMovedBidForecast
        marketZoneDemand1, forecast1 = provider.calculateMovedBidForecast(bid5, bid6, Provider.MARKET_SHARE_ORIENTED)
        marketZoneDemand2, forecast2 = provider.calculateMovedBidForecast(bid5, bid6, Provider.PROFIT_ORIENTED)

        if (forecast1 < 6) or (forecast1 > 7):
            raise FoundationException("error in calculateMovedBidForecast MARKET_SHARE")

        if (forecast2 < 5) or (forecast2 > 6):
            raise FoundationException("error in calculateMovedBidForecast PROFIT_ORIENTED")

        
        # verifies moveBid
        staged_bids = {}        
        provider.moveBid(bid5, moveDirections, 0, staged_bids, Provider.MARKET_SHARE_ORIENTED, fileResult)
	
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        	# disconnect from server
        	db.close()
