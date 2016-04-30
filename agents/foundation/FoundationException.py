class FoundationException(Exception):
    '''
    When this method is called, an exception is thrown.
    '''
    def __init__(self, value):
	self.message = value
    def __str__(self):
	return repr(self.message)
	
# End of FoundationException class
