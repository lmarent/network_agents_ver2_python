from probabilities.ProbabilityDistributionFactory import ProbabilityDistributionFactory
from probabilities.ProbabilityDistributionException import ProbabilityDistributionException
import FoundationException
import xml.dom.minidom
import logging

class QualityParameter(object):
    '''
    This class defines the methods required for the quality parameters.
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
	self._type = QualityParameter.MODEL_UNDEFINED
	self._optimization_objective = QualityParameter.OPT_UNDEFINED
	self._prob_distributions = {}
	self._sample = {}
	
    def setId(self, id):
	'''
	This method sets the quality parameter Id.
	'''
	self._id = id
	
    def getId(self):
	'''
	This method gets the quality parameter Id.
	'''
	return self._id
	
    def setOptimizationObjective(self, optimization_objetive):
	'''
	This method set the quality parameter optimization objective:
	maximize or minimize quality.
	'''
	if (optimization_objetive == "maximize"):
           self._optimization_objective = QualityParameter.OPT_MAXIMIZE
	elif (optimization_objetive == "minimize"):
           self._optimization_objective = QualityParameter.OPT_MINIMIZE	
    
    def getOptimizationObjective(self):
	'''
	This method gets the quality parameter optimization objective.
	'''
	return self._optimization_objective
	
    def setModeling(self, modeling):
	'''
	This method sets the quality parameter modeling. It can model 
	price or quality.
	'''
	if (modeling == "price"):
	    self._type = MODEL_PRICE
	elif (modeling == "quality"):
	    self._type = MODEL_QUALITY
    
    def getModeling(self):
	'''
	This method gets the quality parameter model from previous 
	method.
	'''
	return self._type
    
    def setProbabilityDistribution(self, probability_distribution, parameters):
	'''
	This method sets the quality parameter a probability distribution.
	'''
	factory = ProbabilityDistributionFactory.getInstance()
	self._value['Probability_Distribution'] = factory.create(probability_distribution)
		
    def executeSample(self):
	'''
	This method executes the quality parameter sample.
	<couldn't get what this method is for>
	'''
	msg = 'Starting QualityParamter - executeSample'
	logging.debug(msg)
	self._sample.clear()
	for purpose in self._prob_distributions:
	    self._sample[purpose] = (self._prob_distributions[purpose]).getSample()
	    msg = 'QualityParameter - GetSample' + prob + str(self._sample[purpose])
	    logging.debug(msg)
	msg = 'Ending QualityParamter - executeSample'
	logging.debug(msg)

    def getSample(self, purpose):
	'''
	This method gets the quality parameter purpose.
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
	This method handles the probabilities distributions according 
	to the purpose of the quality parameter.
	'''
	factory = ProbabilityDistributionFactory.Instance()
	for pDistribution in pdistristributions:
	    IdElement = pDistribution.getElementsByTagName("Purpose")[0]
	    purpose = self.getText(IdElement.childNodes)
	    msg = 'QualityParameter - Probability purpose:' + purpose
	    logging.debug(msg)
	    classNameElement = pDistribution.getElementsByTagName("Class_Name")[0]
	    className = self.getText(classNameElement.childNodes)
	    msg = 'QualityParameter - probability className:' + className
	    logging.debug(msg)
	    valProbDistrElements = pDistribution.getElementsByTagName("Probability_Distribution")
	    for probDistrXml in valProbDistrElements:
		probDist = factory.create(className)
		probDist.setFromXmlNode(probDistrXml)
		self._prob_distributions[purpose] = probDist
		break

    def setFromXmlNode(self, qualityParameterXmlNode):
	'''
	This method converts the object from XML to string.
	'''
	try:
	    logging.debug('QualityParameter - Start  setFromXmlNode')
	    # Sets the Id of the parameter
	    IdElement = qualityParameterXmlNode.getElementsByTagName("Id")[0]
	    Id = self.getText(IdElement.childNodes)
	    self._id = Id
	    logging.debug('QualityParameter - setFromXmlNode id:' + Id)

	    # Sets the objectives pursued by the parameter
	    objetiveElement = qualityParameterXmlNode.getElementsByTagName("Objective")[0]
	    objetive = self.getText(objetiveElement.childNodes)
	    self.setOptimizationObjective(objetive)
	    logging.debug('QualityParameter - setFromXmlNode objetive:' + objetive)

	    # Sets the type of decision variable
	    modelingElement = qualityParameterXmlNode.getElementsByTagName("Modeling")[0]
	    modeling = self.getText(modelingElement.childNodes)
	    self.setModeling(modeling)
	    logging.debug('QualityParameter - setFromXmlNode modeling:' + modeling)	    
	    
	    # Sets probability distributions of the parameter
	    valProbDistrElement = qualityParameterXmlNode.getElementsByTagName("Pr_Distributions")
	    self.handlePDistributions(valProbDistrElement)
	    
	    
	except ProbabilityDistributionException as e:
	    raise FoundationException(e.__str__())
	except Exception as e:
	    raise FoundationException("Invalid Quality Parameter Xml")

    def __str__(self):
	val_return = "Id:" + self._id + "Objetive:" + str(self._optimization_objective)
	return val_return
