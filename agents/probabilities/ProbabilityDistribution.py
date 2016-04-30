import logging

class ProbabilityDistribution(object):
    '''
    This is a abstract class for probability distribution
    '''
    
    DOM_CONTINOUS = 1
    DOM_DISCRETE = 2
    DOM_UNDEFINED = 3

    
    def __init__(self):
	self._name = ''
	self._domain = ProbabilityDistribution.DOM_UNDEFINED
	self._paramerters = {}
	self._points ={}
    
    # abstract method
    def getSample(self, randomGenerator):
	'''
	Abstract method to getSample().
	'''
	return
    
    def getParameters(self):
	'''
	Abstract method to getParameters().
	'''
	return 
    
    def getName(self):
	'''
	Abstract method to getName().
	'''
	return

    def getText(self, nodelist):
	'''
	This method gets the text from the node list.
	'''
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
	        rc.append(node.data)
	return ''.join(rc)
    
    def domainFromStr(self, domain):
	'''
	This method gets the domain from a string and set the function
	ProbabilityDistribution.
	'''
	if (domain == "continuous"):
	    return ProbabilityDistribution.DOM_CONTINOUS
	elif (domain == "discrete"):
	    return ProbabilityDistribution.DOM_DISCRETE
	else:
	    return ProbabilityDistribution.DOM_UNDEFINED
    
    def handlePoints(self, points):
	'''
	This method adds a message to the debug log with the points value
	and probability.
	'''
	for point in points:
	    valueElement = point.getElementsByTagName("Value")[0]
	    value = float(self.getText(valueElement.childNodes))
	    probabilityElement = point.getElementsByTagName("Probability")[0]
	    probability = float(self.getText(probabilityElement.childNodes))
	    self._points[value] = probability
	    msg = 'ProbabilityDistribution - point value:' + str(value) + " probability:" + str(probability)
	    logging.debug(msg) 
    
    def handleParameters(self, parameters):
	'''
	This method adds a message to the debug log with parameter name
	and value.
	'''
	for parameter in parameters:
	    nameElement = point.getElementsByTagName("Name")[0]
	    name = self.getText(nameElement.childNodes)
	    valueElement = point.getElementsByTagName("Value")[0]
	    value = float(self.getText(valueElement.childNodes))
	    self._parameters[name] = value
	    msg = 'ProbabilityDistribution - parameter name:' + name + " Value:" + str(value)
	    logging.debug(msg)	    
    
    def setFromXmlNode(self, probabilityDistributionXmlNode):
	'''
	This method convets a message from XML to string.
	'''
	nameElement = probabilityDistributionXmlNode.getElementsByTagName("Name")[0]
	name = self.getText(nameElement.childNodes)
	self._name = name
	msg = 'ProbabilityDistribution - setFromXmlNode name:' + name
	logging.debug(msg) 
	
	domainElement = probabilityDistributionXmlNode.getElementsByTagName("Domain")[0]
	domain = self.getText(domainElement.childNodes)
	self._domain = self.domainFromStr(domain)
	msg = 'ProbabilityDistribution - setFromXmlNode domain:' + domain
	logging.debug(msg) 
	
	points = probabilityDistributionXmlNode.getElementsByTagName("Point")
	self.handlePoints(points)
	
	parameters = probabilityDistributionXmlNode.getElementsByTagName("Parameter")
	self.handleParameters(parameters)
    
    def __str__(self):
	val_return = 'Name:' + self._name + 'Domain:' + str(self._domain) + '\n'
	for parameter in self._paramerters:
	    val_return = val_return + 'Parameter:' + parameter + 'Value:' + str(self._paramerters[parameter]) + '\n'
	for point in self._points:
	    val_return = val_return + 'Point:' + str(point) + 'Probability:' + str(self._points[point]) + '\n'
	return val_return
