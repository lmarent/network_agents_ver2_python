from probabilities.ProbabilityDistributionFactory import ProbabilityDistributionFactory
from probabilities.ProbabilityDistributionException import ProbabilityDistributionException
from costfunctions.CostFunctionFactory import CostFunctionFactory

import FoundationException
import xml.dom.minidom
import logging
import inspect
import os

'''    
Decision variable class.
'''    
class DecisionVariable(object):
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
        self._cost_function = None
        self._sample = {}
        self._min_value = 0
        self._max_value = 0
        self._resource = ''
	
	'''
	This method set the decision variable Id.
	'''
    def setId(self, id):
        self._id = id
	
	'''
	This method returns the decision variable Id.
	'''
    def getId(self):
        return self._id
    
    def setName(self, name):
        self._name = name
    
    def getName(self):
        return self._name
    
	'''
	This method sets the decision variable optimization objective.
	Its options include maximaze or minimize the decision variable.
	'''
    def setOptimizationObjective(self, optimization_objetive):
        if (optimization_objetive == "maximize"):
            self._optimization_objective = DecisionVariable.OPT_MAXIMIZE
        elif (optimization_objetive == "minimize"):
            self._optimization_objective = DecisionVariable.OPT_MINIMIZE	
    
	'''
	This method returns the decision variable optimization 
	objective.
	'''
    def getOptimizationObjective(self):
        return self._optimization_objective
	
	'''
	This method sets the decision variable modeling, between
	price and quality.
	'''
    def setModeling(self, modeling):
        if (modeling == "price"):
            self._type = DecisionVariable.MODEL_PRICE
        elif (modeling == "quality"):
            self._type = DecisionVariable.MODEL_QUALITY
    
	'''
	This method set the decision variable purpose. The avaiable 
	purposes are value and sensitivity.
	'''
    def setPurpose(self,purpose):
        if (purpose == "value"):
            return DecisionVariable.PDST_VALUE
        elif (purpose == "sensitivity"):
            return DecisionVariable.PDST_SENSITIVITY
    

	'''
	This method returns the decision variable modeling type.
	'''
    def getModeling(self):
        return self._type
    
	'''
	This method returns the decision variable minimum value.
	'''
    def getMinValue(self):
        return self._min_value

	'''
	This method returns the decision variable maximum value.
	'''
    def getMaxValue(self):
        return self._max_value
    
	'''
	This method returns the resource used by the decision variable.
	'''
    def getResource(self):
        return self._resource
    
	'''
	This method sets the decision variable probability distribution,
	getting the instance from the factory class.
	'''
    def setProbabilityDistribution(self, probability_distribution, parameters):
        factory = ProbabilityDistributionFactory.Instance()
        self._value['Probability_Distribution'] = factory.create(probability_distribution)
	
    '''
    Get the cost function
    '''    
    def getCostFunction(self):
        return self._cost_function
	
	'''
    execute example method.	
	'''
    def executeSample(self, randomGenerator):
        msg = 'Starting DecisionVariable - executeSample'
        logging.debug(msg)
        self._sample.clear()
        for purpose in self._prob_distributions:
            self._sample[purpose] = (self._prob_distributions[purpose]).getSample(randomGenerator)
            msg = 'DecisionVariable - GetSample' + 'Purpose:' + str(purpose) + 'Value:' + str(self._sample[purpose])
            logging.debug(msg)
        msg = 'Ending DecisionVariable - executeSample'
        logging.debug(msg)

	'''
	This method returns the decision variable purpose.
	'''
    def getSample(self, purpose):
        return self._sample[purpose]

	'''
	This method transforms the object into XML.
	'''
    def getText(self, nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)

	'''
	This method handles probabilities distributions of decision
	variables.
	'''
    def handlePDistributions(self, pdistristributions):
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

	'''
	This method handles cost function of decision variables.
	'''
    def handleCostFunction(self, costFunctions):
        factory = CostFunctionFactory.Instance()
        logging.debug('DecisionVariable - After Cost Function factory creation')
        for costFunction in costFunctions:
            # Read the class name            
            classNameDefined = False
            classNameElements = costFunction.getElementsByTagName("Class_Name")
            for classNameElement in classNameElements:
                className = self.getText(classNameElement.childNodes)
                classNameDefined = True
                break
            
            # Read the rest of the attributes of the cost function.            
            if classNameDefined == True:
                msg = 'DecisionVariable - Cost Function className:' + className
                logging.debug(msg)
                costFunctionElements = costFunction.getElementsByTagName("Cost_Function")
                for costFunctionXml in costFunctionElements:
                    costFunc = factory.create(className)
                    costFunc.setFromXmlNode(costFunctionXml)
                    self._cost_function = costFunc
                    break
            # Stop processing because there is only one costFunction per decision variable.
            break
        logging.debug('DecisionVariable - End handleCostFunction')


	'''
	This method sets the decision variable parameters from XML.
	'''
    def setFromXmlNode(self, decisionVariableXmlNode):
        try:
            logging.debug('DecisionVariable - Start  setFromXmlNode')
            # Set the Id of the parameter
            IdElement = decisionVariableXmlNode.getElementsByTagName("Id")[0]
            Id = self.getText(IdElement.childNodes)
            self._id = Id
            logging.debug('DecisionVariable - setFromXmlNode id:' + Id)

            # Set the objectives pursued by the parameter
            nameElement = decisionVariableXmlNode.getElementsByTagName("Name")[0]
            name = self.getText(nameElement.childNodes)
            self.setName(name)
            logging.debug('DecisionVariable - setFromXmlNode name:' + name)

            # Set the objectives pursued by the parameter
            objetiveElement = decisionVariableXmlNode.getElementsByTagName("Objective")[0]
            objetive = self.getText(objetiveElement.childNodes)
            self.setOptimizationObjective(objetive)
            logging.debug('DecisionVariable - setFromXmlNode objetive:' + objetive)

            # Set the type of decision variable
            modelingElement = decisionVariableXmlNode.getElementsByTagName("Modeling")[0]
            modeling = self.getText(modelingElement.childNodes)
            self.setModeling(modeling)
            logging.debug('DecisionVariable - setFromXmlNode modeling:' + modeling)	    

            # Set the type of decision variable
            minValueElement = decisionVariableXmlNode.getElementsByTagName("Min_Value")[0]
            minValue = float(self.getText(minValueElement.childNodes))
            self._min_value = minValue
            logging.debug('DecisionVariable - setFromXmlNode minValue:' + str(minValue))

            # Set the type of decision variable
            maxValueElement = decisionVariableXmlNode.getElementsByTagName("Max_Value")[0]
            maxValue = float(self.getText(maxValueElement.childNodes))
            self._max_value = maxValue
            logging.debug('DecisionVariable - setFromXmlNode maxValue:' + str(maxValue))
	    
            # Set the resource that uses the decision variable
            resourceElement = decisionVariableXmlNode.getElementsByTagName("Resource")[0]
            self._resource =  self.getText(resourceElement.childNodes)
            logging.debug('DecisionVariable - setFromXmlNode resource:' + self._resource)
	    
            # Set probability distributions of the parameter
            valProbDistrElement = decisionVariableXmlNode.getElementsByTagName("Pr_Distributions")
            self.handlePDistributions(valProbDistrElement)
            logging.debug('DecisionVariable - setFromXmlNode After handleDistribution:')

            # Set cost function of the parameter
            cstFunctionElement = decisionVariableXmlNode.getElementsByTagName("Cst_Function")
            if (len(cstFunctionElement) > 0):
                self.handleCostFunction(cstFunctionElement)
                logging.debug('DecisionVariable - setFromXmlNode After handleCstFunction:')

	    
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
