import os
import sys
import re
import importlib
from CostFunction import CostFunction
import logging
import inspect

import sys
sys.path.append(os.path.realpath('..'))
from foundation.FoundationException import FoundationException


class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)

@Singleton
class CostFunctionFactory(object):  
    
    def __init__(self):
	self._list_classes = {}
	currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	sys.path.append(currentdir)
	costfunction_directory = currentdir
	for filename in os.listdir (costfunction_directory):
            # Ignore subfolders
            if os.path.isdir (os.path.join(costfunction_directory, filename)):
                continue
            else:
                if re.match(r".*?\.py$", filename):
                    logging.debug('Initialising cost function class:'  + filename)
                    classname = re.sub(r".py", r"", filename)
		    module = __import__(classname)
		    targetClass = getattr(module, classname)
		    self._list_classes[classname] = targetClass   
        logging.debug('Cost function initialized')

		
    def create(self, typ):
	if typ in self._list_classes:
	     targetClass = self._list_classes[typ]
	     return targetClass()
	else:
	     err = 'Class' + typ + 'not found to be loaded'
	     raise FoundationException(err)

#from CostFunctionFactory import CostFunctionFactory
#f = CostFunctionFactory.Instance() # Good. Being explicit is in line with the Python Zen
#g = CostFunctionFactory.Instance() # Returns already created instance

#print f is g # True
#linealFunction = g.create("LinealCost")
#linealFunction.getName()
