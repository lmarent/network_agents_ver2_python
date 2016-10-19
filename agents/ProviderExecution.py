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



logger = logging.getLogger('provider_application')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('providers_logs.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)



def load_classes(list_classes):
    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    sys.path.append(currentdir)
    agents_directory = currentdir
    black_list = ['ProviderExecution', 'ProviderAgentException','ProviderExecutionTest','ProviderEdgeTest','ProviderPublicTest']
    for filename in os.listdir (agents_directory):
        	# Ignore subfolders
        	if os.path.isdir (os.path.join(agents_directory, filename)):
        	    continue
        	else:
        	    if re.match(r"Provider.*?\.py$", filename):
            		classname = re.sub(r".py", r"", filename)
            		#if (classname not in black_list):
                        if (classname in foundation.agent_properties.provider_types):
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
        numAccumPeriods, numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl, purchase_service):
    print 'In create provider - Class requested:' + str(typ)
    print list_classes
    if typ in list_classes:
        	targetClass = list_classes[typ]
        	return targetClass(providerName, providerId, serviceId, providerSeed, 
        			   marketPositon, adaptationFactor, monopolistPosition, 
        			   debug, resources, numberOffers, numAccumPeriods, 
        			   numAncestors, startFromPeriod, sellingAddress, buyingAddress, capacityControl, purchase_service)
    else:
        err = 'Class' + typ + 'not found to be loaded'
        raise ProviderException(err)
	

'''
The ProviderExecution starts the threads for the service provider agents.
'''    
if __name__ == '__main__':
    list_classes = {}
    # Load Provider classes
    load_classes(list_classes)
    
    # Open database connection
    #db = MySQLdb.connect("localhost","root","password","Network_Simulation" )
    db = MySQLdb.connect(foundation.agent_properties.addr_database,foundation.agent_properties.user_database,
    foundation.agent_properties.user_password,foundation.agent_properties.database_name )

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
	    WHERE status = 'A'"

    try:
        providers = []
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()
        i = 1
        lst = []
        lst = foundation.agent_properties.provider_types.split(',')


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
            capacityControl = row[20]
            purchase_service = row[21]
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
            
            if (class_name in lst):
                provider = create(list_classes, class_name, providerName + str(providerId), providerId, serviceId, 
        			      providerSeed, marketPositon, adaptationFactor, 
        			      monopolistPosition, debug, resources, numberOffers, 
        			      numAccumPeriods, numAncestors, startFromPeriod, 
                       sellingAddress, buyingAddress, capacityControl, purchase_service)
                providers.append(provider)
                i = i + 1

	    # start the providers
        for w in providers:
            w.start()
        
	
    except FoundationException as e:
        print e.__str__()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
        print e.__str__()
    finally:
        	# disconnect from server
        	db.close()
