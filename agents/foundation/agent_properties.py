'''
This file defines the agent properties.
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

# Addresses for marketplace, clockserver, and own agent address
# are defined below.
addr_mktplace_isp = '192.168.2.12'
addr_mktplace_backhaul = '192.168.2.13'
addr_clock_server = '192.168.2.12'
addr_agent = '192.168.2.13'

threshold = 0.5
neighbor_radius = 0.03
initial_number_bids = 1
num_periods_market_share = 3

#directory results
result_directory = 'results/'
