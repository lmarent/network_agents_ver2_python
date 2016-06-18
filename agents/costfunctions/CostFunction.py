import logging

class CostFunction(object):
    '''
    This is a abstract class for cost function in terms of usage of a resource. 
    
    The domain of this functions should be 0-1, which means:
        
        0 - min quality 
        1 - max quality
    
    The range should be [0, + infty)
    
    In case of 0, the system puts the minimal resource usage defined in the resource. 
    For other values the final cost will be: 
        
        unitaryCost = 1 + getEvaluation(variables))
    
    '''    
    
    RANGE_CONTINOUS = 1
    RANGE_DISCRETE = 2
    RANGE_UNDEFINED = 3

    
    def __init__(self, name):
        self._name = name
        self._range = CostFunction.RANGE_UNDEFINED
        self._parameters = {}
    
    # abstract method
	'''
	Abstract method to getSample().
	'''
    def getEvaluation(self, variables):
        return
    
	'''
	Abstract method to getParameters().
	'''
    def getParameters(self):
        return 
    
    def getName(self):
        return self._name

    '''
    Abstract method to setParameters.
    '''
    def setParameter(self, name, value):
        return 

	'''
	This method gets the text from the node list.
	'''
    def getText(self, nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)
    
	'''
	This method gets the range from a string and set it.
	'''
    def rangeFromStr(self, costRange):
        	if (costRange == "continuous"):
        	    return CostFunction.RANGE_CONTINOUS
        	elif (costRange == "discrete"):
        	    return CostFunction.RANGE_DISCRETE
        	else:
        	    return CostFunction.RANGE_UNDEFINED
    
    '''
	This method adds a message to the debug log with parameter name
	and value.
	'''
    def handleParameters(self, parameters):
        for parameter in parameters:
            nameDefined = False
            valueDefined = False
            
            # Read the name
            nameElements = parameter.getElementsByTagName("Name")
            for nameElement in nameElements:
                name = self.getText(nameElement.childNodes)
                nameDefined = True
                break
            
            # Read the value of the parameter            
            valueElements = parameter.getElementsByTagName("Value")
            for valueElement in valueElements:
                value = float(self.getText(valueElement.childNodes))
                valueDefined = True
                break
            
            if (nameDefined == True) and (valueDefined == True):
                self._parameters[name] = value
                msg = 'CostFunction - parameter name:' + name + " Value:" + str(value)
                logging.debug(msg)	    

    
    def setFromXmlNode(self, xmlNode):
        '''
        This method convets a message from XML to string.
        '''
        nameElement = xmlNode.getElementsByTagName("Name")[0]
        name = self.getText(nameElement.childNodes)
        self._name = name
        msg = 'CostFunction - setFromXmlNode name:' + name
        logging.debug(msg)
        
        domainElement = xmlNode.getElementsByTagName("Range")[0]
        costRange = self.getText(domainElement.childNodes)
        self._range = self.rangeFromStr(costRange)
        msg = 'CostFunction - setFromXmlNode range:' + costRange
        logging.debug(msg) 
        
        parameters = xmlNode.getElementsByTagName("Parameter")
        self.handleParameters(parameters)
    
    def __str__(self):
        	val_return = 'Name:' + self._name + 'Range:' + str(self._range) + '\n'
        	for parameter in self._parameters:
        	    val_return = val_return + 'Parameter:' + parameter + 'Value:' + str(self._parameters[parameter]) + '\n'
        	return val_return
