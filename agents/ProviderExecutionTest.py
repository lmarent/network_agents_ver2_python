import multiprocessing
from Provider import Provider
from ProviderAgentException import ProviderException
from foundation.FoundationException import FoundationException
import foundation.agent_properties
import MySQLdb
import logging
import datetime
import time
import os
import sys
import re
import inspect
from foundation.Bid import Bid
import uuid
from foundation.Agent import AgentServerHandler
from foundation.Agent import Agent




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
    bid.setDecisionVariable("1", price)  #Price
    bid.setDecisionVariable("2", delay)     # Delay
    bid.setStatus(Bid.ACTIVE)
    return bid

def createBidBackhaul(strProv, serviceId, delay, price):
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("4", price)  #Price
    bid.setDecisionVariable("3", delay)     # Delay
    bid.setStatus(Bid.ACTIVE)
    return bid


def createBidWithCapacity(strProv, serviceId, delay, price, capacity):
    bid = Bid()
    uuidId = uuid.uuid1()	# make a UUID based on the host ID and current time
    idStr = str(uuidId)
    bid.setValues(idStr, strProv, serviceId)
    bid.setDecisionVariable("4", price)  #Price
    bid.setDecisionVariable("3", delay)     # Delay
    bid.setStatus(Bid.ACTIVE)
    bid.setCapacity(capacity)
    return bid
    
def load_classes(list_classes):
    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    sys.path.append(currentdir)
    agents_directory = currentdir
    black_list = ['ProviderExecution', 'ProviderAgentException', 'ProviderExecutionTest', 'ProviderEdgeTest']
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
	    resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod,
        sellingAddress, buyingAddress, capacityControl ):
    print 'In create provider - Class requested:' + str(typ)
    print list_classes
    if typ in list_classes:
        	targetClass = list_classes[typ]
        	return targetClass(providerName, providerId, serviceId, providerSeed, 
        			   marketPositon, adaptationFactor, monopolistPosition, 
        			   debug, resources, numberOffers, numAccumPeriods, 
        			   numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
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
            status, paretoStatus,dominatedCount, execution_count, unitary_profit, unitary_cost, capacity) \
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"    
    args = (period, bid.getId(), bid.getProvider(), 1, 0, 0, executionCount, bid.getUnitaryProfit(), bid.getUnitaryCost(), bid.getCapacity())
    cursor.execute(sql, args )

def insertDBBidPurchase(cursor, period, serviceId, executionCount, bid, quantity):
    sql = "insert into Network_Simulation.simulation_bid_purchases(period, \
            serviceId,bidId,quantity, execution_count) values (%s, %s, %s, %s, %s )"    
    args = (period, serviceId, bid.getId(), quantity, executionCount )
    cursor.execute(sql, args )


def test_marketplace_capacity_management():
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
		  , microsecond, class_name, start_from_period, buying_marketplace_address \
          , selling_marketplace_address, capacity_controlled_at \
	     FROM simulation_provider \
	    WHERE status = 'A' AND id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdISP = '1'            
        serviceIdBackhaul = '2'
        adaptationFactor = 0
        monopolistPosition = 0
        marketPosition = 0

        i = 1
        for row in results:
            providerId = row[0]
            providerName = row[1]
            marketPosition = row[2] 
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
            buyingAddress = row[18]
            sellingAddress = row[19]            
            capacityControl = 'G' # Bulk Capacity.
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
            
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)

            i = i + 1

            capacityControl = 'G' # Bulk Capacity.
            class_name = 'ProviderEdge'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_isp
            buyingAddress = foundation.agent_properties.addr_mktplace_backhaul
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdISP, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 

        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)
            i = i + 1

            capacityControl = 'B' # Capacity by Bid.
            class_name = 'Provider'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)
            i = i + 1

            break

        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider2 = providers[1]  # isp provider
        provider3 = providers[2]  # backhaul provider - Bid capacity.

        provider1.start_listening()
        provider1.initialize()
        provider2.start_listening()
        provider2.initialize()
        provider3.start_listening()
        provider3.initialize()

        
        # This code verifies the Market Place Server with BulkCapacity
        # send capacity 10 units
        provider1.send_capacity()
        
        # Variable Initialization        
        serviceId = '2'
        fileResult1 = open(provider1.getProviderId() + '.log',"a")
        currentPeriod = provider2.getCurrentPeriod()
        
        # creates the bid with the minimal quality.                
        quality = 0
        price = 10
        bid = createBidBackhaul(provider1.getProviderId(), serviceId, quality, price)
        bid.setCreationPeriod(1)
        provider1.sendBid(bid, fileResult1)
        
        # Buy with minimum quality 3 units - Response 3 units purchased, provider2 acts as the customer.
        fileResult2 = open(provider1.getProviderId() + '.log',"a")        
        quantity = provider2.purchase(serviceId, bid, 3, fileResult2)
                             
        if (quantity != 3):
            raise FoundationException("error in the purchase function")
            
        # Buy with minimum quality 4 units - Response 4 units purchased
        quantity = provider2.purchase(serviceId, bid, 4, fileResult2)
        if (quantity != 4):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 2 units purchased
        quantity = provider2.purchase(serviceId, bid, 2, fileResult2)
        if (quantity != 2):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 0 units purchased
        quantity = provider2.purchase(serviceId, bid, 2, fileResult2)
        if (quantity != 0):
            raise FoundationException("error in the purchase function")

        # ------------
        # This code verifies the Market Place Server with BidCapacity, provider2 acts as the customer.
        # ------------

        # Variable Initialization        
        serviceId = '2'
        fileResult3 = open(provider3.getProviderId() + '.log',"a")
        currentPeriod = provider3.getCurrentPeriod()
        
        # creates bids with the minimal quality.                
        quality = 0
        price = 10
        bid2 = createBidWithCapacity(provider3.getProviderId(), serviceId, quality, price, 10)
        bid2.setCreationPeriod(1)
        bid3 = createBidWithCapacity(provider3.getProviderId(), serviceId, quality, price, 5)
        bid3.setCreationPeriod(1)
        provider3.sendBid(bid2, fileResult3)
        provider3.sendBid(bid3, fileResult3)
        
        # Buy with minimum quality 5 units - Response 5 units purchased
        quantity = provider2.purchase(serviceId, bid2, 5, fileResult2)
        if (quantity != 5):
            raise FoundationException("error in the purchase function")
            
        # Buy with minimum quality 4 units - Response 5 units purchased
        quantity = provider2.purchase(serviceId, bid2, 6, fileResult2)
        if (quantity != 5):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 2 units purchased
        quantity = provider2.purchase(serviceId, bid3, 2, fileResult2)
        if (quantity != 2):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 2 units purchased
        quantity = provider2.purchase(serviceId, bid3, 2, fileResult2)
        if (quantity != 2):
            raise FoundationException("error in the purchase function")

        # Buy with minimum quality 2 units - Response 1 units purchased
        quantity = provider2.purchase(serviceId, bid3, 5, fileResult2)
        if (quantity != 1):
            raise FoundationException("error in the purchase function")
        
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

