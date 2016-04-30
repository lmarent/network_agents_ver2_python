#-----------------------------------------------------------------------
# Name:        	Beta Probability Distribution
# Purpose:		Implement beta probability
#-----------------------------------------------------------------------

import random
from scipy.stats import beta
from ProbabilityDistribution import ProbabilityDistribution

class BetaDistribution(ProbabilityDistribution):
    '''
    This class implements the beta probability distribution function.
    '''
    def getParameters(self):
	dic_return = { 0 :'alpha', 1 : 'beta'}
	return dic_return    

    def getSample(self, randomGenerator):
	'''
	Generates a number with a beta probability and returns that 
	number.
	'''		
	# generates a random beta parameter for the distribution
	
	parameters = self.getParameters()
	instance= {}
	for parameter in parameters:
	    name = parameters[parameter]
	    value = self._parameters[name]
	    instance[parameter] = value
	    	
	p = randomGenerator.betavariate(instance[0], instance[1])
	return p	

    def getName(self):
	'''
	This method prints the name of the probability distribution 
	function, in this case it prints BetaProbability.
	'''		
	print 'the name of the class is BetaProbability'




