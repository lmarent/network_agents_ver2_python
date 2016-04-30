import xml.dom.minidom
from foundation.Message import Message
import logging
from foundation.Service import Service

class Bid(object):
    '''
    The Bid class defines methods required for the operation of the
    offers, including values and decision variables, as well as 
    Id, service provider, and service to be offered.
    '''

    ACTIVE = 1
    INACTIVE = 0

    def __init__(self):
	self._decision_variables = {}
	self._status = Bid.ACTIVE
	self._unitaryCost = 0
	self._unitaryProfit = 0
	self._parent = None # Bids that origin this bid.
	self._creation_period = 0
	
    def setValues(self, bidId, provider, service):
	'''
	This method receives the offer Id, service provider Id, and 
	service Id as parameters and assigns to related variables.
	'''
	self._provider = provider
	self._service = service
	self._bidId = bidId

    def setDecisionVariable(self, decisionVariable, value):
	'''
	This method sets a value to the decision variable.
	'''
	if decisionVariable in self._decision_variables:
	    raise FoundationException("Decision variable is already included")
	else:   
	    self._decision_variables[decisionVariable] = value

    def getDecisionVariable(self, decisionVariableId): 
	'''
	This method returns the decision variable.
	'''
	logging.debug('stating getDecisionVariable - Parameters:' + decisionVariableId)
	if decisionVariableId in self._decision_variables:			
	    return self._decision_variables[decisionVariableId]
	else:
	    raise FoundationException("The Decision variable is not part of the offer")

    def setUnitaryCost(self, unitaryCost):
	'''
	This method establishes the unitary cost of the offer.
	'''
	self._unitaryCost = unitaryCost
    
    def getUnitaryCost(self):
	'''
	This method returns the unitary cost of the offer.
	'''
	return self._unitaryCost
    
    def setUnitaryProfit(self, unitaryProfit):
	'''
	This method establishes the unitary profit of the offer
	'''
	self._unitaryProfit = unitaryProfit
    
    def getUnitaryProfit(self):
	'''
	This method returns the unitary profit of the offer
	'''
	return self._unitaryProfit
    
    def setCreationPeriod(self, creationPeriod):
	'''
	This method establishes the period when the bid was created
	'''
	self._creation_period = creationPeriod
    
    def getCreationPeriod(self):
	'''
	This method returns the period when the bid was created
	'''
	return self._creation_period
    
    def getText(self, nodelist):
	'''
	This method transform the object into XML.
	'''
	rc = []
	for node in nodelist:
	    if node.nodeType == node.TEXT_NODE:
		rc.append(node.data)
	return ''.join(rc)

    def handleDecisionVariable(self, variableXmlNode):
	'''
	This method assigns a name and value to a decision variable.
	'''
	nameElement = variableXmlNode.getElementsByTagName("Name")[0]
	name = self.getText(nameElement.childNodes)
	valueElement = variableXmlNode.getElementsByTagName("Value")[0]
	value = float(self.getText(valueElement.childNodes))
	self.setDecisionVariable(name, value)	
	
    def setFromXmlNode(self,bidXmlNode):
	'''
	This method converts the object from XML to string.
	'''
	bidIdElement = bidXmlNode.getElementsByTagName("Id")[0]
	bidId = self.getText(bidIdElement.childNodes)
	self._bidId = bidId
	providerElement = bidXmlNode.getElementsByTagName("Provider")[0]
	provider = self.getText(providerElement.childNodes)
	self._provider = provider
	serviceElement = bidXmlNode.getElementsByTagName("Service")[0]
	service = self.getText(serviceElement.childNodes)
	self._service = service
	statusElement = bidXmlNode.getElementsByTagName("Status")[0]
	status = self.getText(statusElement.childNodes)
	if (status == "inactive"):
	    self._status = Bid.INACTIVE
	else:
	    self._status = Bid.ACTIVE
	    
	variableXmlNodes = bidXmlNode.getElementsByTagName("Decision_Variable")
	for variableXmlNode in variableXmlNodes:
	    self.handleDecisionVariable(variableXmlNode)	
		
    def getId(self):
	'''
	This method gets offer Id.
	'''
	return self._bidId
		
    def getProvider(self):
	'''
	This method gets the provider Id.
	'''
	return self._provider
		
    def getService(self):
	'''
	This method returns the offer service.
	'''
	return self._service

    def setStatus(self, status):
	'''
	This method sets the offer status.
	'''
	self._status = status
		
    def __str__(self):
	val_return = 'Id:' + self._bidId + '\n'
	val_return = val_return + 'Provider:' + self._provider + '\n'
	val_return = val_return + 'Service:' + self._service + '\n'
	val_return = val_return + 'Status:' + self.getStatusStr() + '\n'
	for decisionVariable in self._decision_variables:
	    val_return = val_return + decisionVariable + str(self._decision_variables[decisionVariable]) + '\n'	    
	return val_return

    def getStatusStr(self):
	'''
	This method gets the offer status in a string format.
	'''
	if self._status == Bid.INACTIVE:
	    return "inactive"
	else:
	    return "active"

    def to_message(self):
	'''
	This method creates the offer message to be sent to the 
	marketplace.
	'''
	messageBid = Message('')
        messageBid.setMethod(Message.RECEIVE_BID)
        messageBid.setParameter('Id', self._bidId)
        messageBid.setParameter('Provider', self._provider)
        messageBid.setParameter('Service', self._service)
	messageBid.setParameter('Status', self.getStatusStr())
	for decisionVariable in self._decision_variables:
	    messageBid.setParameter(decisionVariable, str(self._decision_variables[decisionVariable]))
	return messageBid
    
    def setFromMessage(self, service, message):
	# Sets the general information
	self.setValues(message.getParameter("Id"), 
		       message.getParameter("Provider"), 
		       message.getParameter("Service"))
	status = message.getParameter("Status")
	if (status == "inactive"):
	    self._status = Bid.INACTIVE
	else:
	    self._status = Bid.ACTIVE
	
	# Sets the decision variables
	for decision_variable in service._decision_variables:
	    value = float(message.getParameter(decision_variable))
	    self.setDecisionVariable(decision_variable, value)

    def isEqual(self, bidtoCompare):
	''' 
	This methods establish if the offer pass as parameter has the
	same decision variables.
	'''
	equal = True
	for decisionVariable in self._decision_variables:
	    if ( self._decision_variables[decisionVariable] == 
		    bidtoCompare.getDecisionVariable(decisionVariable)):
		pass
	    else:
		equal = False
		break
	return equal

    def insertParentBid(self, bid):
	'''
	This method inserts the bid as parameter as a parent of this bid.
	'''
	self._parent = bid
