from django.contrib import admin
from django.forms import ModelForm
from django import forms
from django.forms.models import inlineformset_factory
from simulation.models import Service
from simulation.models import Resource
from simulation.models import DecisionVariable
from simulation.models import Unit
from simulation.models import ProbabilityDistribution
from simulation.models import DiscreteProbabilityDistribution
from simulation.models import ContinuousProbabilityDistribution
from simulation.models import Service_DecisionVariable
from simulation.models import Provider
from simulation.models import Provider_Resource
from simulation.models import Graphic
from simulation.models import Axis_Graphic
from simulation.models import Presenter
from simulation.models import Presenter_Graphic
from simulation.models import offeringData
from simulation.models import Consumer
from simulation.models import ConsumerService
from simulation.models import ExecutionGroup
from simulation.models import ExecutionConfiguration
from simulation.models import ExecutionConfigurationProviders
from simulation.models import GeneralParameters


import importlib


import inspect
import os
import re
import sys


# Register your models here.
class DecisionVariableInline(admin.TabularInline):
    model = Service_DecisionVariable
    extra = 0

admin.site.register(Unit)
admin.site.register(Resource)
admin.site.register(DecisionVariable)

class DiscreteProbabilityDistributionInLine(admin.TabularInline):
    model = DiscreteProbabilityDistribution
    extra = 0

class ContinuousProbabilityDistributionInLine(admin.TabularInline):
    model = ContinuousProbabilityDistribution
    extra = 0

class offeringDataForm(ModelForm):
    class Meta:
	model = offeringData
	fields = ['name', 'type', 'decision_variable', 'function']

    def formfield_for_choice_field(self, available_choices):
        currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	dir_path = file_path.split('/')
	dir_path.pop()		# remove ./simulation from the list
	dir_path.pop()		# remove ./simulation_site from the list
	agents_directory = '/'.join(dir_path)
	agents_directory += '/agents/'
	sys.path.append(agents_directory)
	presenterModule = importlib.import_module('Presenter')
	methods = inspect.getmembers(presenterModule.Presenter, predicate=inspect.ismethod)
	print methods
	for pair in methods:
	    if 'get' in pair[0]:
		available_choices.append((pair[0], pair[0]))

    
    def __init__(self, *args, **kwargs):
        super(offeringDataForm, self).__init__(*args, **kwargs)
	available_choices = []
        self.formfield_for_choice_field(available_choices)
        self.fields['function'] = forms.ChoiceField(choices=available_choices)
	
class offeringDataAdmin(admin.ModelAdmin):
    form = offeringDataForm


admin.site.register(offeringData, offeringDataAdmin)

class ServiceAdmin(admin.ModelAdmin):
    fieldsets = [
        ('General Information', {'fields': ['name']}),
	('Demand Informantion', {'fields':['file_name_demand','converter_origin', 'file_name_converter']}),
    ]
    inlines = [DecisionVariableInline]
admin.site.register(Service, ServiceAdmin)

class ProbabilityForm(ModelForm):
    class Meta:
        model = ProbabilityDistribution
	fields = ['name', 'domain', 'class_name']
    
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
        super(ProbabilityForm, self).__init__(*args, **kwargs)
	available_choices = []
        self.formfield_for_choice_field(available_choices)
	print available_choices
        self.fields['class_name'] = forms.ChoiceField(choices=available_choices)

class ProbabilityAdmin(admin.ModelAdmin):
    form = ProbabilityForm
    inlines = [DiscreteProbabilityDistributionInLine, 
	       ContinuousProbabilityDistributionInLine ]
    
admin.site.register(ProbabilityDistribution, ProbabilityAdmin)

class ProviderResourceInline(admin.TabularInline):
    model = Provider_Resource
    extra = 0


class ProviderForm(ModelForm):
    class Meta:
        model = Provider
	fields = ['name', 'service', 'market_position', 'adaptation_factor', 
		  'status', 'monopolist_position', 'num_ancestors', 'start_from_period',
		  'debug', 'class_name', 'seed', 'year', 'month', 'day', 'hour', 
		  'minute', 'second', 'microsecond', 'buying_marketplace_address',
		  'selling_marketplace_address', 'capacity_controlled_at' ]
    
    def formfield_for_choice_field(self, available_choices):
        currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	sys.path.append(currentdir)
	file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	dir_path = file_path.split('/')
	dir_path.pop()		# remove ./simulation from the list
	dir_path.pop()		# remove ./simulation_site from the list
	probability_directory = '/'.join(dir_path)
	probability_directory += '/agents'
	
	black_list = ['ProviderExecution', 'ProviderAgentException']
		
	for filename in os.listdir (probability_directory):
	    # Ignore subfolders
            if os.path.isdir (os.path.join(probability_directory, filename)):
                continue
            else:
                if re.match(r"Provider.*?\.py$", filename):
                    classname = re.sub(r".py", r"", filename)
		    if (classname not in black_list):
			available_choices.append((classname, classname))

    def __init__(self, *args, **kwargs):
        super(ProviderForm, self).__init__(*args, **kwargs)
	available_choices = []
        self.formfield_for_choice_field(available_choices)
        self.fields['class_name'] = forms.ChoiceField(choices=available_choices)


class ProviderAdmin(admin.ModelAdmin):
    form = ProviderForm
    inlines = [ProviderResourceInline]
admin.site.register(Provider, ProviderAdmin)

class PresenterGraphicInLine(admin.TabularInline):
    model = Presenter_Graphic
    extra = 0

class PresenterAdmin(admin.ModelAdmin):
    fieldsets = [
        ('General Information', {'fields': ['name']}),
    ]
    inlines = [PresenterGraphicInLine]
admin.site.register(Presenter, PresenterAdmin)

class AxisGraphicInLine(admin.TabularInline):
    model = Axis_Graphic
    extra = 0

class GraphicAdmin(admin.ModelAdmin):
    fieldsets = [
        ('General Information', {'fields': ['name','description']}),
    ]
    inlines = [AxisGraphicInLine]
admin.site.register(Graphic, GraphicAdmin)


class ConsumerServiceinLineAdmin(admin.TabularInline):
    model = ConsumerService
    extra = 0

class ConsumerAdmin(admin.ModelAdmin):
    fieldsets = [
        ('General Information', {'fields': ['number_execute','observartions',
					    'seed', 'year', 'month',
					    'day', 'hour', 'minute', 'second',
					    'microsecond'
					   ]
				}
	),
    ]
    inlines = [ConsumerServiceinLineAdmin]

admin.site.register(Consumer, ConsumerAdmin)

class ExecutionGroupAdmin(admin.ModelAdmin):
    fieldsets = [
        ('General Information', {'fields': ['name','description','status']}),
    ] 

admin.site.register(ExecutionGroup, ExecutionGroupAdmin)


class ExecutionConfigurationinLineAdmin(admin.TabularInline):
    model = ExecutionConfigurationProviders
    extra  = 0

class ExecutionConfigurationAdmin(admin.ModelAdmin):
    fieldsets = [
	('General Information', {'fields': ['description', 'status', 'execution_group', 'number_consumers', 'number_periods']} 
	),
    ]
    inlines = [ExecutionConfigurationinLineAdmin]

admin.site.register(ExecutionConfiguration, ExecutionConfigurationAdmin)

class GeneralParametersAdmin(admin.ModelAdmin):
    fieldsets = [
        ('General Information', {'fields': ['bid_periods',
					    'pareto_fronts_to_exchange',
					    'initial_offer_number',
					    'num_periods_market_share'
					    ]}),
    ] 

admin.site.register(GeneralParameters, GeneralParametersAdmin)    
    
