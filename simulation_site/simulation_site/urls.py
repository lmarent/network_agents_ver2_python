from django.conf.urls import url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
import simulation.views

from django.contrib import admin
admin.autodiscover()


urlpatterns = [
    # Examples:
    # url(r'^$', 'simulation_site.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    
    url(r'^$', simulation.views.ListProbabilityDistributionView.as_view(),
        name='probabilities-list',),
        
    url(r'^new$', simulation.views.CreateProbabilityDistributionView.as_view(),
    name='probabilities-new',),
    
    url(r'^edit/(?P<pk>\d+)/$', simulation.views.UpdateProbabilityDistributionView.as_view(),
        name='probabilities-edit',),

    url(r'^delete/(?P<pk>\d+)/$', simulation.views.DeleteProbabilityDistributionView.as_view(),
        name='probabilities-delete',),

	url(r'^(?P<pk>\d+)/$', simulation.views.ProbabilityDistributionView.as_view(),
        name='probabilities-view',),        
        
    url(r'^edit/(?P<pk>\d+)/discrete$', simulation.views.EditDiscreteProbabilityView.as_view(),
        name='probabilities-edit-discrete',),
]

print staticfiles_urlpatterns()
urlpatterns += staticfiles_urlpatterns()
