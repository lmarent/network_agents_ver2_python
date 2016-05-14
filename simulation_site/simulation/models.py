from django.db import models
from django.core.urlresolvers import reverse
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.
class Resource(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)

    def __unicode__(self):  # Python 3: def __str__(self):
        return self.name    

class ProbabilityDistribution(models.Model):
    CONTINOUS = 'C'
    DISCRETE = 'D'
    DOMAIN_CHOICES = ( 
	(CONTINOUS, 'Continous'),
        (DISCRETE, 'Discrete'),
    )

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)
    class_name = models.CharField(max_length=60)
    domain = models.CharField(max_length=2, choices=DOMAIN_CHOICES, default=CONTINOUS)
    
    def get_absolute_url(self):
        return reverse('probabilities-view', kwargs={'pk': self.id})
    
    def __str__(self):  # Python 3: def __str__(self):
        return self.name

class DiscreteProbabilityDistribution(models.Model):
    id = models.AutoField(primary_key=True)
    probability_id = models.ForeignKey('ProbabilityDistribution')
    value = models.FloatField(default=0)
    label = models.CharField(max_length=60, blank=True)
    probability = models.FloatField(default=0, 
				    validators=[MaxValueValidator(1),
						MinValueValidator(0)]) 

class ContinuousProbabilityDistribution(models.Model):
    id = models.AutoField(primary_key=True)
    probability_id = models.ForeignKey('ProbabilityDistribution')
    parameter = models.CharField(max_length=60)
    value = models.FloatField(default=0)

class Unit(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)
    symbol =models.CharField(max_length=3)
    
    def __unicode__(self):  # Python 3: def __str__(self):
        return self.name
    

class DecisionVariable(models.Model):
    MAXIMIZE = 'M'
    MINIMIZE = 'L'
    
    OPT_CHOICES = (
        (MAXIMIZE, 'Maximize'),
        (MINIMIZE, 'Minimize'),
    )
    QUALITY = 'Q'
    PRICE = 'P'
    
    MOD_CHOICES = (
        (QUALITY, 'Quality'),
        (PRICE, 'Price'),
    )
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)
    optimization = models.CharField(max_length=2, choices=OPT_CHOICES, default=MAXIMIZE)
    min_value = models.FloatField(default=0)
    max_value = models.FloatField(default=0)
    modeling = models.CharField(max_length=2, choices=MOD_CHOICES, default=QUALITY)
    resource = models.ForeignKey('Resource')
    unit = models.ForeignKey('Unit')
    sensitivity_distribution = models.ForeignKey('ProbabilityDistribution', related_name='sensitivity')
    value_distribution = models.ForeignKey('ProbabilityDistribution', related_name='value')
    
    def __unicode__(self):  # Python 3: def __str__(self):
        return self.name

class Service(models.Model):
    FILE = 'F'
    DATABASE = 'D'
    CONVERTER_CHOICES = (
        (DATABASE, 'Database'),
        (FILE, 'File'),	
    )
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)
    file_name_demand = models.CharField(max_length=100, verbose_name= 'Demand file')
    converter_origin = models.CharField(max_length=1, choices=CONVERTER_CHOICES, default=DATABASE)
    file_name_converter = models.CharField(max_length=100, verbose_name= 'Traffic converter')
    
    decision_variables = models.ManyToManyField(DecisionVariable, through='Service_DecisionVariable')
    
    def __unicode__(self):  # Python 3: def __str__(self):
        return self.name

	
class Service_DecisionVariable(models.Model):
    id_service = models.ForeignKey(Service)
    id_decision_variable = models.ForeignKey(DecisionVariable)
	
    def __unicode__(self):  # Python 3: def __str__(self):
        return  str(self.id_decision_variable)

class Provider(models.Model):
    ACTIVE = 'A'
    INACTIVE = 'I'
    PROV_STAT_CHOICES = (
	(ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
    )
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)
    market_position =  models.FloatField(default=0,
					blank=False,
					validators=[MaxValueValidator(1),
					MinValueValidator(0)]) 
    adaptation_factor =  models.FloatField(default=0,
					blank=False,
					validators=[MaxValueValidator(1),
					MinValueValidator(0)]) 
    status = models.CharField(max_length=1, 
			      choices=PROV_STAT_CHOICES, 
			      default=ACTIVE)
    num_ancestors = models.IntegerField(default=1,
					 blank=False,
					 validators=[MinValueValidator(1), 
						     MaxValueValidator(10)]
					)
    debug = models.BooleanField(default = False)
    service = models.ForeignKey(Service)
    monopolist_position = models.FloatField(default=0,
					blank=False,
					validators=[MaxValueValidator(1),
					MinValueValidator(0)])  
    seed = models.BooleanField(default = False)
    year = models.IntegerField(default=0,
			       blank=False,
			       validators=[MinValueValidator(1), 
					   MaxValueValidator(9999)]
			       )
    month = models.IntegerField(default=0,
				blank=False,
				validators=[MinValueValidator(1), 
				            MaxValueValidator(12)
					   ]
			       )
    day = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(1), 
					  MaxValueValidator(31) ]
			       )
    hour = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(0), 
					  MaxValueValidator(24) ]
			       )
    minute = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(0), 
					  MaxValueValidator(59) ]
			       )
    second = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(0), 
					  MaxValueValidator(59) ]
			       )
    microsecond = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(0), 
					  MaxValueValidator(999999) ]
			       )
    class_name = models.CharField(max_length=60)
    start_from_period = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(1), 
					  MaxValueValidator(9999) ]
			       )

    
    def __unicode__(self):  # Python 3: def __str__(self):
	return self.name