def test_provider_general_methods():

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
		  , microsecond, class_name, start_from_period, buying_marketplace_address \
          , selling_marketplace_address, capacity_controlled_at \
	     FROM simulation_provider \
	    WHERE status = 'A' AND id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceId = '1'            
        adaptationFactor = 0
        monopolistPosition = 0
        marketPosition = 0

        i = 1
        for row in results:
            providerId = row[0]
            providerName = row[1]
            marketPosition = row[2] 
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
            buyingAddress = row[18]
            sellingAddress = row[19]            
            capacityControl = 'G' # Bulk Capacity.
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
            
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceId, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)

            i = i + 1

        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
    
        # This code test the method calculateDeltaProfitProgression
        progression = []
        progression.append({'bid' :None, 'profit' : 10, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 9, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 8, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 7, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 6, 'delta_profit' : 0 })
        progression.append({'bid' :None, 'profit' : 5, 'delta_profit' : 0 })
        provider1.calculateDeltaProfitProgression(progression)
        i = 0
        while (i < (len(progression) - 1)):
            if (progression[i])['delta_profit'] != 1:
                raise FoundationException("error in method calculateDeltaProfitProgression")
            i = i + 1

        # This code test the method moving average
        progression2 = []
        progression2.append({'bid' :None, 'profit' : 17, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : 12, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : 8, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : 4, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : 2, 'delta_profit' : 0 })
        progression2.append({'bid' :None, 'profit' : -1, 'delta_profit' : 0 })
        provider1.calculateDeltaProfitProgression(progression2)
        estimate = provider1.movingAverage(progression2)
        if round(estimate,2) != 4.47:
            raise FoundationException("error in method movingAverage")

        progression3 = []
        progression3.append({'bid' :None, 'profit' : 17, 'delta_profit' : 0 })
        provider1.calculateDeltaProfitProgression(progression3)
        if (progression3[0])['delta_profit'] != 17:
            raise FoundationException("error in method calculateDeltaProfitProgression")
        
        estimate = provider1.movingAverage(progression3)
        if estimate != 17:
            raise FoundationException("error in method movingAverage")
        
        progression4 = []
        provider1.calculateDeltaProfitProgression(progression4)
        estimate = provider1.movingAverage(progression4)
        if estimate != 0:
            raise FoundationException("error in method movingAverage")
        

        radius = 0.1        
        delay = 0.18
        price = 15
        bid = createBid( provider1.getProviderId(), serviceId, delay, price)

        # Verifies method bids are Neighborhood Bids
        delay = 0.17
        price = 14.5
        bid6 = createBid( provider1.getProviderId(), serviceId, delay, price)
        valReturn = provider1.areNeighborhoodBids(radius, bid, bid6)
        if (valReturn != True):
            raise FoundationException("Bids are not close")
        
        delay = 0.18
        price = 18
        bid7 = createBid( provider1.getProviderId(), serviceId, delay, price)
        valReturn = provider1.areNeighborhoodBids(radius, bid, bid7)
        if (valReturn != False):
            raise FoundationException("Bids are not close")
        
        provider1.run()

        deleteDBPreviousInformation(cursor)
        executionCount = getExecutionCount(cursor)         


    
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        	# disconnect from server
        	db.close()


def test_provider_database_classes():
    '''
    The ProviderExecution starts the threads for the service provider agents.
    '''    

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
		  , microsecond, class_name, start_from_period, buying_marketplace_address \
          , selling_marketplace_address, capacity_controlled_at \
	     FROM simulation_provider \
	    WHERE status = 'A' AND id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdISP = '1'            
        serviceIdBackhaul = '2'
        adaptationFactor = 0
        monopolistPosition = 0
        marketPosition = 0

        i = 1
        for row in results:
            providerId = row[0]
            providerName = row[1]
            marketPosition = row[2] 
            adaptationFactor = row[3] 
            monopolistPosition = row[4] 
            serviceId = str(row[5])
            numAncestors = 4 # For testing we left four.
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
            buyingAddress = row[18]
            sellingAddress = row[19]            
            capacityControl = 'G' # Bulk Capacity.
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
            
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)


            i = i + 1

            capacityControl = 'G' # Bulk Capacity.
            class_name = 'ProviderEdge'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_isp
            buyingAddress = foundation.agent_properties.addr_mktplace_backhaul
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdISP, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 


        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)
            i = i + 1

            break

        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider2 = providers[1]  # isp provider

        provider1.start_listening()
        provider1.initialize()
        provider2.start_listening()
        provider2.initialize()

        fileResult2 = open(provider2.getProviderId() + '.log',"a")        

        deleteDBPreviousInformation(cursor)
        executionCount = getExecutionCount(cursor)         

        serviceId = '2'        
        delay = 0.14
        price = 20
                
        bid = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid.setId('bf6632ce-1c7a-11e6-acae-080027fc03c6')
        bid.setCreationPeriod(3)
        insertDBBid(cursor, 3, executionCount, bid)
        insertDBBidPurchase(cursor, 3, serviceId, executionCount, bid, 10)
        insertDBBidPurchase(cursor, 4, serviceId, executionCount, bid, 7)
        
        bid2 = provider2.copyBid(bid)
        if (bid2.isEqual(bid) == False):
            raise FoundationException("copyBid Function Error")
                            
        competitor_bids = {}
        bid2 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid2.setId('bf679646-1c7a-11e6-acae-080027fc03c6')
        bid2.setCreationPeriod(5)
        insertDBBid(cursor, 5, executionCount, bid2)
        insertDBBidPurchase(cursor, 5, serviceId, executionCount, bid2, 6)
        insertDBBidPurchase(cursor, 6, serviceId, executionCount, bid2, 5)
        
        competitor_bids[bid2.getId()] = bid2
        bid3 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid3.setId('bf692efc-1c7a-11e6-acae-080027fc03c6')
        bid3.setCreationPeriod(7)
        insertDBBid(cursor, 7, executionCount, bid3)
        insertDBBidPurchase(cursor, 7, serviceId, executionCount, bid3, 7)
        insertDBBidPurchase(cursor, 8, serviceId, executionCount, bid3, 3)
        
        competitor_bids[bid3.getId()] = bid3
        bid4 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid4.setId('bf695e04-1c7a-11e6-acae-080027fc03c6')
        bid4.setCreationPeriod(9)
        insertDBBid(cursor, 9, executionCount, bid4)
        insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid4, 7)
        
        competitor_bids[bid4.getId()] = bid4
        bid5 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid5.setId('bf697f4c-1c7a-11e6-acae-080027fc03c6')
        bid5.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid5)
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid5, 5)
        
        competitor_bids[bid5.getId()] = bid5
        marketZoneDemand, totQuantity, numRelated = provider2.getDBMarketShareZone(bid,competitor_bids,3,1, fileResult2)
        if (totQuantity != 10):
            raise FoundationException("error in getDBMarketShareZone")

        marketZoneDemand, totQuantity, numRelated = provider2.getDBMarketShareZone(bid,competitor_bids,5,3, fileResult2)
        if (totQuantity != 23):
            raise FoundationException("error in getDBMarketShareZone")

        marketZoneDemand, totQuantity, numRelated = provider2.getDBMarketShareZone(bid,competitor_bids,7,2, fileResult2)
        if (totQuantity != 12):
            raise FoundationException("error in getDBMarketShareZone")

        # Verifies the number of ancestors.
        numAncestors = provider2.getNumAncestors()
        if (numAncestors != 4):
            raise FoundationException("error in getNumAncestors")

        
        bid6 = createBid( provider2.getProviderId(), serviceId, delay, price)        
                        
        # verifies getDBBidMarketShare
        bidDemand, totQuantity = provider2.getDBBidMarketShare(bid5.getId(),  10, 1, fileResult2)
        if (totQuantity != 5):
            raise FoundationException("error in getDBBidMarketShare")
                
        # verifies getDBBidAncestorsMarketShare
        bid5.insertParentBid(bid4)
        bid4.insertParentBid(bid3)
        bid3.insertParentBid(bid2)
        bid2.insertParentBid(bid)
        
        bidDemand2, totQuantity2 = provider2.getDBBidAncestorsMarketShare(bid5, 10, 4, fileResult2)
        if (totQuantity2 != 22):
            raise FoundationException("error in getDBBidAncestorsMarketShare")
        
        provider2._list_vars['Current_Period'] = 11        
        
        bid6.insertParentBid(bid5)

        delay = 0.14
        price = 20 
        
        # include in related bids in order to test the function getRelatedBids ( bid7 - bid 14)
        bid7 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid7.setCreationPeriod(7)        
        (provider2._list_vars['Related_Bids'])[bid7.getId()] = bid7
        bid8 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid8.setCreationPeriod(7)
        (provider2._list_vars['Related_Bids'])[bid8.getId()] = bid8
        bid9 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid9.setCreationPeriod(8)
        (provider2._list_vars['Related_Bids'])[bid9.getId()] = bid9
        bid10 = createBid( provider2.getProviderId(), serviceId, delay, price)
        bid10.setCreationPeriod(8)        
        (provider2._list_vars['Related_Bids'])[bid10.getId()] = bid10
        bid11 = createBid(provider2.getProviderId(), serviceId, delay, price)
        bid11.setCreationPeriod(9)        
        (provider2._list_vars['Related_Bids'])[bid11.getId()] = bid11

        insertDBBid(cursor, 9, executionCount, bid11)
        insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid11, 9)

        bid12 = createBid(provider2.getProviderId(), serviceId, delay, price)
        bid12.setCreationPeriod(9)
        (provider2._list_vars['Related_Bids'])[bid12.getId()] = bid12

        insertDBBid(cursor, 9, executionCount, bid12)
        insertDBBidPurchase(cursor, 9, serviceId, executionCount, bid12, 8)

        bid13 = createBid(provider2.getProviderId(), serviceId, delay, price)
        bid13.setCreationPeriod(10)        
        (provider2._list_vars['Related_Bids'])[bid13.getId()] = bid13

        insertDBBid(cursor, 10, executionCount, bid13)
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid13, 7)

        bid14 = createBid(provider2.getProviderId(), serviceId, delay, price)
        bid14.setCreationPeriod(10)
        (provider2._list_vars['Related_Bids'])[bid14.getId()] = bid14

        insertDBBid(cursor, 10, executionCount, bid14)
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid14, 7)
                        
        currentPeriod = 11
        radius = 0.1
        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 0, radius, fileResult2)          
        if len(related_bids) != 0:
            raise FoundationException("error in getRelatedBids")

        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 1, radius, fileResult2)          
        if len(related_bids) != 2:
            raise FoundationException("error in getRelatedBids")

        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 2, radius, fileResult2)          
        if len(related_bids) != 4:
            raise FoundationException("error in getRelatedBids")

        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 3, radius, fileResult2)          
        if len(related_bids) != 6:
            raise FoundationException("error in getRelatedBids")

        related_bids ={}
        related_bids = provider2.getRelatedBids(bid, currentPeriod, 4, radius, fileResult2)          
        if len(related_bids) != 8:
            raise FoundationException("error in getRelatedBids")

                        
        # verifies calculateMovedBidForecast
        marketZoneDemand1, forecast1 = provider2.calculateMovedBidForecast(currentPeriod, radius, bid5, bid6, Provider.MARKET_SHARE_ORIENTED, fileResult2)
        # The forecast is 6.333 which is 19 / 3 , that comes from demand competitor bids:bid14,bid13 and parent bid: bid5 
        marketZoneDemand2, forecast2 = provider2.calculateMovedBidForecast(currentPeriod, radius, bid5, bid6, Provider.PROFIT_ORIENTED, fileResult2)

        if (forecast1 < 6) or (forecast1 > 7):
            raise FoundationException("error in calculateMovedBidForecast MARKET_SHARE")

        if (forecast2 < 5) or (forecast2 > 6):
            raise FoundationException("error in calculateMovedBidForecast PROFIT_ORIENTED")

                        
        # ---------------------------------------------
        # verifies the method evaluateDirectionalDerivate
        # ---------------------------------------------
        
        # Test the case when the bid is not a current bids
        directions = provider2.evaluateDirectionalDerivate(currentPeriod, radius, bid, fileResult2)
        if len(directions) != 0:
            raise FoundationException("error in evaluateDirectionalDerivate")

        # In this case bid has zero purchases for the period and it is in the current bids.
        (provider2._list_vars['Bids'])[bid.getId()] = bid
        directions = provider2.evaluateDirectionalDerivate(currentPeriod, radius, bid, fileResult2)
        
        if len(directions) != 2:
            raise FoundationException("error in evaluateDirectionalDerivate")

        # In this case bid has 10  units of purchases for the period and it is in the current bids.        
        insertDBBidPurchase(cursor, 10, serviceId, executionCount, bid, 10)
        directions = provider2.evaluateDirectionalDerivate(currentPeriod, radius, bid, fileResult2)
        if len(directions) != 2:
            raise FoundationException("error in evaluateDirectionalDerivate")


    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        	# disconnect from server
        	db.close()



