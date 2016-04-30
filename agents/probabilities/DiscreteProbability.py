import random
from ProbabilityDistribution import ProbabilityDistribution

class DiscreteProbability(ProbabilityDistribution):
    '''
    This class implements the discrete probability functions.
    '''    

    def getSample(self, randomGenerator):
	'''
	Generates a random number uniformly distributed.
	'''
	# Generates a random float x, 0.0 <= x < 1.0
	x = randomGenerator.uniform(0,1)
	sorted_dict = (sorted((self._points).items(),  key=lambda t: t[0]))
	# If the number falls in a certain range, return a value
	lower_limit = 0
	for i in sorted_dict:
	    upper_limit = i[1] + lower_limit
	    if x > lower_limit and x < upper_limit: 
		return i[0]
	    else:
		lower_limit = upper_limit

    def getName(self):
	'''
	This method prints the name of the probability distribution 
	function, in this case it prints DiscreteProbability.
	'''
	print 'the name of the class is DiscreteProbability'	