class Provider_Resource(models.Model):
    provider = models.ForeignKey(Provider)
    resource = models.ForeignKey(Resource)
    capacity = models.FloatField(default=0)
    cost = models.FloatField(default=0)
    service = models.ForeignKey(Service)

class offeringData(models.Model):
    DECISION_VARIABLES = 'D'
    CALCULATED_FIELD = 'C'
    OFF_CHOICES = (
        (DECISION_VARIABLES, 'Decision Variable'),
        (CALCULATED_FIELD, 'Calculated Field'),
    )
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)
    type = models.CharField(max_length=1, choices=OFF_CHOICES, default=DECISION_VARIABLES)
    decision_variable = models.ForeignKey(DecisionVariable, blank=True, null=True)
    function = models.CharField(max_length=100, blank=True, null=True)
    
    def __unicode__(self):  # Python 3: def __str__(self):
	return self.name

class Graphic(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)
    description = models.TextField(blank=True)
    def __unicode__(self):  # Python 3: def __str__(self):
	return self.name

class Axis_Graphic(models.Model):
    id = models.AutoField(primary_key=True)
    graphic = models.ForeignKey(Graphic)
    x_axis = models.ForeignKey(offeringData, related_name='x_axis')
    y_axis = models.ForeignKey(offeringData, related_name='y_axis')
    detail = models.BooleanField(default = True)
    label = models.ForeignKey(offeringData, related_name='label', blank=True, null=True)
    color = models.ForeignKey(offeringData, related_name='color', blank=True, null=True)
    column1 = models.ForeignKey(offeringData, related_name='column1', blank=True, null=True)
    column2 = models.ForeignKey(offeringData, related_name='column2', blank=True, null=True)
    column3 = models.ForeignKey(offeringData, related_name='column3', blank=True, null=True)
    column4 = models.ForeignKey(offeringData, related_name='column4', blank=True, null=True)
	
class Presenter(models.Model):
    id =  models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)
    
    def __unicode__(self):  # Python 3: def __str__(self):
	return self.name

class Presenter_Graphic(models.Model):
    presenter = models.ForeignKey(Presenter)
    graphic = models.ForeignKey(Graphic)

class Consumer(models.Model):
    id = models.AutoField(primary_key=True)
    observartions = models.TextField(blank=True)
    number_execute = models.IntegerField(default=1,
					 blank=False,
					 validators=[MinValueValidator(1), 
						     MaxValueValidator(9999)]
					)
    seed = models.BooleanField(default = False)
    year = models.IntegerField(default=0,
			       blank=False,
			       validators=[MinValueValidator(1), 
					   MaxValueValidator(9999)]
			       )
    month = models.IntegerField(default=0,
				blank=False,
				validators=[MinValueValidator(1), 
				            MaxValueValidator(12)
					   ]
			       )
    day = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(1), 
					  MaxValueValidator(31) ]
			       )
    hour = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(0), 
					  MaxValueValidator(24) ]
			       )
    minute = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(0), 
					  MaxValueValidator(59) ]
			       )
    second = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(0), 
					  MaxValueValidator(59) ]
			       )
    microsecond = models.IntegerField(default=0,
			      blank=False,
			      validators=[MinValueValidator(0), 
					  MaxValueValidator(999999) ]
			       )			       

class ConsumerService(models.Model):
    id = models.AutoField(primary_key=True)
    consumer = models.ForeignKey(Consumer)
    service = models.ForeignKey(Service)
    average = models.FloatField(default=0)
    variance = models.FloatField(default=0)
    market_potential = models.FloatField(default=0)
    execute = models.BooleanField(default = False)

class ExecutionGroup(models.Model):
    ACTIVE = 'A'
    INACTIVE = 'I'
    PROV_STAT_CHOICES = (
	(ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
    )
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)
    status = models.CharField(max_length=1, 
			      choices=PROV_STAT_CHOICES, 
			      default=ACTIVE)
    description = models.TextField(blank=True)
    
    def __unicode__(self):  # Python 3: def __str__(self):
	return self.name
    
class ExecutionConfiguration(models.Model):
    ACTIVE = 'A'
    INACTIVE = 'I'
    PROV_STAT_CHOICES = (
	(ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
    )
    id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=1, 
			      choices=PROV_STAT_CHOICES, 
			      default=ACTIVE)
    description = models.TextField(blank=True)
    execution_group = models.ForeignKey(ExecutionGroup)
    number_consumers = models.IntegerField(default=1, blank=False)
    number_periods = models.IntegerField(default=1, blank=False)
    
    def __unicode__(self):  # Python 3: def __str__(self):
	return self.execution_group.name + ' ' + str(self.id)
    

class ExecutionConfigurationProviders(models.Model):
    id = models.AutoField(primary_key=True)
    execution_configuration = models.ForeignKey(ExecutionConfiguration)
    provider = models.ForeignKey(Provider)
 
class GeneralParameters(models.Model):
	id = models.AutoField(primary_key=True)
	bid_periods = models.IntegerField(default=10, blank=False)
	pareto_fronts_to_exchange = models.IntegerField(default=3, 
							blank=False,
							validators=[MinValueValidator(1)]
						       )
	initial_offer_number = models.IntegerField(default=1, 
						   blank=False,
						   validators=[MinValueValidator(1), MaxValueValidator(10)]
						  )
	num_periods_market_share = models.IntegerField(default=3, 
						   blank=False,
						   validators=[MinValueValidator(1), MaxValueValidator(10)]
						    )
