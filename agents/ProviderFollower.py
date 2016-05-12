from Provider import Provider
from foundation.FoundationException import FoundationException
from ProviderAgentException import ProviderException
from foundation.Agent import AgentServerHandler
from foundation.DecisionVariable import DecisionVariable
import logging
import numpy as np
from scipy.cluster.vq import kmeans,vq

logger = logging.getLogger('provider_application')

class ProviderFollower(Provider):

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
	    super(ProviderFollower, self).__init__(strID, Id, serviceId, providerSeed, marketPosition, 
			    adaptationFactor, monopolistPosition, debug, 
			    resources, numberOffers, numAccumPeriods, 
			    numAncestors, startFromPeriod)
	    self._used_variables['InnovationFactor'] = 0.5
	except FoundationException as e:
	    raise ProviderException(e.__str__())

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
		      self._list_vars['Id'], str(centroids))
	# Iterate over the list of clusters and create clusters 
	return numCentroids, centroids

    def createBidsOnCluster(self, centroid):
	logger.debug('Agent %s - createBidsOnCluster - Start %s', 
		      self._list_vars['Id'], str(centroid))
	output= {}
	j = 0
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
		min_val_adj, max_val_adj = self.calculateIntervalsQuality(self._used_variables['marketPosition'], min_val, max_val, optimum)
	    else:
		min_val_adj, max_val_adj = self.calculateIntervalsPrice(self._used_variables['marketPosition'], min_val, max_val)
	    if (max_val_adj != 0):
		adjust = (self._list_vars['Random'].uniform(min_val_adj, max_val_adj)) / max_val_adj
	    else:
		adjust = 0
	    adjust = adjust * (max_val_adj - min_val_adj)
	    logger.debug('Agent %s - createBidsOnCluster - DecisionVariable %s - Adjust: %s', 
		      self._list_vars['Id'], str(decisionVariable),  str(adjust))
	    if optimum == 1:
		output[decisionVariable] = centroid[j]
	    else:
		output[decisionVariable] = centroid[j]
	    j = j + 1
	logger.debug('Agent %s - createBidsOnCluster - Out: %s', 
		      self._list_vars['Id'], str(output))
	return output
    
    def initilizeFromBidList(self, k, bidList):
	output = {}
	numCentroids, centroids = self.formBidClusters(k, bidList)
	i = 0 
	while i < numCentroids:
	    newBidData = self.createBidsOnCluster(centroids[i,:])
	    output[i] = newBidData
	    i = i + 1
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
	
