from FoundationException import FoundationException

class Message(object):
    '''
    The Message class declares methods to handle the messaging part of
    the system. These methods include set and get message parameters 
    and body, and check if the message was received by the marketplace.
    '''
    # Initialize constants
    UNDEFINED = 1
    CONNECT = 2
    RECEIVE_BID = 3
    SEND_PORT = 4
    START_PERIOD = 5
    END_PERIOD = 6
    RECEIVE_PURCHASE = 7
    GET_BEST_BIDS = 8
    GET_CURRENT_PERIOD = 9
    DISCONNECT = 10
    GET_SERVICES = 11
    ACTIVATE_CONSUMER = 12
    RECEIVE_PURCHASE_FEEDBACK = 13
    SEND_AVAILABILITY = 14
    RECEIVE_BID_INFORMATION = 15
    GET_BID = 16
    GET_PROVIDER_CHANNEL = 17
    GET_UNITARY_COST = 18
    ACTIVATE_PRESENTER = 19
    
    # define the separator
    LINE_SEPARATOR = '\r\n'
    
    MESSAGE_SIZE = 10
	
    def __init__(self, messageStr):
	self._method = Message.UNDEFINED
	self._body = ''
	self._parameters = {}
	# Split message string when encounter LINE_SEPARATOR
	splitList = messageStr.split(Message.LINE_SEPARATOR)
	count = len(splitList)
	# Split message string when encounter ':'
	# Assign methods
	
	if (count > 0):
	    methodLine = splitList[0]
	    methodParam = methodLine.split(':')
	    if (len(methodParam) == 2):
		if (methodParam[1] == 'receiveBid'):
		    self._method = Message.RECEIVE_BID
		elif (methodParam[1] == 'connect'):
		    self._method = 	Message.CONNECT
		elif (methodParam[1] == 'disconnect'):
		    self._method = 	Message.DISCONNECT		    
		elif (methodParam[1] == 'send_port'):
		    self._method = Message.SEND_PORT
		elif (methodParam[1] == 'start_period'):
		    self._method = Message.START_PERIOD
		elif (methodParam[1] == 'end_period'):
		    self._method = Message.END_PERIOD
		elif (methodParam[1] == 'receive_purchase'):
		    self._method = Message.RECEIVE_PURCHASE
		elif (methodParam[1] == 'get_best_bids'):
		    self._method = Message.GET_BEST_BIDS
		elif (methodParam[1] == 'get_services'):
		    self._method = Message.GET_SERVICES
		elif (methodParam[1] == 'activate_consumer'):
		    self._method = Message.ACTIVATE_CONSUMER
		elif (methodParam[1] == 'receive_purchase_feedback'):
		    self._method = Message.RECEIVE_PURCHASE_FEEDBACK
		elif (methodParam[1] == 'send_availability'):
		    self._method = Message.SEND_AVAILABILITY		
		elif (methodParam[1] == 'receive_bid_information'):
		    self._method = Message.RECEIVE_BID_INFORMATION				
		elif (methodParam[1] == 'get_bid'):
		    self._method = Message.GET_BID				
		elif (methodParam[1] == 'get_provider_channel'):
		    self._method = Message.GET_PROVIDER_CHANNEL		
		elif (methodParam[1] == 'get_unitary_cost'):
		    self._method = Message.GET_UNITARY_COST
		elif (methodParam[1] == 'activate_presenter'):
		    self._method = Message.ACTIVATE_PRESENTER
		else:
		    self._method = Message.UNDEFINED
	# Repeat for each line to get the parameters
	if (count > 1):
	    i = 1
	    # Extracts the message header
	    while (i < count):
		paramLine = splitList[i]
		if (len(paramLine) == 0): 
		    # Corresponds to the empty line
		    break
		else:
		    lineParam = paramLine.split(':')
		    if (len(lineParam) == 2):
			self._parameters[lineParam[0]] = lineParam[1]
		i += 1
	    # Extracts the body
	    while (i < count):
		self._body = self._body + splitList[i]
		i += 1
	
    def setParameter(self, parameterKey, parameterValue):
	'''
	This method add the parameter to the list of parameters.
	'''
	# First we check if the parameter key is already on the list
	if parameterKey  in self._parameters:
	    # If it is already on the list, we create an exception
	    raise FoundationException('Parameter is already included on the list')
	# If not, we add the parameter to the list
	else:
	    self._parameters[parameterKey] = parameterValue
			
    def getParameter(self, param):
	'''
	This method returns the message parameter.
	'''
        if param in self._parameters:
            return self._parameters[param]
        else:
            raise FoundationException('Parameter not found')
    
    def setBody(self,param):
	'''
	This method sets the message body.
	'''
	self._body = param
	
    def getBody(self):
	'''
	This method returns the message body.
	'''
	return self._body
    
    def setMethod(self, method):
	'''
	This method sets the methos according with the message status.
	'''
        # Check if the provided method is correct
        # if it's not correct, we put undefined
        if (method == Message.RECEIVE_BID):
            self._method = Message.RECEIVE_BID
        elif (method == Message.CONNECT):
            self._method = Message.CONNECT
        elif (method == Message.DISCONNECT):
            self._method = Message.DISCONNECT            
        elif (method == Message.SEND_PORT):
            self._method = Message.SEND_PORT
        elif (method == Message.START_PERIOD):
            self._method = Message.START_PERIOD
        elif (method == Message.END_PERIOD):
            self._method = Message.END_PERIOD
        elif (method == Message.RECEIVE_PURCHASE):
            self._method = Message.RECEIVE_PURCHASE
        elif (method == Message.GET_BEST_BIDS):
            self._method = Message.GET_BEST_BIDS
	elif (method == Message.GET_SERVICES):
            self._method = Message.GET_SERVICES
	elif (method == Message.ACTIVATE_CONSUMER):
            self._method = Message.ACTIVATE_CONSUMER
	elif (method == Message.RECEIVE_PURCHASE_FEEDBACK):
            self._method = Message.RECEIVE_PURCHASE_FEEDBACK
	elif (method == Message.SEND_AVAILABILITY):
            self._method = Message.SEND_AVAILABILITY
	elif (method == Message.RECEIVE_BID_INFORMATION):
	    self._method = Message.RECEIVE_BID_INFORMATION				
	elif (method == Message.GET_BID):
	    self._method = Message.GET_BID
	elif (method == Message.GET_PROVIDER_CHANNEL):
	    self._method = Message.GET_PROVIDER_CHANNEL
	elif (method == Message.GET_UNITARY_COST):
	    self._method = Message.GET_UNITARY_COST
	elif (method == Message.ACTIVATE_PRESENTER):
	    self._method = Message.ACTIVATE_PRESENTER
        else:
            self._method = Message.UNDEFINED
	
    def getMethod(self):
	'''
	Thi method returns the current message status.
	'''
	return self._method
    
    def getStringMethod(self):
	'''
	Similar to getMethod, this method returns the current message
	status, but in a string format.
	'''
	if (self._method == Message.RECEIVE_BID):
	    return "receive_bid"
	elif (self._method == Message.CONNECT):
	    return "connect"
	elif (self._method == Message.DISCONNECT):
	    return "disconnect"
	elif (self._method == Message.SEND_PORT):
	    return "send_port"
	elif (self._method == Message.START_PERIOD):
	    return "start_period"
	elif (self._method == Message.END_PERIOD):
	    return "end_period"
	elif (self._method == Message.RECEIVE_PURCHASE):
	    return "receive_purchase"
	elif (self._method == Message.GET_BEST_BIDS):
	    return "get_best_bids"
	elif (self._method == Message.GET_SERVICES):
	    return "get_services"
	elif (self._method == Message.ACTIVATE_CONSUMER):
	    return "activate_consumer"
	elif (self._method == Message.RECEIVE_PURCHASE_FEEDBACK):
	    return "receive_purchase_feedback"
	elif (self._method == Message.SEND_AVAILABILITY):
	    return "send_availability"
	elif (self._method == Message.RECEIVE_BID_INFORMATION):
	    return "receive_bid_information"
	elif (self._method == Message.GET_BID):
	    return "get_bid"
	elif (self._method == Message.GET_PROVIDER_CHANNEL):
	    return "get_provider_channel"
	elif (self._method == Message.GET_UNITARY_COST):
	    return "get_unitary_cost"
	elif (self._method == Message.ACTIVATE_PRESENTER):
	    return "activate_presenter"

    def __str__(self):
	'''
	This method reconstructs the original message appending 
	its parameters.
	'''
	result = 'Method:'
	if self.getStringMethod() is not None:
	    result = result + self.getStringMethod()
	result = result + Message.LINE_SEPARATOR
	
	result2 = ''
	for item in self._parameters:
	    result2 = result2 + item
	    result2 = result2 + ':'
	    result2 = result2 + self._parameters[item]		
	    result2 = result2 + Message.LINE_SEPARATOR

	result2 = result2 + Message.LINE_SEPARATOR
	if self._body is not None:
	    result2 = result2 + self._body
	
	result = result + 'Message_Size:'
	size = len(result) + len(result2) + 2 + Message.MESSAGE_SIZE
	sizeStr = str(size).zfill(Message.MESSAGE_SIZE)
	result = result + sizeStr
	result = result + Message.LINE_SEPARATOR
	result = result + result2
	return result
		
    def isMessageStatusOk(self):
	'''
	This method checks if the message was sucesfully received.
	'''
	if ('Status_Code' in self._parameters):
	    code = int(self.getParameter('Status_Code'))
	    if (code == 200):
		return True
	    else:
		return False
	return False

    def setMessageStatusOk(self):
	''' 
	This method establishes the message as Ok
	'''
	self.setParameter("Status_Code", "200");
	self.setParameter("Status_Description", "OK");

    def isComplete(self, lenght):
	try:
	    size = self.getParameter("Message_Size")
	    messageSize = int(size)
	    if (lenght == messageSize):
		return True
	    else:
		return False
	except FoundationException as e:
	    print 'The message is' + '\n' + self.__str__()
	    raise FoundationException("Parameter not found")
	except ValueError as e:
	    print 'The value in size is' + str(size)
	    raise FoundationException("Invalid value inside Message Size")

# End of Message class
