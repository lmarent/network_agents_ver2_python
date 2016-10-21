from foundation.Message import Message
import logging
import FoundationException
import xml.dom.minidom
import uuid


'''
The Bid class defines methods required for the operation of the
offers, including values and decision variables, as well as 
Id, service provider, and service to be offered.
'''
class Bid(object):

    ACTIVE = 1
    INACTIVE = 0

    def __init__(self):
        # These are the offered variables for customers.        
        self._decision_variables = {}
        self._status = Bid.ACTIVE
        self._unitaryCost = 0
        self._unitaryProfit = 0
        self._parent = None # Bids that origin this bid.
        self._creation_period = 0
        self._providerBid = None # bid that generates this bid.
        self._numAncestors = 0 # This indicates how many ancestors a bid have.
        
        # These are the specific requirements with respect to quality 
        # that providers should cover with own resources, 
        # if not defined are equal to those in specified in the decision variables.
        self._qualityRequirements = {} 
        self._capacity = 0

    '''
    This method receives the offer Id, service provider Id, and 
    service Id as parameters and assigns to related variables.
    '''
    def setValues(self, bidId, provider, service):
        	self._provider = provider
        	self._service = service
        	self._bidId = bidId

    '''
    This method receives the offer Id as a parameter and assigns it.
    '''
    def setId(self, bidId):
        self._bidId = bidId 
    
    '''
    This method sets a value to the decision variable.
    '''
    def setDecisionVariable(self, decisionVariable, value):
        self._decision_variables[decisionVariable] = value

    '''
    This method returns the decision variable.
    '''
    def getDecisionVariable(self, decisionVariableId): 
        	#logging.debug('stating getDecisionVariable - Parameters:' + decisionVariableId)
        	if decisionVariableId in self._decision_variables:			
        	    return self._decision_variables[decisionVariableId]
        	else:
        	    raise FoundationException("The Decision variable is not part of the offer")

    '''
    This method establishes the unitary cost of the offer.
    '''
    def setUnitaryCost(self, unitaryCost):
        	self._unitaryCost = unitaryCost
    
    '''
    This method returns the unitary cost of the offer.
    '''
    def getUnitaryCost(self):
        	return self._unitaryCost
    
    '''
    This method establishes the unitary profit of the offer
    '''
    def setUnitaryProfit(self, unitaryProfit):
        	self._unitaryProfit = unitaryProfit
    
    '''
    This method returns the unitary profit of the offer
    '''
    def getUnitaryProfit(self):
        	return self._unitaryProfit
    
    '''
    This method establishes the period when the bid was created
    '''
    def setCreationPeriod(self, creationPeriod):
        	self._creation_period = creationPeriod
    
    '''
    This method returns the period when the bid was created
    '''
    def getCreationPeriod(self):
        	return self._creation_period
    
    '''
    This method transform the object into XML.
    '''
    def getText(self, nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)

    '''
    This method assigns a name and value to a decision variable.
    '''
    def handleDecisionVariable(self, variableXmlNode):
        nameElement = variableXmlNode.getElementsByTagName("Name")[0]
        name = self.getText(nameElement.childNodes)
        valueElement = variableXmlNode.getElementsByTagName("Value")[0]
        value = float(self.getText(valueElement.childNodes))
        self.setDecisionVariable(name, value)

    '''
    This method converts the object from XML to string.
    '''
    def setFromXmlNode(self,bidXmlNode):
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

        parentBidElement = bidXmlNode.getElementsByTagName("ParentBid")[0]
        parentBidId = self.getText(parentBidElement.childNodes)
        parentBid = Bid()
        parentBid.setId(parentBidId)
        self.insertParentBid(parentBid)
        
        variableXmlNodes = bidXmlNode.getElementsByTagName("Decision_Variable")
        for variableXmlNode in variableXmlNodes:
            self.handleDecisionVariable(variableXmlNode)

    '''
    This method gets offer Id.
    '''
    def getId(self):
        return self._bidId	

    '''
    This method gets the provider Id.
    '''
    def getProvider(self):
        return self._provider

    '''
    This method returns the offer service.
    '''
    def getService(self):
        return self._service

    '''
    This method sets the offer status.
    '''
    def setStatus(self, status):
        self._status = status
    
    def __str__(self):
        val_return = 'Id:' + self._bidId + ' '
        val_return = val_return + ':Provider:' + self._provider + ' '
        val_return = val_return + ':Service:' + self._service + ' '
        val_return = val_return + ':Status:' + self.getStatusStr() + ' '
        for decisionVariable in self._decision_variables:
            val_return = val_return + ':desc_var:' + decisionVariable + ':value:'+ str(self._decision_variables[decisionVariable]) + ' '
        return val_return

	'''
	This method gets the offer status in a string format.
	'''
    def getStatusStr(self):
        if self._status == Bid.INACTIVE:
            return "inactive"
        else:
            return "active"
    
    def isActive(self):
        if self._status == Bid.INACTIVE:
            return False
        else:
            return True
    
	'''
	This method creates the offer message to be sent to the 
	marketplace.
	'''
    def to_message(self):
        messageBid = Message('')
        messageBid.setMethod(Message.RECEIVE_BID)
        messageBid.setParameter('Id', self._bidId)
        messageBid.setParameter('Provider', self._provider)
        messageBid.setParameter('Service', self._service)
        messageBid.setParameter('Status', self.getStatusStr())
        messageBid.setParameter('UnitaryProfit', str(self.getUnitaryProfit() ))
        messageBid.setParameter('UnitaryCost', str(self.getUnitaryCost() ))
        messageBid.setParameter('Capacity', str(self.getCapacity() ))
        messageBid.setParameter('CreationPeriod', str(self.getCreationPeriod() ))
        if (self._parent != None):
            messageBid.setParameter('ParentBid', self._parent.getId())
        else:
            messageBid.setParameter('ParentBid', ' ')
        for decisionVariable in self._decision_variables:
            messageBid.setParameter(decisionVariable, str(self._decision_variables[decisionVariable]))
        return messageBid
    
	'''
	Sets the general information
	'''
    def setFromMessage(self, service, message):
        	self.setValues(message.getParameter("Id"), message.getParameter("Provider"), message.getParameter("Service"))
        	status = message.getParameter("Status")
        	if (status == "inactive"):
        	    self._status = Bid.INACTIVE
        	else:
        	    self._status = Bid.ACTIVE
	
        	# Sets the decision variables
        	for decision_variable in service._decision_variables:
        	    value = float(message.getParameter(decision_variable))
        	    self.setDecisionVariable(decision_variable, value)

    ''' 
    This methods establish if the offer pass as parameter has the
    same decision variables.
    '''
    def isEqual(self, bidtoCompare):
        equal = True
        for decisionVariable in self._decision_variables:
            if ( self._decision_variables[decisionVariable] == bidtoCompare.getDecisionVariable(decisionVariable)):
                pass
            else:
                equal = False
                break
        return equal

	'''
	This method inserts the bid as parameter as a parent of this bid.
	'''
    def insertParentBid(self, bid):
        self._parent = bid

    '''
    This method establishes the provider bid (object).
    '''
    def setProviderBid(self, providerBid):
        self._providerBid = providerBid

    '''
    This method establishes the capacity for this bid (object).
    '''
    def setCapacity(self, capacity):            
        self._capacity = capacity
    
    def getCapacity(self):
        return self._capacity
    
    def getParentBid(self):
        return self._parent
    
    '''
    This method returns the associated bid of the provider that helps to create this bid.
    '''
    def getProviderBid(self):
        return self._providerBid
        
    '''
    This method establihes a quality requirement for the bid.
    '''
    def setQualityRequirement(self, decisionVariable, value):
        	if decisionVariable in self._qualityRequirements:
        	    raise FoundationException("Decision variable is already included")
        	else:   
        	    self._qualityRequirements[decisionVariable] = value

    '''
    This method returns the decision variable.
    '''
    def getQualityRequirement(self, decisionVariableId):
        #logging.debug('stating getDecisionVariable - Parameters:' + decisionVariableId)        
        if decisionVariableId in self._qualityRequirements:
            return self._qualityRequirements[decisionVariableId]
        else:
            if decisionVariableId in self._decision_variables:
                return self._decision_variables[decisionVariableId]
            else:
                raise FoundationException("The Decision variable is not part of the offer")

    def removeQualityRequirements(self):
        (self._qualityRequirements).clear()
        	
    ''' 
    This method gets the number of predecessor that a bid has
    '''
    def getNumberPredecessor(self):
        return self._numAncestors
    
    '''
    This method increment by one the number of predecessor
    '''
    def incrementPredecessor(self):
        self._numAncestors = self._numAncestors + 1
    
    '''
    This method establishes the number of predecessor
    '''
    def setNumberPredecessor(self, numPredecessor):
        self._numAncestors = numPredecessor
    