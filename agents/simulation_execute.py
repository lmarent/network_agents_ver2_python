import subprocess
import MySQLdb
import shutil
import os
import inspect
import foundation.agent_properties
import time

def execute_process(exec_dir):
    try:
	clock_command = exec_dir + '/ClockManager2/src/ClockServer'
	clock_stdout = open('clockserver_stdout.log', "w")
	clock_stderr = open('clockserver_stderr.log', "w")
	clock = subprocess.Popen(clock_command, 
				 stdout=clock_stdout, 
				 stderr=clock_stderr, 
				 shell=True)
	time.sleep(0.1)
	
	market_command = exec_dir + '/MarketPlaceServer/src/MarketPlaceServer'
	market_stdout = open('marketserver_stdout.log', "w")
	market_stderr = open('marketserver_stderr.log', "w")
	market = subprocess.Popen(market_command, 
				  stdout=market_stdout, 
				  stderr=market_stderr,
				  shell=True)
	time.sleep(0.5)
	
	provider_command = '/usr/bin/python ' + exec_dir + '/agents/ProviderExecution.py'
	provider_stdout = open('providerexecution_stdout.log', "w")
	provider_stderr = open('providerexecution_stderr.log', "w")
	provider = subprocess.Popen(provider_command, 
				    stdout=provider_stdout, 
				    stderr=provider_stderr, 
				    shell=True)
	
	consumer_command = '/usr/bin/python ' + exec_dir + '/agents/ConsumerExecution.py'
	consumer_stdout = open('consumerexecution_stdout.log', "w")
	consumer_stderr = open('consumerexecution_stderr.log', "w")
	consumer = subprocess.Popen(consumer_command, 
				    stdout=consumer_stdout,  
				    stderr=consumer_stderr,  
				    shell=True)
	
	presenter_command = '/usr/bin/python ' + exec_dir + '/agents/PresenterExecution.py'
	presenter_stdout = open('presenterexecution_stdout.log', "w")
	presenter_stderr = open('presenterexecution_stderr.log', "w")
	presenter = subprocess.Popen(presenter_command, 
				     stdout=presenter_stdout, 
				     stderr=presenter_stderr, 
				     shell=True)

	provider_status = provider.wait()
	consumer_status = consumer.wait()
	presenter_status = presenter.wait()
	clock_status = clock.wait()
	market_status = market.wait()

	clock_stdout.close()
	clock_stderr.close()
	
	market_stdout.close()
	market_stderr.close()
	
	provider_stdout.close()
	provider_stderr.close()
	
	consumer_stdout.close()
	consumer_stderr.close()
	
	presenter_stdout.close()
	presenter_stderr.close()
	print 'Command exit Status/Return Code  provider_execution ' +  str(provider_status) + '\n'
	print 'Command exit Status/Return Code  consumer_execution ' +  str(consumer_status) + '\n'
	print 'Command exit Status/Return Code  presenter_execution ' +  str(presenter_status) + '\n'
	print 'Command exit Status/Return Code clock_server : ' +  str(clock_status) + '\n'
	print 'Command exit Status/Return Code market_server : ' +  str(market_status) + '\n'
    except Exception as e:
	print e

def update_consumers(cursor, consumer_id, num_consumers):
    sql = "update simulation_consumer \
	      set number_execute = '%d' \
	    where id = '%d' " % (num_consumers, consumer_id)
    cursor.execute(sql)

def update_periods(num_periods):
    sql = "update simulation_generalparameters \
	      set bid_periods = '%d'" % (num_periods)
    cursor.execute(sql) 
	
	
def update_provider(cursor, provider_id):
    sql = "update simulation_provider \
	      set status = 'A' \
	    where id = '%d' " % (provider_id)
    cursor.execute(sql)

def inactivate_providers(cursor):
    sql = "update simulation_provider \
	      set status = 'I' "
    cursor.execute(sql)
	
def read_configuration_step_providers(cursor, execution_configuration):
    sql = "select id, provider_id \
	     from simulation_executionconfigurationproviders \
	    where execution_configuration_id = '%d' " % (execution_configuration)
    providers = {}
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
	providers[row[0]] = { 'provider_id' : row[1] } 
    return providers

