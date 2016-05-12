from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.views.generic import ListView
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from simulation.models import ProbabilityDistribution
from simulation.models import DiscreteProbabilityDistribution
import forms
import inspect
import os
import re
import sys

# Create your views here.

class ListProbabilityDistributionView(ListView):

    model = ProbabilityDistribution
    template_name = 'probability_list.html'

class CreateProbabilityDistributionView(CreateView):

    model = ProbabilityDistribution
    template_name = 'edit_probability.html'
    form_class = forms.ProbabilityDistributionForm

    def get_success_url(self):
        return reverse('probabilities-list')

    def get_context_data(self, **kwargs):

        context = super(CreateProbabilityDistributionView, self).get_context_data(**kwargs)
        context['action'] = reverse('probabilities-new')

        return context        
        
    
    def __init__(self, *args, **kwargs):
        super(CreateProbabilityDistributionView, self).__init__(*args, **kwargs)
        available_choices = []
        self.formfield_for_choice_field(available_choices)
        print self.fields
        #self.fields['class_name'].choices = available_choices

class UpdateProbabilityDistributionView(UpdateView):

    model = ProbabilityDistribution
    template_name = 'edit_probability.html'
    form_class = forms.ProbabilityDistributionForm

    def get_success_url(self):
        return reverse('probability-list')

    def __init__(self, *args, **kwargs):
        super(UpdateProbabilityDistributionView, self).__init__(*args, **kwargs)
        available_choices = []
        self.formfield_for_choice_field(available_choices)
        print available_choices
        
    
    def get_context_data(self, **kwargs):
        context = super(UpdateProbabilityDistributionView, self).get_context_data(**kwargs)
        context['action'] = reverse('probabilities-edit',
                                    kwargs={'pk': self.get_object().id})
        return context        

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

class DeleteProbabilityDistributionView(DeleteView):

    model = ProbabilityDistribution
    template_name = 'delete_probability.html'

    def get_success_url(self):
        return reverse('probabilities-list')


class ProbabilityDistributionView(DetailView):

    model = ProbabilityDistribution
    template_name = 'probability.html'

class EditDiscreteProbabilityView(UpdateView):

    model = ProbabilityDistribution
    template_name = 'edit_discreteprobability.html'
    form_class = forms.DiscreteProbabilityFormSet

    def get_success_url(self):

        # redirect to the Contact view.
        return self.get_object().get_absolute_url()
