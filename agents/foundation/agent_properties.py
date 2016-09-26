'''
This file defines the agent_properties.
'''
# ClockServer listening port and Marketplace listening port are
# defined below.
clock_listening_port = 3333
mkt_place_listening_port = 5555

# The listening ports for presenter, provider, and consumer are 
# defined below.
l_port_presenter = 12000
l_port_provider = 13000
l_port_consumer = 14000

# Address for the database server information
addr_database = '10.10.6.1'
port_database = 3306
user_database = 'admin'
user_password = 'password'
database_name = 'Network_Simulation'

# Addresses for marketplace, clockserver, and own agent address
# are defined below.
addr_mktplace_isp = '10.10.6.2'
addr_mktplace_backhaul = '10.10.4.2'
addr_clock_server = '10.10.6.1'
addr_agent_mktplace_isp = '10.10.4.1'
addr_agent_mktplace_backhaul = '10.10.4.1'
addr_agent_clock = '10.10.4.1'


threshold = 2
own_neighbor_radius = 0.05
others_neighbor_radius = 100 # almost every bid is in the neighbor.
initial_number_bids = 5
num_periods_market_share = 3
intervals_per_cycle = 2
provider_types = 'Provider'

#directory results
result_directory = 'results/'
