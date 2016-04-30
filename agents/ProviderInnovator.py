from Provider import Provider
from foundation.FoundationException import FoundationException
from ProviderAgentException import ProviderException
from foundation.Agent import AgentServerHandler
from foundation.DecisionVariable import DecisionVariable
import logging
import numpy as np
from scipy.cluster.vq import kmeans,vq

logger = logging.getLogger('provider_application')


class ProviderInnovator(Provider):

    LOW_MARKET_POSITION = 0.2
    HIGH_MARKET_POSITION = 0.8
	
    def __init__(self, strID, Id, serviceId, providerSeed, marketPosition, 
		 adaptationFactor, monopolistPosition, debug, 
		 resources, numberOffers, numAccumPeriods, numAncestors, startFromPeriod):
	try:
	    logger.info('Initializing the provider:' + strID + 'Id:' + str(Id) 
			  + 'Service Id:' + serviceId
			  + 'seed:' + str(providerSeed)
		          + 'market position:' + str(marketPosition)
			  + 'monopolist position:' + str(monopolistPosition)
			  + 'debug:' + str(debug) )
	    super(ProviderInnovator, self).__init__(strID, Id, serviceId, providerSeed, marketPosition, 
			    adaptationFactor, monopolistPosition, debug, 
			    resources, numberOffers, numAccumPeriods, 
			    numAncestors, startFromPeriod)
	    self._used_variables['InnovationFactor'] = 0.5
	except FoundationException as e:
	    raise ProviderException(e.__str__())
	

    def calculateBidUnitaryCost(self, bid):
	logger.debug('Starting - calculateBidUnitaryCost')
	totalUnitaryCost = 0
	totalPercentage = 0
	resources = self._used_variables['resources']
	for decisionVariable in (self._service)._decision_variables:
	    minValue = ((self._service)._decision_variables[decisionVariable]).getMinValue()
	    maxValue = ((self._service)._decision_variables[decisionVariable]).getMaxValue()
	    resourceId = ((self._service)._decision_variables[decisionVariable]).getResource() 
	    if ((self._service)._decision_variables[decisionVariable].getModeling() 
		    == DecisionVariable.MODEL_QUALITY):
		value = float(bid.getDecisionVariable(decisionVariable))
		if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() \
		    == DecisionVariable.OPT_MAXIMIZE):
		    percentage = (value - minValue) / minValue
		else:
		    percentage = (maxValue - value) / maxValue
		totalPercentage = totalPercentage + ( percentage * self._used_variables['InnovationFactor'] )
		if resourceId in resources:
		    unitaryCost = float((resources[resourceId])['Cost'])
		    totalUnitaryCost = totalUnitaryCost + (unitaryCost * (1+totalPercentage) )
	logger.debug('End - calculateBidUnitaryCost:' + str(totalUnitaryCost))
	return totalUnitaryCost  


    def initializeBids(self, k):
	'''
	Method to initialize offers. It receives a signal from the 
	simulation environment (demand server) with its position 
	in the market. The argument position serves to understand 
	if the provider at the beginning is oriented towards low 
	price (0) or high quality (1). Providers innovators 
	can compite with offers with high quality and low price. 
	'''
	logger.debug('Starting - initial bid generation innovator')
	output = {}
	#initialize the k points
	for i in range(0,k):
	    output[i] = {}
	for decisionVariable in (self._service)._decision_variables:
	    if ((self._service)._decision_variables[decisionVariable].getModeling() 
		== DecisionVariable.MODEL_PRICE):
		min_val = (self._service)._decision_variables[decisionVariable].getMinValue()
		max_val = (self._service)._decision_variables[decisionVariable].getMaxValue()
		min_val_adj, max_val_adj = self.calculateIntervalsPrice(ProviderInnovator.LOW_MARKET_POSITION, min_val, max_val)
		if (k == 1):
		    (output[0])[decisionVariable] = min_val_adj
		elif (k >= 2):
		    step_size = (max_val_adj - min_val_adj) / (k - 1)
		    for i in range(0,k):
			(output[i])[decisionVariable] = min_val_adj + step_size * i
		
	for decisionVariable in (self._service)._decision_variables:
	    if ((self._service)._decision_variables[decisionVariable].getModeling() 
		== DecisionVariable.MODEL_QUALITY):
		if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() \
		    == DecisionVariable.OPT_MAXIMIZE):
		    optimum = 1 # Maximize
		else:
		    optimum = 2 # Minimize
			
		min_val = (self._service)._decision_variables[decisionVariable].getMinValue()
		max_val = (self._service)._decision_variables[decisionVariable].getMaxValue()
		min_val_adj, max_val_adj = self.calculateIntervalsQuality(ProviderInnovator.HIGH_MARKET_POSITION, min_val, max_val, optimum)
		if (optimum == 1):
		    if (k == 1):
			(output[0])[decisionVariable] = min_val_adj
		    elif (k >= 2):
			step_size = (max_val_adj - min_val_adj) / (k - 1)
			for i in range(0,k):
			    (output[i])[decisionVariable] = min_val_adj + (step_size * i)
		else:
		    if (k == 1):
			(output[0])[decisionVariable] = max_val_adj
		    elif (k >= 2):
			step_size = (max_val_adj - min_val_adj) / (k - 1)
			for i in range(0,k):
			    (output[i])[decisionVariable] = max_val_adj - (step_size * i)
	logger.debug('Ranges created in bid initialization innovator - NumOffers:' 
		      +  str(k) + 'output' + str(output))
	return self.createInitialBids(k, output)

    def formBidClusters(self, k, bidList):
	logger.debug('Agent %s - formBidClusters:', 
		      self._list_vars['Id'])
	numDecisionVariables = len((self._service)._decision_variables)
	numBids = len(bidList)
	data = np.zeros((numBids, numDecisionVariables))
	i = 0
	for bid in bidList:
	   j = 0 
	   for decisionVariable in (self._service)._decision_variables:
	       data[i,j] = bid.getDecisionVariable(decisionVariable)
	       j = j + 1
	   i = i + 1
	logger.debug('Agent %s - formBidClusters - Data: %s', 
		      self._list_vars['Id'], data)
	
	if numBids > k:
	    numCentroids = k
	else:
	    numCentroids = numBids
	centroids,_ = kmeans(data, numCentroids)
	idx,_ = vq(data,centroids)
	logger.debug('Agent %s - formBidClusters - Centroids %s', 
		      self._list_vars['Id'], str(idx))
	# Iterate over the list of clusters and create clusters 
	bidClusters = {}
	i = 0
	while (i < numCentroids):
	    bidClusters[i] = None
	    j = 0 
	    while (j < idx.size):
		if (idx[j] == i):
		    if (bidClusters[i] == None):
			bidClusters[i] = data[j,:]
		    else:
			bidClusters[i] = np.vstack( [bidClusters[i], data[j,:] ])
		j = j + 1
	    i = i + 1
	logger.debug('Agent %s - formBidClusters - Output %s', 
		      self._list_vars['Id'], str(bidClusters))
	return bidClusters

    def createDominateBidOnCluster(self, clusterBidList):
	logger.debug('Agent %s - createDominateBidOnCluster - Start %s', 
		      self._list_vars['Id'], str(clusterBidList))
	output= {}
	i = 0
	for decisionVariable in (self._service)._decision_variables:
	    if ((self._service)._decision_variables[decisionVariable].getOptimizationObjective() \
		    == DecisionVariable.OPT_MAXIMIZE):
		optimum = 1 # Maximize
	    else:
		optimum = 2 # Minimize
	    min_val = (self._service)._decision_variables[decisionVariable].getMinValue()
	    max_val = (self._service)._decision_variables[decisionVariable].getMaxValue()
	    if ((self._service)._decision_variables[decisionVariable].getModeling() 
		== DecisionVariable.MODEL_QUALITY):
		min_val_adj, max_val_adj = self.calculateIntervalsQuality(ProviderInnovator.HIGH_MARKET_POSITION, min_val, max_val, optimum)
	    else:
		min_val_adj, max_val_adj = self.calculateIntervalsPrice(ProviderInnovator.LOW_MARKET_POSITION, min_val, max_val)
	    if (max_val_adj != 0):
		adjust = (self._list_vars['Random'].uniform(min_val_adj, max_val_adj)) / max_val_adj
	    else:
		adjust = 0
	    adjust = adjust * (max_val_adj - min_val_adj)
	    logger.debug('Agent %s - createDominateBidOnCluster - DecisionVariable %s - Adjust: %s', 
		      self._list_vars['Id'], str(decisionVariable),  str(adjust))
	    logger.debug('Agent %s - createDominateBidOnCluster %s', 
			  self._list_vars['Id'], str(clusterBidList.shape))
	    if (clusterBidList.shape == (2,)):
		if optimum == 1:
		    output[decisionVariable] = clusterBidList[i] + adjust
		else:
		    output[decisionVariable] = clusterBidList[i] - adjust
	    else:
		if optimum == 1:
		    output[decisionVariable] = np.max(clusterBidList[:,i]) + adjust
		else:
		    output[decisionVariable] = np.min(clusterBidList[:,i]) - adjust
	    i = i + 1
	logger.debug('Agent %s - createDominateBidOnCluster - Out: %s', 
		      self._list_vars['Id'], str(output))
	return output
    
    def initilizeFromBidList(self, k, bidList):
	output = {}
	bidClusters = self.formBidClusters(k, bidList)
	for cluster in bidClusters:
	    newBidData = self.createDominateBidOnCluster(bidClusters[cluster])
	    output[cluster] = newBidData
	return output
    
    def initilizeFromFronts(self, k, fronts):
	# Sorts the offerings  based on the customer's needs, only iterate
	# on the first pareto front.
	logger.debug('The agent %s is initializing from Fronts', 
			self._list_vars['Id'])
			
	keys_sorted = sorted(fronts,reverse=True)
	output = {}
	for front in keys_sorted:
	    bidList = fronts[front]
	    output = self.initilizeFromBidList(k, bidList)
	    break
	logger.debug('The agent %s is initializing from Fronts - Output: %s', 
			self._list_vars['Id'], str(output))
	return self.createInitialBids(k, output)

    def exec_algorithm(self):
        '''
	This method checks if the service provider is able to place an 
	offer in the marketplace, i.e. if the offering period is open.
	If this is the case, it will place the offer at the best position
	possible.
	'''
        logger.debug('The state for agent %s is %s', 
			self._list_vars['Id'], str(self._list_vars['State']))
	fileResult = open(self._list_vars['Id'] + '.log',"a")
	self.registerLog(fileResult, 'executing algorithm - Period: ' + 
			 str(self._list_vars['Current_Period']) )
        if (self._list_vars['State'] == AgentServerHandler.BID_PERMITED):
	    logger.info('Biding for agent %s in the period %s', 
			   str(self._list_vars['Id']), 
			   str(self._list_vars['Current_Period']))

	    logger.debug('Number of bids: %s for provider: %s', \
			len(self._list_vars['Bids']), self._list_vars['Id'])
	    staged_bids = {}
	    if (self._used_variables['startPeriod'] <= 
		    self._list_vars['Current_Period']):
		if (len(self._list_vars['Bids']) == 0):
		    serviceId = (self._service).getId()
		    fronts = self.createAskBids(serviceId)
		    marketPosition = self._used_variables['marketPosition']
		    initialNumberBids = self._used_variables['initialNumberBids']
		    if (len(fronts) == 0):
			staged_bids = self.initializeBids(initialNumberBids)
		    else:
			# Initilize based on bids actually on the market.
			staged_bids = self.initilizeFromFronts(initialNumberBids, fronts)
		    
		    logger.debug('Number of created bids: %s for provider innovator: %s', 
			    str(len(staged_bids)), self._list_vars['Id']) 
		else:
		    # By assumption providers at this point have the bid usage updated.
		    summarizedUsage = self.sumarizeBidUsage() 
		    self.replaceDominatedBids(staged_bids) 
		    if (self.canAdoptStrongPosition(fileResult)):
			self.moveBetterProfits(summarizedUsage, staged_bids, fileResult)
		    else:
			self.moveForMarketShare(summarizedUsage, staged_bids, fileResult)
		
		self.eliminateNeighborhoodBid(staged_bids, fileResult)
		self.registerLog(fileResult, 'The Final Number of Staged offers is:' + str(len(staged_bids)) ) 
		self.sendBids(staged_bids, fileResult) #Pending the status of the bid.
		self.purgeBids(staged_bids, fileResult)
		fileResult.close()
	    else:
		pass
	self._list_vars['State'] = AgentServerHandler.IDLE
	    
	logger.info('Ending exec_algorithm %s is %s', 
			self._list_vars['Id'], str(self._list_vars['State']))
