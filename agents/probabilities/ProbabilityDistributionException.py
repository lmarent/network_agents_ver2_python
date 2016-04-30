class ProbabilityDistributionException(Exception):
    '''
    When this method is called, an exception is thrown.
    '''
    def __init__(self, value):
	self.value = value
	
    def __str__(self):
	return repr(self.value)
	 
# End of ProbabilityDistributionException class