def read_configuration_steps(cursor, configuration_group):
    sql = "select id, description, number_consumers, number_periods \
	     from simulation_executionconfiguration \
	    where execution_group_id = '%d' \
	      and status = 'A'" % (configuration_group)
    steps = {}
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
	steps[row[0]] = { 'description' : row[1], 
			  'number_consumers' : row[2],
			  'number_periods' : row[3],
			}
    return steps

def read_consumer(cursor):
    sql = "select a.id \
	     from simulation_consumer a, simulation_consumerservice b \
	    where a.id = b.consumer_id \
	      and b.execute = 1 \
	    LIMIT 1 "	
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
	consumerId = row[0]
    return consumerId

def read_configuration_groups(cursor):
    sql = "select id, name, description \
	     from simulation_executiongroup \
	    where status = 'A'"
	
    groups = {}
    cursor.execute(sql)
    results = cursor.fetchall()
    for row in results:
	groups[row[0]] = {'name' : row[1], 'description' : row[2], 'steps' : {} }
    return groups

def removing_directory_content(directory):
    for the_file in os.listdir(directory):
	full_file_name = os.path.join(directory, the_file)
	try:
	    if (os.path.isfile(full_file_name)):
		os.unlink(full_file_name)
	except Exception, e:
	    print e

def copy_directory_content(src_directory, dst_directory):
    src_files = os.listdir(src_directory)
    for file_name in src_files:
	full_file_name = os.path.join(src_directory, file_name)
	des_file_name = os.path.join(dst_directory, file_name)
	if (os.path.isfile(full_file_name)):
	    shutil.copy(full_file_name, des_file_name)

def copy_logs_files(src_directory,dst_directory):
    src_files = os.listdir(src_directory)
    for file_name in src_files:
	if file_name.endswith('.log'):
	    full_file_name = os.path.join(src_directory, file_name)
	    des_file_name = os.path.join(dst_directory, file_name)
	    if (os.path.isfile(full_file_name)):
		shutil.copy(full_file_name, des_file_name)

def delete_log_files(directory):
    for the_file in os.listdir(directory):
	if the_file.endswith('.log'):
	    full_file_name = os.path.join(directory, the_file)
	    try:
		if (os.path.isfile(full_file_name)):
		    os.unlink(full_file_name)
	    except Exception, e:
		print e
    		

# Open database connection
db = MySQLdb.connect("localhost","root","password","Network_Simulation" )

# Prepare a cursor object using cursor() method
cursor = db.cursor()

# Brings the consumer 
consumer_id = read_consumer(cursor)

# Brings configuration groups.
groups = read_configuration_groups(cursor)

for groupId in groups:
	group = groups[groupId]
	steps = read_configuration_steps(cursor, groupId)
	group['steps'] = steps

# Brings the providers of every step.
for groupId in groups:
    group = groups[groupId]
    steps = group['steps']
    for stepId in steps:
	step = steps[stepId]
	providers = read_configuration_step_providers(cursor, stepId)
	step['providers'] = providers

file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
dir_path = file_path.split('/')
dir_path.pop()		# remove ./agents from the list
main_dir = '/'.join(dir_path)


result_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
result_dir = result_dir + '/' + foundation.agent_properties.result_directory


# Execute different configurations
for groupId in groups:
    group = groups[groupId]
    steps = group['steps']
    for stepId in steps:
	delete_log_files(file_path)
	step = steps[stepId]
	num_periods = step['number_periods']
	num_consumers = step['number_consumers']
	# Activate providers that must be executed in the configuration.
	inactivate_providers(cursor)
	for provider in step['providers']:
	    provider_id = ((step['providers']).get(provider)).get('provider_id')
	    print 'provider_id:' + str(provider_id)
	    # update the status of the provider
	    update_provider(cursor, provider_id)
	# Establish the correct number of consumers
	update_consumers(cursor, consumer_id, num_consumers)	
	# Updates the number of periods.
	update_periods(num_periods)
	cursor.connection.commit()
	# Executes the software
	execute_process(main_dir)
	# Create and copy the result files. The directory is created under the result folder. 
	# The name of the folder is composed by the group and step id
	folder_name = str(groupId) + '_' + str(stepId)
	directory = result_dir + '/' + folder_name
	if not os.path.exists(directory):
	    os.makedirs(directory)
	removing_directory_content(directory)
	copy_directory_content(result_dir, directory)
	copy_logs_files(file_path,directory)
		
