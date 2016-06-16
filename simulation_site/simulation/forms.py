from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory
import inspect
import os
import re
import sys


from simulation.models import ProbabilityDistribution
from simulation.models import DiscreteProbabilityDistribution
from simulation.models import CostFunction
from simulation.models import ContinuousCostFunction


class ProbabilityDistributionForm(forms.ModelForm):

    class Meta:
        model = ProbabilityDistribution

    def formfield_for_choice_field(self, available_choices):
        currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        sys.path.append(currentdir)
        file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        dir_path = file_path.split('/')
        dir_path.pop()		# remove ./simulation from the list
        dir_path.pop()		# remove ./simulation_site from the list
        probability_directory = '/'.join(dir_path)
        probability_directory += '/agents/probabilities'
	
        black_list = ['__init__','ProbabilityDistribution',
                      'ProbabilityDistributionFactory', 
                      'ProbabilityDistributionException']
	
        for filename in os.listdir (probability_directory):
            # Ignore subfolders
            if os.path.isdir (os.path.join(probability_directory, filename)):
                continue
            else:
                if re.match(r".*?\.py$", filename):
                    classname = re.sub(r".py", r"", filename)
                    if (classname not in black_list):
                        available_choices.append((classname, classname))

    def __init__(self, *args, **kwargs):
		available_choices = []
		self.formfield_for_choice_field(available_choices)
		print available_choices
		#self.fields['class_name'].choices = available_choices
		return super(ProbabilityDistributionForm, self).__init__(*args, **kwargs)

# inlineformset_factory creates a Class from a parent model (Contact)
# to a child model (Address)
DiscreteProbabilityFormSet = inlineformset_factory(
    ProbabilityDistribution,
    DiscreteProbabilityDistribution,
)


class CostFunctionForm(forms.ModelForm):

    class Meta:
        model = CostFunction

    def formfield_for_choice_field(self, available_choices):
        currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        sys.path.append(currentdir)
        file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        dir_path = file_path.split('/')
        dir_path.pop()		# remove ./simulation from the list
        dir_path.pop()		# remove ./simulation_site from the list
        costfunction_directory = '/'.join(dir_path)
        costfunction_directory += '/agents/costfunction'
	
        black_list = ['__init__','CostFunction', 'CostFunctionFactory']
	
        for filename in os.listdir (costfunction_directory):
            # Ignore subfolders
            if os.path.isdir (os.path.join(costfunction_directory, filename)):
                continue
            else:
                if re.match(r".*?\.py$", filename):
                    classname = re.sub(r".py", r"", filename)
                    if (classname not in black_list):
                        available_choices.append((classname, classname))

    def __init__(self, *args, **kwargs):
		available_choices = []
		self.formfield_for_choice_field(available_choices)
		print available_choices
		#self.fields['class_name'].choices = available_choices
		return super(CostFunctionForm, self).__init__(*args, **kwargs)

# inlineformset_factory creates a Class from a parent model (Contact)
# to a child model (Address)
ConstinousCostFunctionFormSet = inlineformset_factory(
    CostFunction,
    ContinuousCostFunction,
)
