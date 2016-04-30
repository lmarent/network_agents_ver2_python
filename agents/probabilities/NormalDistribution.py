#-----------------------------------------------------------------------
# Name:        	Normal Probability Distribution
# Purpose:		Implement normal probability 
#-----------------------------------------------------------------------

import random
from scipy.stats import norm
from ProbabilityDistribution import ProbabilityDistribution

class NormalDistribution(ProbabilityDistribution):
    '''
    This class implements the normal probability distribution function.
    '''    
    def getParameters(self):
	dic_return = { 0 :'mean', 1 : 'sigma'}
	return dic_return
		
    def getSample(self, randomGenerator):
	'''
	Generates a number normal distributed and returns that 
	number.
	'''
	parameters = self.getParameters()
	instance= {}
	for parameter in parameters:
	    name = parameters[parameter]
	    value = self._parameters[name]
	    instance[parameter] = value

	p = randomGenerator.normalvariate(instance[0], instance[1])
	return p	

    def getName(self):
	'''
	This method prints the name of the probability distribution 
	function, in this case it prints NormalProbability.
	'''
	print 'the name of the class is NormalProbability'