def test_provider_edge_monopoly_classes():
    '''
    The ProviderExecution starts the threads for the service provider agents.
    '''    

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
		  , microsecond, class_name, start_from_period, buying_marketplace_address \
          , selling_marketplace_address, capacity_controlled_at \
	     FROM simulation_provider \
	    WHERE status = 'A' AND id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdISP = '1'            
        serviceIdBackhaul = '2'
        adaptationFactor = 0
        monopolistPosition = 0
        marketPosition = 0

        i = 1
        for row in results:
            providerId = row[0]
            providerName = row[1]
            marketPosition = row[2] 
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
            buyingAddress = row[18]
            sellingAddress = row[19]            
            capacityControl = 'G' # Bulk Capacity.
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
            
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)

            i = i + 1

            capacityControl = 'G' # Bulk Capacity.
            class_name = 'ProviderEdge'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_isp
            buyingAddress = foundation.agent_properties.addr_mktplace_backhaul
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdISP, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 

        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)
            i = i + 1

            capacityControl = 'B' # Capacity by Bid.
            class_name = 'Provider'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)
            i = i + 1

            capacityControl = 'B' # Capacity by Bid.
            class_name = 'ProviderEdgeMonopoly'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_isp
            buyingAddress = foundation.agent_properties.addr_mktplace_backhaul
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdISP, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, 
                       sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)
            i = i + 1

            break

        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider2 = providers[1]  # isp provider
        provider3 = providers[2]  # backhaul provider - Bid capacity.
        provider4 = providers[3]  # isp monopoly provider 

        provider1.start_listening()
        provider1.initialize()
        provider2.start_listening()
        provider2.initialize()
        provider3.start_listening()
        provider3.initialize()
        provider4.start_listening()
        provider4.initialize()
        if (provider4.getNumberServices() != 2):
            raise FoundationException("error in the initialize method of class ProviderEdgeMonopoly")


        
        # This code verifies the Market Place Server with BulkCapacity
        # send capacity 10 units
        provider1.send_capacity()
        
        # Variable Initialization        
        serviceId = '2'
        fileResult1 = open(provider1.getProviderId() + '.log',"a")
        currentPeriod = provider2.getCurrentPeriod()
        
        # creates the bid with the minimal quality.                
        quality = 0
        price = 10
        bid = createBidBackhaul(provider1.getProviderId(), serviceId, quality, price)
        provider1.sendBid(bid, fileResult1)
        
        # Buy with minimum quality 3 units - Response 3 units purchased
        fileResult2 = open(provider2.getProviderId() + '.log',"a")        

        # Variable Initialization        
        serviceId = '2'
        fileResult3 = open(provider3.getProviderId() + '.log',"a")
        currentPeriod = provider3.getCurrentPeriod()
        
        # creates bids with the minimal quality.                
        quality = 0
        price = 10
        bid2 = createBidWithCapacity(provider3.getProviderId(), serviceId, quality, price, 10)
        bid3 = createBidWithCapacity(provider3.getProviderId(), serviceId, quality, price, 5)
        provider3.sendBid(bid2, fileResult3)
        provider3.sendBid(bid3, fileResult3)
        
        
        
        # ----------------
        #  Test Methods for the ProviderEdgeMonopoly
        # ----------------
        quality = 0.1
        price = 11
        bid4 = createBidWithCapacity(provider3.getProviderId(), serviceId, quality, price, 10)
        provider3.sendBid(bid4, fileResult3)

        quality = 0.3
        price = 13
        bid5 = createBidWithCapacity(provider3.getProviderId(), serviceId, quality, price, 10)
        provider3.sendBid(bid5, fileResult3)

        fileResult4 = open(provider4.getProviderId() + '.log',"a")
        currentPeriod = provider4.getCurrentPeriod()
        quantity = provider4.purchaseBasedOnProvidersBids(currentPeriod, serviceId, bid4, 3, fileResult4)
        if (quantity != 3):
            raise FoundationException("error in the purchase method of ProviderEdgeMonopoly")

        # test auxiliary functions for moving bids.        
        direction = 1 
        adaptationFactor = 0.1
        marketPosition = 0.4
        
        serviceBackhaul = provider4.getService(serviceIdBackhaul)
        if (serviceBackhaul == None):
            raise FoundationException("getService method is not working in class ProviderEdgeMonopoly")
            
        qualityVariableBack = serviceBackhaul.getDecisionVariable('3')
        minValueBack = qualityVariableBack.getMinValue()        
        maxValueBack = qualityVariableBack.getMaxValue()
        maxValueRange = (maxValueBack - minValueBack)*adaptationFactor
        
        output1 = provider4.moveQuality(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult4)

        if ((output1['3'])['Direction'] != 1):
            raise FoundationException("error in the purchase method of moveQuality")

        if (((output1['3'])['Step'] <= 0) or ((output1['3'])['Step'] >= maxValueRange) ):
            raise FoundationException("error in the purchase method of moveQuality")
                        
        adaptationFactor = 0.5
        marketPosition = 0.7
        maxValueRange = (maxValueBack - minValueBack)*adaptationFactor
        output1 = provider4.moveQuality(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult4)
        if (((output1['3'])['Step'] <= 0) or ((output1['3'])['Step'] >= maxValueRange) ):
            raise FoundationException("error in the purchase method of moveQuality")

        direction = -1 
        maxValueRange = maxValueRange *-1
        output2 = provider4.moveQuality(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult4)
        if ((output2['3'])['Direction'] != -1):
            raise FoundationException("error in the purchase method of moveQuality")

        if (((output2['3'])['Step'] >= 0) or ((output2['3'])['Step'] <= maxValueRange) ):
            raise FoundationException("error in the purchase method of moveQuality")


        priceVariableBack = serviceBackhaul.getDecisionVariable('4')
        minValueBack = priceVariableBack.getMinValue()        
        maxValueBack = priceVariableBack.getMaxValue()
        maxValueRange = (maxValueBack - minValueBack)*adaptationFactor

        direction = 1
        output2 = provider4.movePrice(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult4)
        if ((output2['4'])['Direction'] != 1):
            raise FoundationException("error in the purchase method of movePrice")

        if (((output2['4'])['Step'] <= 0) or ((output2['4'])['Step'] >= maxValueRange) ):
            raise FoundationException("error in the purchase method of moveQuality")

        direction = -1
        maxValueRange = maxValueRange *-1
        output2 = provider4.movePrice(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult4)
        if ((output2['4'])['Direction'] != -1):
            raise FoundationException("error in the purchase method of movePrice")

        if (((output2['4'])['Step'] >= 0) or ((output2['4'])['Step'] <= maxValueRange) ):
            raise FoundationException("error in the purchase method of moveQuality")
        
        # Test functions for relating variables in services
        serviceIsp = provider4.getService(serviceIdISP)
        for decisionVariable in serviceIsp._decision_variables:
            provider4.getRelatedDecisionVariable(serviceIsp, serviceBackhaul, decisionVariable)        

        # Test functions for relating variables in services
        for decisionVariable in serviceBackhaul._decision_variables:
            provider4.getRelatedDecisionVariable(serviceBackhaul, serviceIsp, decisionVariable)        
        
        
        # Test the function convert to own bid.        
        bid4_1 = provider4.convertToOwnBid(serviceIsp, serviceBackhaul, bid4)
        bid4_2 = provider4.convertToOwnBid(serviceIsp, serviceBackhaul, bid5)
        bid4_1.setProviderBid(bid4)
        bid4_2.setProviderBid(bid5)
        
        qualityVariable = serviceIsp.getDecisionVariable('2')
        minValue = qualityVariable.getMinValue()
        maxValue = qualityVariable.getMaxValue()
        
        if (bid4_1.getDecisionVariable('2') != minValue + (0.9*(maxValue-minValue))):
            raise FoundationException("Error in method convertToOwnBid of ProviderEdgeMonopoly")

        if (bid4_2.getDecisionVariable('2') != minValue + (0.7*(maxValue-minValue))):
            raise FoundationException("Error in method convertToOwnBid of ProviderEdgeMonopoly")
                
        staged_bids = {}
        staged_bids[bid4_1.getId()] = {'Object': bid4_1, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 3 }
        staged_bids[bid4_2.getId()] = {'Object': bid4_2, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 3 }
        provider4.purchaseBidsBasedOnProvidersBids( currentPeriod, staged_bids, fileResult4)
        provider4.sendBids(staged_bids, fileResult4)        

        # Test is neighborhoodBidToStaged
        staged_bids_test = {}
        radius = 0.1        
        delay = 0.18
        price = 15
        bidTest4_01 = createBid( provider4.getProviderId(), serviceIsp.getId(), delay, price)

        # Verifies method bids are Neighborhood Bids
        delay = 0.17
        price = 14.5
        bidTest4_02 = createBid( provider4.getProviderId(), serviceIsp.getId(), delay, price)

        delay = 0.18
        price = 18
        bidTest4_03 = createBid( provider4.getProviderId(), serviceIsp.getId(), delay, price)

        staged_bids_test[bidTest4_03.getId()] = {'Object': bidTest4_03, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
        ret = provider4.isNeighborhoodBidToStaged( bidTest4_01,  staged_bids_test, radius, fileResult4)
        if ret != False:
            raise FoundationException("Error in method isNeighborhoodBidToStaged of ProviderEdgeMonopoly")

        staged_bids_resp = {}
        provider4.includeExploringBid( bidTest4_01, bid4, serviceIsp, radius, staged_bids_resp, staged_bids_test, fileResult4)
        if len(staged_bids_resp) != 1:
            raise FoundationException("Error in method includeExploringBid of ProviderEdgeMonopoly")
                
        staged_bids_test[bidTest4_02.getId()] = {'Object': bidTest4_02, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
        ret = provider4.isNeighborhoodBidToStaged( bidTest4_01,  staged_bids_test, radius, fileResult4)
        if ret != True:
            raise FoundationException("Error in method isNeighborhoodBidToStaged of ProviderEdgeMonopoly")

        staged_bids_resp = {}
        provider4.includeExploringBid( bidTest4_01, bid4, serviceIsp, radius, staged_bids_resp, staged_bids_test, fileResult4)
        if len(staged_bids_resp) != 0:
            raise FoundationException("Error in method includeExploringBid of ProviderEdgeMonopoly")
                
        deleteDBPreviousInformation(cursor)
        executionCount = getExecutionCount(cursor)         
        currentPeriod = 13

        # we are going to test customers oriented by quality        
        
        delay = 0.18	
        price = 15	
        demand = 12
        bid4_test = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        insertDBBid(cursor, 13, executionCount, bid)


        delay = 0.19	
        price = 14.5	
        demand = 12
        bid4_5 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_5.setUnitaryProfit(0.2)
        bid4_5.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_5)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_5, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_5, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_5, demand)        
        (provider4._list_vars['Bids'])[bid4_5.getId()] = bid4_5
        
        delay = 0.19	
        price = 15
        demand = 11
        bid4_6 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_6.setUnitaryProfit(0.2)
        bid4_6.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_6)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_6, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_6, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_6, demand)        
        (provider4._list_vars['Bids'])[bid4_6.getId()] = bid4_6
        
        
        delay = 0.19	
        price = 15.5	
        demand = 10
        bid4_7 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_7.setUnitaryProfit(0.2)
        bid4_7.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_7)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_7, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_7, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_7, demand+0)        
        (provider4._list_vars['Bids'])[bid4_7.getId()] = bid4_7
        
        
        delay = 0.18	
        price = 13.5	
        demand = 15
        bid4_8 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_8.setUnitaryProfit(0.2)
        bid4_8.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_8)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_8, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_8, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_8, demand+0)        
        (provider4._list_vars['Bids'])[bid4_8.getId()] = bid4_8
        
        
        delay = 0.18	
        price = 14	
        demand = 14
        bid4_9 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_9.setUnitaryProfit(0.2)
        bid4_9.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_9)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_9, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_9, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_9, demand+0)        
        (provider4._list_vars['Bids'])[bid4_9.getId()] = bid4_9
        
        
        delay = 0.18	
        price = 14.5	
        demand = 13
        bid4_10 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_10.setUnitaryProfit(0.2)
        bid4_10.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_10)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_10, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_10, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_10, demand+0)        
        (provider4._list_vars['Bids'])[bid4_10.getId()] = bid4_10
        
        
        delay = 0.18	
        price = 15	
        demand = 12
        bid4_11 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_11.setUnitaryProfit(0.2)
        bid4_11.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_11)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_11, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_11, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_11, demand+0)        
        (provider4._list_vars['Bids'])[bid4_11.getId()] = bid4_11
        
        
        delay = 0.18	
        price = 15.5	
        demand = 11
        bid4_12 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_12.setUnitaryProfit(0.2)
        bid4_12.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_12)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_12, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_12, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_12, demand+0)        
        (provider4._list_vars['Bids'])[bid4_12.getId()] = bid4_12
        
        
        delay = 0.18	
        price = 16	
        demand = 10
        bid4_13 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_13.setUnitaryProfit(0.2)
        bid4_13.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_13)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_13, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_13, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_13, demand+0)        
        (provider4._list_vars['Bids'])[bid4_13.getId()] = bid4_13
        
        
        delay = 0.18	
        price = 16.5	
        demand = 9
        bid4_14 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_14.setUnitaryProfit(0.2)
        bid4_14.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_14)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_14, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_14, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_14, demand+0)        
        (provider4._list_vars['Bids'])[bid4_14.getId()] = bid4_14
        
        delay = 0.17	
        price = 14.5	
        demand = 14
        bid4_15 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_15.setUnitaryProfit(0.2)
        bid4_15.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_15)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_15, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_15, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_15, demand+0)        
        (provider4._list_vars['Bids'])[bid4_15.getId()] = bid4_15
        
        delay = 0.17	
        price = 15	
        demand = 13
        bid4_16 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_16.setUnitaryProfit(0.2)
        bid4_16.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_16)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_16, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_16, demand+2)
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_16, demand+0)        
        (provider4._list_vars['Bids'])[bid4_16.getId()] = bid4_16
        
        delay = 0.17	
        price = 15.5	
        demand = 12
        bid4_17 = createBid(provider4.getProviderId(), serviceIdISP, delay, price)
        bid4_17.setUnitaryProfit(0.2)
        bid4_17.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_17)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_17, demand+4)
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_17, demand+2)
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_17, demand+0)
        (provider4._list_vars['Bids'])[bid4_17.getId()] = bid4_17

        
        provBid4Test = provider.convertToOwnBid(serviceBackhaul, serviceIsp,  bid4_test)
        bid = provBid4Test
        radius = 0.1
        value = provider4.determineProfitForecast(currentPeriod, numAncestors, radius, serviceIsp, serviceBackhaul, adaptationFactor, marketPosition, bid4_test, fileResult4)

        # we test the function Exec Front Bids by calling all of their functions
        
        staged_bids.clear()
        
        direction = -1
        staged_bids_resp = {}
        directionQuality = provider4.moveQuality(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult4)
        newBidProv = provider4.moveBidOnDirection(bid, serviceBackhaul, directionQuality)
        newBidOwn1 = provider4.convertToOwnBid( serviceIsp, serviceBackhaul,  newBidProv)
        profForecast = provider4.determineProfitForecast(currentPeriod, numAncestors, radius, serviceIsp, serviceBackhaul, adaptationFactor, marketPosition, newBidOwn1, fileResult4)
        if profForecast > 0:
            provider4.includeExploringBid( newBidOwn1, bid, serviceIsp, radius, staged_bids_resp, staged_bids, fileResult4)
            
        # increase prices
        direction = 1

        directionPrice = provider4.movePrice(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult4)
        newBidProv = provider4.moveBidOnDirection(bid, serviceBackhaul, directionPrice)
        newBidOwn2 = provider4.convertToOwnBid( serviceIsp, serviceBackhaul,  newBidProv)
        profForecast = provider4.determineProfitForecast(currentPeriod, numAncestors, radius, serviceIsp, serviceBackhaul, adaptationFactor, marketPosition, newBidOwn2, fileResult4)
        if profForecast > 0:
            provider4.includeExploringBid( newBidOwn2, bid, serviceIsp, radius, staged_bids_resp, staged_bids, fileResult4)            
            

        # decrease prices
        direction = -1
        directionPrice = provider4.movePrice(serviceBackhaul, adaptationFactor, marketPosition, direction, fileResult4)
        newBidProv = provider4.moveBidOnDirection(bid, serviceBackhaul, directionPrice)

        newBidOwn3 = provider4.convertToOwnBid( serviceIsp, serviceBackhaul,  newBidProv)
        profForecast = provider4.determineProfitForecast(currentPeriod, numAncestors, radius, serviceIsp, serviceBackhaul, adaptationFactor, marketPosition, newBidOwn3, fileResult4)
        if profForecast > 0:
            provider4.includeExploringBid( newBidOwn3, bid, serviceIsp, radius, staged_bids_resp, staged_bids, fileResult4)
            
        staged_bids_resp.clear()
        
        bidList = []
        bidList.append(provBid4Test)
        provider4.execFrontBids(currentPeriod, numAncestors, radius, serviceIsp, serviceBackhaul, adaptationFactor, marketPosition, bidList, staged_bids, staged_bids_resp, fileResult4)

        if (len(staged_bids_resp) != 0):
            raise FoundationException("Error in method execFrontBids of ProviderEdgeMonopoly")
                
        staged_bids_resp.clear()
        
        # Test the method AskBackhaulBids.
        dic_return = provider4.AskBackhaulBids(serviceBackhaul.getId())
        if (len(dic_return) != 1):
            raise FoundationException("Error in method AskBackhaulBids of ProviderEdgeMonopoly")
        
        staged_bids_temp = {}
        bidList = []
        keys_sorted = sorted(dic_return,reverse=True)
        for front in keys_sorted:
            bidList = dic_return[front]
            break        
        
        if (len(bidList) != 5):
            raise FoundationException("Error in method AskBackhaulBids of ProviderEdgeMonopoly")
                    
        staged_bids_temp2 = {}
        provider4.execBidUpdate(currentPeriod, numAncestors, radius, serviceIsp, serviceBackhaul, adaptationFactor, marketPosition, staged_bids, staged_bids_temp2, fileResult4)
        if (len(staged_bids_temp2) != 11):
            raise FoundationException("Error in method execBidUpdate of ProviderEdgeMonopoly")
        
        for bidId in staged_bids_temp:
            staged_bids_temp2[bidId] = staged_bids_temp[bidId]
                
        # Delete all previous bids.
        provider4._list_vars['Bids'].clear()
                        
        incrPrice = 0.5
        priceVariable = serviceIsp.getDecisionVariable('1')
        minPrice = priceVariable.getMinValue()
        maxPrice = priceVariable.getMaxValue()
        
        numBefore = len(provider4._list_vars['Bids'])
        
        incrQuality = 0.01
        qualityVariable = serviceIsp.getDecisionVariable('2')
        minQuality = qualityVariable.getMinValue()
        maxQuality = qualityVariable.getMaxValue()
        price = minPrice
        quality = minQuality
        while (price <= maxPrice):
            quality = minQuality
            while (quality <= maxQuality):
                BidTmp = createBid(provider4.getProviderId(), serviceIsp.getId(), quality, price)
                (provider4._list_vars['Bids'])[BidTmp.getId()] = BidTmp
                quality = quality + incrQuality
            price = price + incrPrice
        
        numAfter = len(provider4._list_vars['Bids'])

        if (numAfter - numBefore) != 102:
            raise FoundationException("Error in assigning bids to provider4")
        
        radius = 0.05
        for bidId in staged_bids_resp:
            bid = (staged_bids_resp[bidId])['Object']
            relatedBids = provider4.getOwnRelatedBids(bid, radius, 10, 2, fileResult4)
            if len(relatedBids) != 0:
                raise FoundationException("Error in getOwnRelatedBids")
        
        for bidId in provider4._list_vars['Bids']:
            ((provider4._list_vars['Bids'])[bidId]).setCreationPeriod(10)

        radius = 0.2        
        for bidId in staged_bids_resp:
            bid = (staged_bids_resp[bidId])['Object']
            relatedBids = provider4.getOwnRelatedBids(bid, radius, 10, 2, fileResult4)
            if len(relatedBids) == 0:
                raise FoundationException("Error in getOwnRelatedBids")

        for bidId in provider4._list_vars['Bids']:
            ((provider4._list_vars['Bids'])[bidId]).setCreationPeriod(9)

        for bidId in staged_bids_resp:
            bid = (staged_bids_resp[bidId])['Object']
            relatedBids = provider4.getOwnRelatedBids(bid, radius, 10, 2, fileResult4)
            if len(relatedBids) == 0:
                raise FoundationException("Error in getOwnRelatedBids")

        for bidId in provider4._list_vars['Bids']:
            ((provider4._list_vars['Bids'])[bidId]).setCreationPeriod(8)

        for bidId in staged_bids_resp:
            bid = (staged_bids_resp[bidId])['Object']
            relatedBids = provider4.getOwnRelatedBids(bid, radius, 10, 2, fileResult4)
            if len(relatedBids) == 0:
                raise FoundationException("Error in getOwnRelatedBids")

        for bidId in provider4._list_vars['Bids']:
            ((provider4._list_vars['Bids'])[bidId]).setCreationPeriod(7)

        for bidId in staged_bids_resp:
            bid = (staged_bids_resp[bidId])['Object']
            relatedBids = provider4.getOwnRelatedBids(bid, radius, 10, 2, fileResult4)
            if len(relatedBids) != 0:
                raise FoundationException("Error in getOwnRelatedBids")

        # This code creates the bids in the database
        for bidId in provider4._list_vars['Bids']:
            ((provider4._list_vars['Bids'])[bidId]).setCreationPeriod(7)
            ((provider4._list_vars['Bids'])[bidId]).setUnitaryProfit(0.6)
            bid = ((provider4._list_vars['Bids'])[bidId])            
            insertDBBid(cursor, 7, executionCount, bid)
            insertDBBidPurchase(cursor, 7, serviceIdISP, executionCount, bid, 3)

        # This code creates purchases in the database for another period.
        for bidId in provider4._list_vars['Bids']:
            bid = ((provider4._list_vars['Bids'])[bidId])            
            insertDBBidPurchase(cursor, 8, serviceIdISP, executionCount, bid, 2)
        
        # This code creates purchases in the database for another period.
        for bidId in provider4._list_vars['Bids']:
            bid = ((provider4._list_vars['Bids'])[bidId])            
            insertDBBidPurchase(cursor, 9, serviceIdISP, executionCount, bid, 1)

        bid4_3 = createBid(provider4.getProviderId(), serviceIdISP, 0.15, 17) 
        # This bring all bids that were created in the last three periods
        radius = 0.1
        currentPeriod = 10
        bids_related = provider4.getOwnRelatedBids(bid4_3, radius, currentPeriod, 3, fileResult4)
        
        if len(bids_related) != 13:
            raise FoundationException("Error in calculating method getOwnRelatedBids of ProviderEdgeMonopoly")
            
        marketZoneDemand, totQuantity, numRelated = provider4.getDBMarketShareZone(bid4_3, bids_related, currentPeriod -1 , 1, fileResult4)
        if totQuantity != 13:
            raise FoundationException("Error (1) in calculating method getDBMarketShareZone of ProviderEdgeMonopoly")
        
        marketZoneDemand, totQuantity, numRelated = provider4.getDBMarketShareZone(bid4_3, bids_related, currentPeriod -1 , 2, fileResult4)
        if totQuantity != 39:
            raise FoundationException("Error (2) in calculating method getDBMarketShareZone of ProviderEdgeMonopoly")

        marketZoneDemand, totQuantity, numRelated = provider4.getDBMarketShareZone(bid4_3, bids_related, currentPeriod -1 , 3, fileResult4)
        if totQuantity != 78:
            raise FoundationException("Error (3) in calculating method getDBMarketShareZone of ProviderEdgeMonopoly")

        profitZone, totProfit, numRelated = provider4.getDBProfitZone(bid4_3, bids_related, 9, fileResult4)
        if round(totProfit,1) != 7.8:
            raise FoundationException("Error (1) in calculating method getDBProfitZone of ProviderEdgeMonopoly")
        
        profitZone, totProfit, numRelated = provider4.getDBProfitZone(bid4_3, bids_related, 8, fileResult4)
        if round(totProfit,1) != 15.6:
            raise FoundationException("Error (2) in calculating method getDBProfitZone of ProviderEdgeMonopoly")

        profitZone, totProfit, numRelated = provider4.getDBProfitZone(bid4_3, bids_related, 7, fileResult4)
        if round(totProfit,1) != 23.4:
            raise FoundationException("Error (3) in calculating method getDBProfitZone of ProviderEdgeMonopoly")
        
        
        bid4_4 = createBid(provider4.getProviderId(), serviceIdISP, 0.14, 15)

        bids_related = provider4.getOwnRelatedBids(bid4_4, radius, currentPeriod, 3, fileResult4)
        
        if len(bids_related) != 10:
            raise FoundationException("Error in calculating method getOwnRelatedBids of ProviderEdgeMonopoly")
            
        marketZoneDemand, totQuantity, numRelated = provider4.getDBMarketShareZone(bid4_4, bids_related, currentPeriod -1, 1, fileResult4)
        if totQuantity != 10:
            raise FoundationException("Error (1) in calculating method getDBMarketShareZone of ProviderEdgeMonopoly")
        
        marketZoneDemand, totQuantity, numRelated = provider4.getDBMarketShareZone(bid4_4, bids_related, currentPeriod -1, 2, fileResult4)
        if totQuantity != 30:
            raise FoundationException("Error (2) in calculating method getDBMarketShareZone of ProviderEdgeMonopoly")

        marketZoneDemand, totQuantity, numRelated = provider4.getDBMarketShareZone(bid4_4, bids_related, currentPeriod -1, 3, fileResult4)
        if totQuantity != 60:
            raise FoundationException("Error (3) in calculating method getDBMarketShareZone of ProviderEdgeMonopoly")


        profitZone, totProfit, numRelated = provider4.getDBProfitZone(bid4_4, bids_related, 9, fileResult4)
        if round(totProfit,0) != 6:
            raise FoundationException("Error (1) in calculating method getDBProfitZone of ProviderEdgeMonopoly")
        
        profitZone, totProfit, numRelated = provider4.getDBProfitZone(bid4_4, bids_related, 8, fileResult4)
        if round(totProfit,0) != 12:
            raise FoundationException("Error (2) in calculating method getDBProfitZone of ProviderEdgeMonopoly")

        profitZone, totProfit, numRelated = provider4.getDBProfitZone(bid4_4, bids_related, 7, fileResult4)
        if round(totProfit,0) != 18:
            raise FoundationException("Error (3) in calculating method getDBProfitZone of ProviderEdgeMonopoly")
        
        
        #-------------------------------------------------------
        # Test Calculate Forecast
        #-------------------------------------------------------        
        staged_bids.clear()
        staged_bids[bid4_3.getId()] = {'Object': bid4_3, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
        staged_bids[bid4_4.getId()] = {'Object': bid4_4, 'Action': Bid.ACTIVE, 'MarketShare': {}, 'Forecast': 0 }
                                    
        provider4.calculateForecast(radius, currentPeriod, 3, 5, staged_bids, fileResult4)
        
        if ((staged_bids[bid4_3.getId()])['Forecast'] <= 5.571) or ((staged_bids[bid4_3.getId()])['Forecast'] >= 5.572):
            raise FoundationException("Error (1) in calculating method calculateForecast of ProviderEdgeMonopoly")
        
        if ((staged_bids[bid4_4.getId()])['Forecast'] <= 5.454) or ((staged_bids[bid4_4.getId()])['Forecast'] >= 5.455):
            raise FoundationException("Error (2) in calculating method calculateForecast of ProviderEdgeMonopoly")

        
        
	
    except FoundationException as e:
        print e.__str__()
        fileResult1.close()
        fileResult2.close()
        fileResult3.close()
        fileResult4.close()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        	# disconnect from server
        	db.close()


def test_provider_edge_monopoly_current_bids():
    '''
    The ProviderExecution starts the threads for the service provider agents.
    '''    

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
		  , microsecond, class_name, start_from_period, buying_marketplace_address \
          , selling_marketplace_address, capacity_controlled_at \
	     FROM simulation_provider \
	    WHERE status = 'A' AND id = 1"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        serviceIdISP = '1'            
        serviceIdBackhaul = '2'
        adaptationFactor = 0
        monopolistPosition = 0
        marketPosition = 0

        i = 1
        for row in results:
            providerId = row[0]
            providerName = row[1]
            marketPosition = row[2] 
            adaptationFactor = 0.99 # Large values for testing.
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
            buyingAddress = row[18]
            sellingAddress = row[19]            
            capacityControl = 'G' # Bulk Capacity.
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
            
            capacityControl = 'G' # Bulk Capacity.
            class_name = 'Provider'
            sellingAddress = foundation.agent_properties.addr_mktplace_backhaul
            buyingAddress = ' '
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdBackhaul, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)

            i = i + 1

            capacityControl = 'B' # Capacity by Bid.
            class_name = 'ProviderEdgeMonopoly'
            providerId = i
            providerName = 'Provider' + str(providerId)
            sellingAddress = foundation.agent_properties.addr_mktplace_isp
            buyingAddress = foundation.agent_properties.addr_mktplace_backhaul
            provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceIdISP, 
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, 
                       sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)
            i = i + 1

            break

        # start the providers
        provider1 = providers[0]  # backhaul provider - Bulk capacity.
        provider2 = providers[1]  # isp monopoly provider 

        provider1.start_listening()
        provider1.initialize()
        provider2.start_listening()
        provider2.initialize()

        fileResult1 = open(provider1.getProviderId() + '.log',"a")
        fileResult2 = open(provider2.getProviderId() + '.log',"a")        
        
        # test the function sortByLastMarketShare
        deleteDBPreviousInformation(cursor)
        executionCount = getExecutionCount(cursor)         
        currentPeriod = 12

        delay = 0.2
        price = 13	
        demand = 11
        bid4_12 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_12.setUnitaryProfit(0.2)
        bid4_12.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_12)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_12, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_12, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_12, demand+0)        
        (provider2._list_vars['Bids'])[bid4_12.getId()] = bid4_12
        
        
        delay = 0.18
        price = 14.0	
        demand = 10
        bid4_13 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_13.setUnitaryProfit(0.2)
        bid4_13.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_13)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_13, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_13, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_13, demand+0)        
        (provider2._list_vars['Bids'])[bid4_13.getId()] = bid4_13
        
        
        delay = 0.15
        price = 15.5	
        demand = 9
        bid4_14 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_14.setUnitaryProfit(0.2)
        bid4_14.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_14)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_14, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_14, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_14, demand+0)        
        (provider2._list_vars['Bids'])[bid4_14.getId()] = bid4_14
        
        delay = 0.14
        price = 17	
        demand = 14
        bid4_15 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_15.setUnitaryProfit(0.2)
        bid4_15.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_15)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_15, demand+4)        
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_15, demand+2)        
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_15, demand+0)        
        (provider2._list_vars['Bids'])[bid4_15.getId()] = bid4_15
        
        dict_result = provider2.sortByLastMarketShare(currentPeriod, fileResult2)
        list_keys = dict_result.keys()
        if (list_keys[0] != bid4_15.getId()):
            raise FoundationException("Error (1) in calculating method sortByLastMarketShare of Provider")

        if (list_keys[1] != bid4_12.getId()):
            raise FoundationException("Error (2) in calculating method sortByLastMarketShare of Provider")

        if (list_keys[2] != bid4_13.getId()):
            raise FoundationException("Error (3) in calculating method sortByLastMarketShare of Provider")

        if (list_keys[3] != bid4_14.getId()):
            raise FoundationException("Error (4) in calculating method sortByLastMarketShare of Provider")
        
        radius = 0.1
        staged_bids = {}    
        serviceIsp = provider2.getService(serviceIdISP)        
        provider2.maintainBids(currentPeriod, radius, serviceIsp, staged_bids, fileResult2)
                
        if len(staged_bids) != 8:
            raise FoundationException("Error in calculating method maintainBids of Provider")
        
        staged_bids.clear()
        provider2.moveBetterProfits(currentPeriod, radius, staged_bids, fileResult2)

        delay = 0.14
        price = 17	
        demand = 14
        bid4_16 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_16.setUnitaryProfit(0.2)
        bid4_16.setCreationPeriod(10)
        insertDBBid(cursor, 10, executionCount, bid4_16)
        insertDBBidPurchase(cursor, 10, serviceIdISP, executionCount, bid4_16, 0)        

        bid4_17 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_17.setUnitaryProfit(0.2)
        bid4_17.setCreationPeriod(11)
        bid4_17.insertParentBid(bid4_16)
        insertDBBid(cursor, 11, executionCount, bid4_17)
        insertDBBidPurchase(cursor, 11, serviceIdISP, executionCount, bid4_17, 30)        

        bid4_18 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_18.setUnitaryProfit(0.2)
        bid4_18.setCreationPeriod(12)
        bid4_18.insertParentBid(bid4_17)
        insertDBBid(cursor, 12, executionCount, bid4_18)
        insertDBBidPurchase(cursor, 12, serviceIdISP, executionCount, bid4_18, 20)        
        

        bid4_19 = createBid(provider2.getProviderId(), serviceIdISP, delay, price)
        bid4_19.setUnitaryProfit(0.2)
        bid4_19.setCreationPeriod(13)
        bid4_19.insertParentBid(bid4_18)
        insertDBBid(cursor, 13, executionCount, bid4_19)
        insertDBBidPurchase(cursor, 13, serviceIdISP, executionCount, bid4_19, 10)        
        

        currentPeriod = 14
        val_return, result_progression = provider2.continueDirectionImprovingProfits( currentPeriod, bid4_19, fileResult2)
        if val_return != False:
            raise FoundationException("Error in calculating method continueDirectionImprovingProfits of Provider")
            
        if len(result_progression) != 4:
            raise FoundationException("Error in calculating method continueDirectionImprovingProfits of Provider")

        #----------------------------------------        
        # test the method improveBidForProfits 
        #----------------------------------------

        serviceBackHaul = provider2.getService(serviceIdBackhaul)        
        variablePrice = serviceBackHaul.getDecisionVariable('4') #Price
        minValuePrice = variablePrice.getMinValue()        
        maxValuePrice = variablePrice.getMaxValue()
        maxValuePriceRange = (maxValuePrice - minValuePrice) * provider2.getAdaptationFactor()

        variableQual = serviceBackHaul.getDecisionVariable('3')
        minValueQual = variableQual.getMinValue()        
        maxValueQual = variableQual.getMaxValue()
        maxValueQualRange = (maxValueQual - minValueQual) * provider2.getAdaptationFactor()
                
        reverse = 1
        output2 = provider2.improveBidForProfits(serviceBackHaul, fileResult2, reverse)
        if ((output2['4'])['Direction'] != 1):
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['4'])['Step'] <= 0) or ((output2['4'])['Step'] >= maxValuePriceRange) ):
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['3'])['Direction'] != -1):  # Quality
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['3'])['Step'] >= 0) or ((output2['3'])['Step'] <= maxValueQualRange *-1) ):
            raise FoundationException("error in the method of improveBidForProfits")

        reverse = -1
        output2 = provider2.improveBidForProfits(serviceBackHaul, fileResult2, reverse)
        if ((output2['4'])['Direction'] != -1):
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['4'])['Step'] >= 0) or ((output2['4'])['Step'] <= maxValuePriceRange*-1) ):
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['3'])['Direction'] != 1):  # Quality
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['3'])['Step'] <= 0) or ((output2['3'])['Step'] >= maxValueQualRange) ):
            raise FoundationException("error in the method of improveBidForProfits")


        serviceIsp = provider2.getService(serviceIdISP)        
        variablePrice = serviceIsp.getDecisionVariable('1') #Price
        minValuePrice = variablePrice.getMinValue()        
        maxValuePrice = variablePrice.getMaxValue()
        maxValuePriceRange = (maxValuePrice - minValuePrice) * provider2.getAdaptationFactor()

        variableQual = serviceIsp.getDecisionVariable('2') # Quality
        minValueQual = variableQual.getMinValue()        
        maxValueQual = variableQual.getMaxValue()
        maxValueQualRange = (maxValueQual - minValueQual) * provider2.getAdaptationFactor()

        reverse = 1
        output2 = provider2.improveBidForProfits(serviceIsp, fileResult2, reverse)
        if ((output2['1'])['Direction'] != 1):  # Price
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['1'])['Step'] <= 0) or ((output2['1'])['Step'] >= maxValuePriceRange) ):
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['2'])['Direction'] != 1):
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['2'])['Step'] <= 0) or ((output2['2'])['Step'] >= maxValueQualRange) ):
            raise FoundationException("error in the method of improveBidForProfits")
            
        reverse = -1
        output2 = provider2.improveBidForProfits(serviceIsp, fileResult2, reverse)
        if ((output2['1'])['Direction'] != -1):  # Price
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['1'])['Step'] >= 0) or ((output2['1'])['Step'] <= maxValuePriceRange*-1) ):
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['2'])['Direction'] != -1):
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['2'])['Step'] >= 0) or ((output2['2'])['Step'] <= maxValueQualRange*-1) ):
            raise FoundationException("error in the method of improveBidForProfits")

        # -----------------------------
        # Test the function generate direction between two bids.
        # -----------------------------
        price1 = 17.5
        delay1 = 0.2
        
        price2 = 15
        delay2 = 0.16
        bid4_20 = createBid(provider2.getProviderId(), serviceIdISP, delay1, price1)
        bid4_21 = createBid(provider2.getProviderId(), serviceIdISP, delay2, price2)
        
        output1 = provider2.generateDirectionBetweenTwoBids( bid4_20, bid4_21, fileResult2)
        output2 = provider2.generateDirectionBetweenTwoBids( bid4_21, bid4_20, fileResult2)

        if ((output1['1'])['Direction'] != -1):  # Price
            raise FoundationException("error in the method of generateDirectionBetweenTwoBids")

        if (((output1['1'])['Step'] >= 0)  ): # it is expected a negative step
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output1['2'])['Direction'] != -1): # quality - improve
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output1['2'])['Step'] >= 0)  ): # it is expected a negative step
            raise FoundationException("error in the method of improveBidForProfits")
        

        if ((output2['1'])['Direction'] != 1):  # Price - greater price
            raise FoundationException("error in the method of generateDirectionBetweenTwoBids")

        if (((output2['1'])['Step'] <= 0)  ): # it is expected a positive step
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['2'])['Direction'] != 1): # quality - decrease quality
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['2'])['Step'] <= 0)  ): # it is expected a positive step
            raise FoundationException("error in the method of improveBidForProfits")
        
        
        price3 = 15 
        quality3 = 0.4
        
        price4 = 11
        quality4 = 0.8
        bid1_20 = createBidBackhaul(provider1.getProviderId(), serviceIdBackhaul, quality3, price3)
        bid1_21 = createBidBackhaul(provider1.getProviderId(), serviceIdBackhaul, quality4, price4)
        
        output1 = provider1.generateDirectionBetweenTwoBids( bid1_20, bid1_21, fileResult1)
        output2 = provider1.generateDirectionBetweenTwoBids( bid1_21, bid1_20, fileResult1)
        

        if ((output1['4'])['Direction'] != -1):  # Price
            raise FoundationException("error in the method of generateDirectionBetweenTwoBids")

        if (((output1['4'])['Step'] >= 0)  ): # it is expected a negative step
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output1['3'])['Direction'] != 1): # quality - improve
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output1['3'])['Step'] <= 0)  ): # it is expected a positive step
            raise FoundationException("error in the method of improveBidForProfits")
        

        if ((output2['4'])['Direction'] != 1):  # Price - greater price
            raise FoundationException("error in the method of generateDirectionBetweenTwoBids")

        if (((output2['4'])['Step'] <= 0)  ): # it is expected a postive step
            raise FoundationException("error in the method of improveBidForProfits")

        if ((output2['3'])['Direction'] != -1): # quality - decrease quality
            raise FoundationException("error in the method of improveBidForProfits")

        if (((output2['3'])['Step'] >= 0)  ): # it is expected a negative step
            raise FoundationException("error in the method of improveBidForProfits")        

        
        #---------------------------------------
        # Test Move Bid method
        #---------------------------------------
        price1 = 17.5
        delay1 = 0.2
        
        price2 = 15
        delay2 = 0.16
        
        price3 = 17
        delay3 = 0.15       
        bid4_20 = createBid(provider2.getProviderId(), serviceIdISP, delay1, price1)
        bid4_21 = createBid(provider2.getProviderId(), serviceIdISP, delay2, price2)
        bid4_22 = createBid(provider2.getProviderId(), serviceIdISP, delay3, price3)

        output1 = provider2.generateDirectionBetweenTwoBids( bid4_20, bid4_21, fileResult2)
        output2 = provider2.generateDirectionBetweenTwoBids( bid4_20, bid4_22, fileResult2)
        output3 = { }
        output3['1'] = {'Direction': 0, 'Step': 0 } 
        output3['2'] = {'Direction': 0, 'Step': 0 } 
        
        
        moveDirections= []
        moveDirections.append(output1)
        moveDirections.append(output2)
        moveDirections.append(output3)
        
        staged_bids = {}        
        marketShare = 0        
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.PROFIT_ORIENTED, fileResult2)
        
        # It should inactivivate the bid for and move it for the two first cases.
        if len(staged_bids) != 3:
            raise FoundationException("error in the method moveBid") 
                
        staged_bids = {}        
        marketShare = 0        
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.MARKET_SHARE_ORIENTED, fileResult2)

        if len(staged_bids) != 3:
            raise FoundationException("error in the method moveBid") 

        staged_bids = {}        
        marketShare = 3  
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.PROFIT_ORIENTED, fileResult2)

        if len(staged_bids) != 3:
            raise FoundationException("error in the method moveBid") 

        staged_bids = {}        
        marketShare = 3  
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.MARKET_SHARE_ORIENTED, fileResult2)

        if len(staged_bids) != 3:
            raise FoundationException("error in the method moveBid") 
        
        provider2._list_vars['Type'] = Agent.PROVIDER_BACKHAUL
        
        staged_bids = {}        
        marketShare = 3  
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.PROFIT_ORIENTED, fileResult2)

        if len(staged_bids) != 4:
            raise FoundationException("error in the method moveBid") 

        staged_bids = {}        
        marketShare = 3  
        provider2.moveBid(currentPeriod, radius, bid4_20, moveDirections, marketShare, staged_bids, Provider.MARKET_SHARE_ORIENTED, fileResult2)

        if len(staged_bids) != 4:
            raise FoundationException("error in the method moveBid") 

        provider2._list_vars['Type'] = Agent.PROVIDER_ISP
        
        
    except FoundationException as e:
        print e.__str__()
        fileResult1.close()
        fileResult2.close()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        	# disconnect from server
        	db.close()



def test_integrated_classes():
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
		  , microsecond, class_name, start_from_period, buying_marketplace_address \
          , selling_marketplace_address, capacity_controlled_at \
	     FROM simulation_provider \
	    WHERE status = 'A'"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()

        adaptationFactor = 0
        monopolistPosition = 0
        marketPosition = 0

        i = 1
        for row in results:
            providerId = row[0]
            providerName = row[1]
            marketPosition = row[2] 
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
            buyingAddress = row[18]
            sellingAddress = row[19]            
            capacityControl = row[20]
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
        			      providerSeed, marketPosition, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl)
            providers.append(provider)
            i = i + 1

        w = providers[1]
        w.start()

        provider1 = providers[0]        
        provider1.start_listening()
        provider1.initialize()
        time.sleep(1)        
        provider._list_vars['State'] == AgentServerHandler.BID_PERMITED
        provider1.exec_algorithm()
	
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        	# disconnect from server
        	db.close()


if __name__ == '__main__':
    #test_integrated_classes()
    #test_marketplace_capacity_management()
    #test_provider_general_methods()
    test_provider_database_classes()
    #test_provider_edge_monopoly_classes()
    #test_provider_edge_monopoly_current_bids()
    
