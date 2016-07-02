import multiprocessing
from Consumer import Consumer
from ProviderAgentException import ProviderException
import logging
import MySQLdb
import datetime
import random

logger = logging.getLogger('consumer_application')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('consumers_logs.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

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

if __name__ == '__main__':
    '''
    The ConsumerExecution starts the threads for the consumer agents.
    '''
	
    # Open database connection
    db = MySQLdb.connect("localhost","root","password","Network_Simulation" )

    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # Brings the general parameters from the database
    bidPeriods, numberOffers, numAccumPeriods = getGeneralConfigurationParameters(cursor)

    # Prepare SQL query to SELECT customers from the database.
    sql = "select a.number_execute, b.service_id, a.seed, a.year, a.month, a.day, \
		  a.hour, a.minute, a.second, a.microsecond \
          from simulation_consumer a, simulation_consumerservice b \
	      where a.id = b.consumer_id \
	      and b.execute = 1 \
	      LIMIT 1"

    # every iteraction of the consumer execution requires 6 random numbers. 
    if (bidPeriods > 0):
	numRandom = bidPeriods * 7
    else:
	numRandom = 100 * 7
    
    try:
	# Execute the SQL command
	cursor.execute(sql)
	# Fetch all the rows in a list of lists.
	results = cursor.fetchall()
	num_consumers = 0
	for row in results:
	    num_consumers = row[0]
	    serviceId = str(row[1])
	    seed = row[2]
	    year = row[3]
	    month = row[4]
	    day = row[5]
	    hour = row[6]
	    minute = row[7]
	    second = row[8]
	    microsecond = row[9]
	    seed = getSeed(seed, year, month, day, hour, minute, second, microsecond)
	    random.seed(seed)
	    # Start consumers
	    logger.info('Creating %d consumers' % num_consumers)
	    logger.info('seed:' + str(seed))
	    # Creating aleatory numbers for the customers.
	    consumers = []
	    for i in xrange(num_consumers):
		customer_seed = random.randint(0, 1000 * num_consumers)
		logger.info('customer seed:'+ str(customer_seed))
		consumer = Consumer("agent" + str(i), i, serviceId, customer_seed)
		consumers.append(consumer)

	if (num_consumers > 0):
	    for w in consumers:
		    w.start()
    except ProviderException as e:
        print e.__str__()
    except Exception as e:
	print e.__str__()
    finally:
	# disconnect from server
	db.close()
	
    
