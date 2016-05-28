import xml.dom.minidom
import logging
from DecisionVariable import DecisionVariable
from FoundationException import FoundationException

class Service(object):
    '''
    This class defines the methods required for the creation of services,
    such as set and get service Id, add and get decision variables, 
    set and get service name.
    '''
	
    def __init__(self):
	self._id = ''
	self._name = ''
	self._decision_variables = {}
	
    def setId(self, Id):
	'''
	This method set the service Id.
	'''
	self._id = Id
		
    def getId(self):
	'''
	This method returns the service Id.
	'''
	return self._id
	
    def addDecisionVariable(self, decision_param):
	'''
	This method adds a decision variable to the service.
	'''
	if decision_param.getId() in self._decision_variables:
	    raise FoundationException("Decision variable is already included")
	else:   
	    self._decision_variables[decision_param.getId()] = decision_param	
	
    def getDecisionVariable(self, Id): 
	'''
	This method gets a decision variable from the service.
	'''
	if Id in self._decision_variables:			
	    return self._decision_variables[Id]
	else:
	    raise FoundationException("The Decision variable is not part of the service")
	
    def setName(self, setName):
	'''
	This method sets the service name.
	'''
	self._name = name
		
    def getName(self):
	'''
	This method gets the service name.
	'''
	return self._name
	
    def getText(self,nodelist):
	'''
	This method transform the object into XML
	'''
	logging.debug('Start getText')
	rc = []
	for node in nodelist:
	    if node.nodeType == node.TEXT_NODE:
		rc.append(node.data)
	return ''.join(rc)

    def getPriceDecisionVariable(self):
	for decisionVariable in self._decision_variables:
	    decisionVar = self._decision_variables[decisionVariable]
	    if (decisionVar.getModeling() == DecisionVariable.MODEL_PRICE):
		return decisionVariable
	return None
	
    def getDecisionVariableObjetive(self, decisionVariableId):
        optimum = 0 # undefined.
        for decisionVariable in self._decision_variables:
            if (decisionVariable == decisionVariableId):
                if (self._decision_variables[decisionVariable].getOptimizationObjective() == DecisionVariable.OPT_MAXIMIZE):
                    optimum = 1 # Maximize
                else:
                    optimum = 2 # Minimize       
        return optimum
 
    def setFromXmlNode(self, serviceXmlNode):
	'''
	This method converts the object from XML to string.
	'''
	logging.debug('Service - Start setFromXmlNode')
	# Sets the Id of the service
	IdElement = serviceXmlNode.getElementsByTagName("Id")[0]
	Id = self.getText(IdElement.childNodes)
	self._id = Id
	logging.debug('Service - setFromXmlNode id:' + Id)
	# Sets the name of the service
	nameElement = serviceXmlNode.getElementsByTagName("Name")[0]
	name = self.getText(nameElement.childNodes)
	self._name = name
	logging.debug('Service - setFromXmlNode Name:' + name)
	# Sets the Decision variables of the service
	variableXmlNodes = serviceXmlNode.getElementsByTagName("Decision_Variable")
	for variableXmlNode in variableXmlNodes:
	    variable = DecisionVariable()
	    logging.debug('Decision variable created')
	    variable.setFromXmlNode(variableXmlNode)
	    logging.debug('Decision variable set xml executed')
	    self._decision_variables[variable.getId()] = variable
	logging.debug('Finish Decision variables')

    def __str__(self):
	val_return = "Id" + self._id + " Name:" + self._name 
	for variable in self._decision_variables:
	    val_return = val_return + (self._decision_variables[variable]).__str__()
	return val_return
