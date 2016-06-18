# -*- coding: utf-8 -*-
"""
Created on Tue Jun 14 10:47:21 2016

Name: NonApplicableCost 
Purpose: Implements a non applicable cost function.

@author: luis
"""

#-----------------------------------------------------------------------
# Name:        	Non Applicable cost function
# Purpose:		Cost function for decision variables not related to costs.
#-----------------------------------------------------------------------

from CostFunction import CostFunction


'''
This class implements the non aplicable cost function, this function should be used
on decision variables that are not related to costs.
'''
class NonApplicableCost(CostFunction):

    def __init__(self):
        super(NonApplicableCost, self).__init__('NonApplicableCost')

    def getParameters(self):
        	dic_return = { }
        	return dic_return
    
    '''
	Generates an evaluation of the function based on the variable value.
	'''		
    def getEvaluation(self, variableValue):
        # Verifies existance of all parameters.
        return 0
