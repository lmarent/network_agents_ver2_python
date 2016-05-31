from probabilities.ProbabilityDistributionFactory import ProbabilityDistributionFactory
from probabilities.ProbabilityDistributionException import ProbabilityDistributionException
import FoundationException
import xml.dom.minidom
import logging
import inspect
import os

class DecisionVariable(object):
    '''
    
    '''
    
    OPT_MAXIMIZE = 1
    OPT_MINIMIZE = 2
    OPT_UNDEFINED = 3
    
    PDST_VALUE = 1
    PDST_SENSITIVITY = 2
    
    MODEL_PRICE = 1
    MODEL_QUALITY = 2
    MODEL_UNDEFINED = 3
    
    def __init__(self):
	self._id = ''
	self._name = ''
	self._type = DecisionVariable.MODEL_UNDEFINED
	self._optimization_objective = DecisionVariable.OPT_UNDEFINED
	self._prob_distributions = {}
	self._sample = {}
	self._min_value = 0
	self._max_value = 0
	self._resource = ''
	
    def setId(self, id):
	'''
	This method set the decision variable Id.
	'''
	self._id = id
	
    def getId(self):
	'''
	This method returns the decision variable Id.
	'''
	return self._id
    
    def setName(self, name):
	self._name = name
    
    def getName(self):
	return self._name
    
    def setOptimizationObjective(self, optimization_objetive):
	'''
	This method sets the decision variable optimization objective.
	Its options include maximaze or minimize the decision variable.
	'''
	if (optimization_objetive == "maximize"):
           self._optimization_objective = DecisionVariable.OPT_MAXIMIZE
	elif (optimization_objetive == "minimize"):
           self._optimization_objective = DecisionVariable.OPT_MINIMIZE	
    
    def getOptimizationObjective(self):
	'''
	This method returns the decision variable optimization 
	objective.
	'''
	return self._optimization_objective
	
    def setModeling(self, modeling):
	'''
	This method sets the decision variable modeling, between
	price and quality.
	'''
	if (modeling == "price"):
	    self._type = DecisionVariable.MODEL_PRICE
	elif (modeling == "quality"):
	    self._type = DecisionVariable.MODEL_QUALITY
    
    def setPurpose(self,purpose):
	'''
	This method set the decision variable purpose. The avaiable 
	purposes are value and sensitivity.
	'''
	if (purpose == "value"):
	    return DecisionVariable.PDST_VALUE
	elif (purpose == "sensitivity"):
	    return DecisionVariable.PDST_SENSITIVITY
    

    def getModeling(self):
	'''
	This method returns the decision variable modeling type.
	'''
	return self._type
    
    def getMinValue(self):
	'''
	This method returns the decision variable minimum value.
	'''
	return self._min_value

    def getMaxValue(self):
	'''
	This method returns the decision variable maximum value.
	'''
	return self._max_value
    
    def getResource(self):
	'''
	This method returns the resource used by the decision variable.
	'''
	return self._resource
    
    def setProbabilityDistribution(self, probability_distribution, parameters):
	'''
	This method sets the decision variable probability distribution,
	getting the instance from the factory class.
	'''
	factory = ProbabilityDistributionFactory.Instance()
	self._value['Probability_Distribution'] = factory.create(probability_distribution)
		
    def executeSample(self, randomGenerator):
	'''
	
	'''
	msg = 'Starting DecisionVariable - executeSample'
	logging.debug(msg)
	self._sample.clear()
	for purpose in self._prob_distributions:
	    self._sample[purpose] = (self._prob_distributions[purpose]).getSample(randomGenerator)
	    msg = 'DecisionVariable - GetSample' + 'Purpose:' + str(purpose) + 'Value:' + str(self._sample[purpose])
	    logging.debug(msg)
	msg = 'Ending DecisionVariable - executeSample'
	logging.debug(msg)

    def getSample(self, purpose):
	'''
	This method returns the decision variable purpose.
	'''
	return self._sample[purpose]

    def getText(self, nodelist):
	'''
	This method transforms the object into XML.
	'''
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
	        rc.append(node.data)
	return ''.join(rc)

    def handlePDistributions(self, pdistristributions):
	'''
	This method handles probabilities distributions of decision
	variables.
	'''
	factory = ProbabilityDistributionFactory.Instance()
	logging.debug('DecisionVariable - After factory creation')
	for pDistribution in pdistristributions:
	    IdElement = pDistribution.getElementsByTagName("Purpose")[0]
	    purposeStr = self.getText(IdElement.childNodes)
	    msg = 'DecisionVariable - Probability purpose:' + purposeStr
	    purpose = self.setPurpose(purposeStr)
	    logging.debug(msg)
	    
	    classNameElement = pDistribution.getElementsByTagName("Class_Name")[0]
	    className = self.getText(classNameElement.childNodes)
	    msg = 'DecisionVariable - probability className:' + className
	    logging.debug(msg)
	    valProbDistrElements = pDistribution.getElementsByTagName("Probability_Distribution")
	    for probDistrXml in valProbDistrElements:
		probDist = factory.create(className)
		probDist.setFromXmlNode(probDistrXml)
		self._prob_distributions[purpose] = probDist
		break
	logging.debug('DecisionVariable - End  handlePDistributions')

    def setFromXmlNode(self, decisionVariableXmlNode):
	'''
	This method sets the decision variable parameters from XML.
	'''
	try:
	    logging.debug('DecisionVariable - Start  setFromXmlNode')
	    # Sets the Id of the parameter
	    IdElement = decisionVariableXmlNode.getElementsByTagName("Id")[0]
	    Id = self.getText(IdElement.childNodes)
	    self._id = Id
	    logging.debug('DecisionVariable - setFromXmlNode id:' + Id)

	    # Sets the objectives pursued by the parameter
	    nameElement = decisionVariableXmlNode.getElementsByTagName("Name")[0]
	    name = self.getText(nameElement.childNodes)
	    self.setName(name)
	    logging.debug('DecisionVariable - setFromXmlNode name:' + name)

	    # Sets the objectives pursued by the parameter
	    objetiveElement = decisionVariableXmlNode.getElementsByTagName("Objective")[0]
	    objetive = self.getText(objetiveElement.childNodes)
	    self.setOptimizationObjective(objetive)
	    logging.debug('DecisionVariable - setFromXmlNode objetive:' + objetive)

	    # Sets the type of decision variable
	    modelingElement = decisionVariableXmlNode.getElementsByTagName("Modeling")[0]
	    modeling = self.getText(modelingElement.childNodes)
	    self.setModeling(modeling)
	    logging.debug('DecisionVariable - setFromXmlNode modeling:' + modeling)	    

	    # Sets the type of decision variable
	    minValueElement = decisionVariableXmlNode.getElementsByTagName("Min_Value")[0]
	    minValue = float(self.getText(minValueElement.childNodes))
	    self._min_value = minValue
	    logging.debug('DecisionVariable - setFromXmlNode minValue:' + str(minValue))

	    # Sets the type of decision variable
	    maxValueElement = decisionVariableXmlNode.getElementsByTagName("Max_Value")[0]
	    maxValue = float(self.getText(maxValueElement.childNodes))
	    self._max_value = maxValue
	    logging.debug('DecisionVariable - setFromXmlNode maxValue:' + str(maxValue))
	    
	    #Set the resource that uses the decision variable
	    resourceElement = decisionVariableXmlNode.getElementsByTagName("Resource")[0]
	    self._resource =  self.getText(resourceElement.childNodes)
	    logging.debug('DecisionVariable - setFromXmlNode resource:' + self._resource)
	    
	    # Sets probability distributions of the parameter
	    valProbDistrElement = decisionVariableXmlNode.getElementsByTagName("Pr_Distributions")
	    self.handlePDistributions(valProbDistrElement)
	    logging.debug('DecisionVariable - setFromXmlNode After handleDistribution:')
	    
	except ProbabilityDistributionException as e:
	    raise FoundationException(e.__str__())
	except Exception as e:
	    raise FoundationException("Invalid Decision Variable Xml")

    def __str__(self):
	val_return = 'Id:' + self._id + 'Name:' + self._name + '\n'
	val_return = val_return + 'Objetive:' + str(self._optimization_objective) + '\n'
	val_return = val_return + 'Modeling:' + str(self._type) + '\n'
	val_return = val_return + 'Min_Value:' + str(self._min_value) + 'Max value:' + str(self._max_value) + '\n'
	for prob in self._prob_distributions:
	    val_return = val_return + (self._prob_distributions[prob]).__str__()	
	return val_return
