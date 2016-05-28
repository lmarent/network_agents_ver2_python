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
    bid.setDecisionVariable("1", price)  #Price
    bid.setDecisionVariable("2", delay)     # Delay
    bid.setStatus(Bid.ACTIVE)
    return bid

def createBidService2(strProv, serviceId, quality, price):
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
    black_list = ['ProviderExecution', 'ProviderAgentException','ProviderExecutionTest', 'ProviderEdgeTest']
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
        numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress):
    print 'In create provider - Class requested:' + str(typ)
    print list_classes
    if typ in list_classes:
        	targetClass = list_classes[typ]
        	return targetClass(providerName, providerId, serviceId, providerSeed, 
        			   marketPositon, adaptationFactor, monopolistPosition, 
        			   debug, resources, numberOffers, numAccumPeriods, 
        			   numAncestors, startFromPeriod, sellingAddress, buyingAddress)
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

def sendBid(bid, action, provider):
    bid.setStatus(action)
    message = bid.to_message()
    messageResult = provider._channelMarketPlace.sendMessage(message)
    if messageResult.isMessageStatusOk():
        pass
    
            

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
		  , microsecond, class_name, start_from_period, buying_marketplace_address \
          , selling_marketplace_address \
	     FROM simulation_provider \
	    WHERE status = 'A' AND id in (1,2)"

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
            buyingAddress = row[18]
            sellingAddress = row[19]
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
        			      numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress)
            providers.append(provider)
            i = i + 1
            
        # start the providers
        provider1 = providers[0]
        provider2 =providers[1]
                
        provider1.start_listening()
        provider1.initialize()
        provider2.start_listening()
        provider2.initialize()

        
        provider1.restartAvailableCapacity()
        resources = provider1._used_variables['resources']
        for resourceId in resources:
            print (resources[resourceId])['Capacity']
            print (resources[resourceId])['Cost']
            provider1.updateAvailability(resourceId, 100)
        
        availability = {}
        for resourceId in resources:
            availability[resourceId] = provider1.getAvailableCapacity(resourceId)
        
        provider1.sendCapacityEdgeProvider(availability)
        
        provider1.restartAvailableCapacity()
        resources = provider1._used_variables['resources']
        for resourceId in resources:
            print (resources[resourceId])['Capacity']
            print (resources[resourceId])['Cost']
            provider1.updateAvailability(resourceId, 200)
        
        availability = {}
        for resourceId in resources:
            availability[resourceId] = provider1.getAvailableCapacity(resourceId)
                
        provider1.sendCapacityEdgeProvider(availability)

        provider1.restartAvailableCapacity()
        availability = {}
        for resourceId in resources:
            availability[resourceId] = provider1.getAvailableCapacity(resourceId)
        provider1.sendCapacityEdgeProvider(availability)

        
        provider2.send_capacity()

        serviceId = provider2.getServiceId()
        strProvider2 = provider2.getProviderId()
        quality = 0.5
        price = 14        
        BidService2_1 = createBidService2(provider2.getProviderId(), serviceId, quality, price)
        sendBid(BidService2_1, Bid.ACTIVE, provider2)


        serviceId = provider2.getServiceId()
        strProvider2 = provider2.getProviderId()
        quality = 0.7
        price = 15        
        BidService2_2 = createBidService2(provider2.getProviderId(), serviceId, quality, price)
        sendBid(BidService2_2, Bid.ACTIVE, provider2)

        serviceId = provider2.getServiceId()
        strProvider2 = provider2.getProviderId()
        quality = 0.8
        price = 16        
        BidService2_3 = createBidService2(provider2.getProviderId(), serviceId, quality, price)
        sendBid(BidService2_3, Bid.ACTIVE, provider2)

        serviceId = provider2.getServiceId()
        strProvider2 = provider2.getProviderId()
        quality = 0.9
        price = 17        
        BidService2_4 = createBidService2(provider2.getProviderId(), serviceId, quality, price)
        sendBid(BidService2_4, Bid.ACTIVE, provider2)

        bidService2Id = BidService2_1.getId()
        quantity = provider1.purchase( serviceId, BidService2_1, 20)
        if (quantity != 20):
            raise FoundationException("could not buy everything")            

        # 50 units remanining
        dic_return = provider1.AskBackhaulBids(serviceId)
        if (len(dic_return) != 1):
            raise FoundationException("Invalid number of bids in the server") 
        
        resources = provider1._used_variables['resources']
        resourceIds = resources.keys()
        resourceId = resourceIds[0]
            
        purchased = 0
        quantityReq = 20   
        quality =  0.8
        keys_sorted = sorted(dic_return,reverse=True)
        for front in keys_sorted:
            bidList = dic_return[front]
            evaluatedBids = {}
            for bid in bidList:
                disutility, totPercentage = provider1.getDisutility(resourceId, serviceId, bid)
                if disutility in evaluatedBids:
                    evaluatedBids[disutility].append({'object' : bid, 'overPercentage' : totPercentage })
                else:
                    evaluatedBids[disutility] = [{'Object' : bid, 'OverPercentage' : totPercentage }]
            
            # Purchase based on the disutility order.
            disutilities_sorted = sorted(evaluatedBids)        
            unitaryCost = float((resources[resourceId])['Cost'])
            purchased = provider1.purchaseResource(front, serviceId, unitaryCost, quantityReq, quality, evaluatedBids, disutilities_sorted)
            break
        
        if (purchased != 21.25):
            raise FoundationException("Invalid purchase")

        # The quantities remaining are 28.75
        quantityReq = 10
        quality = 1.0
        purchased = provider1.execServicePurchase(resourceId, serviceId, quantityReq, quality)
        if (purchased < 10):
            raise FoundationException("Invalid purchase")
        
        quantityReq = 50
        quality = 1.0
        purchased = provider1.execResourcePurchase( resourceId, quantityReq, quality, 40)
        if (purchased < 10):
            raise FoundationException("Invalid purchase")

        delay = 0.14 
        price = 20 
        bidProvider1_1 = createBid( provider1.getProviderId(), provider1.getServiceId(), delay, price)
                
        availability = {}
        resources = provider1.calculateBidResources(bidProvider1_1)
        purchased = provider1.purchaseResourceForBid(bidProvider1_1, 10, resources, availability)
        if (purchased < 10):
            raise FoundationException("Invalid purchase")

        delay = 0.16
        price = 18 
        bidProvider1_2 = createBid( provider1.getProviderId(), provider1.getServiceId(), delay, price)
        purchased = provider1.purchaseResourceForBid(bidProvider1_1, 10, resources, availability)
        if (purchased < 10):
            raise FoundationException("Invalid purchase")
        
        staged_bids = {}        

        delay = 0.14 
        price = 20 
        bidProvider1_3 = createBid( provider1.getProviderId(), provider1.getServiceId(), delay, price)

        delay = 0.16
        price = 18 
        bidProvider1_4 = createBid( provider1.getProviderId(), provider1.getServiceId(), delay, price)

        staged_bids[bidProvider1_3.getId()] = {'Object': bidProvider1_3, 'Action': Bid.ACTIVE, 'MarketShare' : {}, 'Forecast': 10 }        
        staged_bids[bidProvider1_4.getId()] = {'Object': bidProvider1_4, 'Action': Bid.ACTIVE, 'MarketShare' : {}, 'Forecast': 10 }        
        provider1.purchaseBids(staged_bids, availability)        
        
        print availability        
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
