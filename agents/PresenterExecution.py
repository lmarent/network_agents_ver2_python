import multiprocessing
from Presenter import Presenter
from UnitaryTest import Presenter_Test
from ProviderAgentException import ProviderException
import MySQLdb
import logging

logger = logging.getLogger('presenter_application')
logger.setLevel(logging.INFO)
fh = logging.FileHandler('presenter_logs.log')
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


def load_offered_data(cursor, offer_variable):
    if offer_variable != None:
	sql_variable = "select name, type, function, decision_variable_id \
			  from simulation_offeringdata \
			 where id = '%d' " % (offer_variable)
	cursor.execute(sql_variable)
	# Fetch all the rows in a list of lists.
	variables_res = cursor.fetchall()
	variable_def = {}
	for row in variables_res:
	    variable_def['id'] = offer_variable
	    variable_def['name'] = row[0]
	    variable_def['type'] = row[1]
	    variable_def['function'] = row[2]
	    variable_def['decision_variable'] = str(row[3])
    else:
	variable_def = {}
    return variable_def	

def load_graphics(cursor2, cursor3, presenterId, graphics):
    sql_graphics = "select b.graphic_id, c.name, b.detail, b.label_id, \
		           b.color_id, b.x_axis_id, b.y_axis_id, b.column1_id, \
			   b.column2_id, b.column3_id, b.column4_id \
		      from simulation_presenter_graphic a, \
			   simulation_axis_graphic b, \
		           simulation_graphic c \
		     where a.graphic_id = b.graphic_id \
		       and a.presenter_id = '%d' \
		       and c.id = a.graphic_id  \
		     order by b.graphic_id" % (presenterId)
    cursor2.execute(sql_graphics)
    # Fetch all the rows in a list of lists.
    graphics_res = cursor2.fetchall()
    for row in graphics_res:
	# Establish detail property
	if (row[2] == 1):
	    detail = True
	else:
	    detail = False
	# Establish label property
	if ( row[3] > 0 ):
	    label = load_offered_data(cursor3, row[3])
	else:
	    label = None
	# Establish color property
	if ( row[4] > 0 ):
	    color = load_offered_data(cursor3, row[4])
	    colors = {}
	else:
	    color = None
	variable_x = load_offered_data(cursor3, row[5])
	variable_y = load_offered_data(cursor3, row[6])
	column1 = load_offered_data(cursor3, row[7])
	column2 = load_offered_data(cursor3, row[8])
	column3 = load_offered_data(cursor3, row[9])
	column4 = load_offered_data(cursor3, row[10])
	graphics[row[0]] = {'name': row[1], 'detail': detail,  
			     'x_axis' : variable_x, 'y_axis' : variable_y,
			     'label' : label, 'color' : color,
			     'instance_colors' : colors, 'column1' : column1, 
			     'column2' : column2, 'column3' : column3, 'column4' : column4}
     

if __name__ == '__main__':
    '''
    The PresenterExecution starts the threads for the presenter 
    agents.
    '''
    # Open database connection
    db = MySQLdb.connect("localhost","root","password","Network_Simulation" )

    # prepare a cursor object using cursor() method
    cursor = db.cursor()

    # Prepare SQL query to SELECT presenters from the database.
    sql = "SELECT id, name FROM simulation_presenter"

    sql2 = "select b.service_id \
	   from simulation_consumer a, simulation_consumerservice b \
	  where a.id = b.consumer_id \
	    and b.execute = 1 \
	    LIMIT 1"
    # Start providers
    try:
	
	# Retries the service Id.
	cursor.execute(sql2)
	# Fetch all the rows in a list of lists.
	serviceFound = False
	results = cursor.fetchall()
	for servicerow in results:
	    serviceId = str(servicerow[0])
	    serviceFound = True
	
	if (serviceFound == True):
	    presenters = []
	    cursor.execute(sql)
	    # Fetch all the rows in a list of lists.
	    results = cursor.fetchall()
	    i = 1
	    for row in results:
		presenterId = row[0]
		presenterName = row[1]
		graphics = {}
		cursor3 = db.cursor()
		cursor4 = db.cursor()
		logger.info('Ready to load Graphics')
		load_graphics(cursor3, cursor4, presenterId, graphics)
		logger.info('Graphics loaded')
		presenters.append(Presenter(presenterName +str(presenterId), 
					    presenterId, serviceId, graphics) )
		logger.info('Start presenter' + presenterName +str(presenterId))
	    # start the providers
	    for w in presenters:
		w.start()
	else:
	    logger.error('No service found, please check the configuration')

    except ProviderException as e:
	print e.__str__()
    except Exception as e:
	print e.__str__()
