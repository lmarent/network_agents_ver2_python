class ProviderException(Exception):
    '''
    When provider call this method, an exception is thrown.
    '''
    def __init__(self, value):
	self.message = value
    
    def __str__(self):
         return repr(self.message)
# End of ProviderException class
