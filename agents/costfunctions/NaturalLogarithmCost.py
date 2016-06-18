# -*- coding: utf-8 -*-
"""
Created on Tue Jun 14 10:47:21 2016

Name: LinealCost 
Purpose: Implements a lineal function.

@author: luis
"""

#-----------------------------------------------------------------------
# Name:        	Beta Probability Distribution
# Purpose:		Implement beta probability
#-----------------------------------------------------------------------

from CostFunction import CostFunction
from foundation.FoundationException import FoundationException
import math


'''
This class implements the Natural Logarithm cost function defined as:
    a*In(x+1) + b 

    Intercept with the y axis: b
    
    
'''
class NaturalLogarithmCost(CostFunction):

    def __init__(self):
        super(NaturalLogarithmCost, self).__init__('NaturalLogarithmCost')

    def getParameters(self):
        	dic_return = { 0 :'a', 1 : 'b' }
        	return dic_return

    '''
    This method sets a parameter for the function
    '''
    def setParameter(self, name, value):
        parameterNames = self.getParameters()
        for param in parameterNames:
            if ( name == parameterNames[param]):
                # if it already exists in the dictionary, then update the value.
                self._parameters[name] = value
    
    '''
	Generates an evaluation of the function based on the variable value.
	'''		
    def getEvaluation(self, variableValue):
        # Verifies existance of all parameters.
        parameters = self.getParameters()
        for parameter in parameters:
            name = parameters[parameter]
            if name not in self._parameters.keys():
                raise FoundationException('parameter for cost evaluation not found' + name)
        
        a = self._parameters['a']
        b = self._parameters['b']
        return (a*math.log(variableValue + 1)) + b
