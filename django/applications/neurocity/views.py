from django.views.generic import TemplateView
from django.utils.translation import ugettext as _

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.mail import send_mail, BadHeaderError
from django.core.urlresolvers import reverse

from catmaid.control.segment import *
from catmaid.models import SegmentVote
from neurocity.forms import *

import datetime
import json

def userstatistics_view(request):
    return render_to_response('neurocity/statistics.html', {},
     context_instance=RequestContext(request))

def profile_view(request):
    if request.method == 'POST':
        form = UserForm(instance=request.user, data=request.POST)
        profileform = UserProfileForm(instance=request.user.userprofile, data=request.POST)
        if form.is_valid() and profileform.is_valid():
            form.save()
            profileform.save()
            return HttpResponseRedirect('/')    
    else:
        form = UserForm(instance=request.user)
        profileform = UserProfileForm(instance=request.user.userprofile)

    return render(request, 'neurocity/profile.html', {
        'form': form,
        'profileform': profileform,
        'flag': request.user.userprofile.country.code.lower()
    })


def language_view(request):
    return render_to_response('neurocity/setlanguage.html', {
        }, context_instance=RequestContext(request))

def about_view(request):
    return render_to_response('neurocity/about.html', {
        }, context_instance=RequestContext(request))

def terms_view(request):
    return render_to_response('neurocity/terms.html', {
        }, context_instance=RequestContext(request))

 # def contact_view(request):
 #     return render_to_response('neurocity/contact.html', {
 #         }, context_instance=RequestContext(request))

class NeurocityBaseView(TemplateView):

    def get_context_data(self, **kwargs):
        context = super(NeurocityBaseView, self).get_context_data(**kwargs)
        # context['flag'] = self.request.user.userprofile.country.code.lower()
        context['GOOGLE_TRACKING_ID'] = settings.GOOGLE_TRACKING_ID
        return context

class NeurocityHomeView(NeurocityBaseView):

    template_name = "neurocity/home.html"

    def get_context_data(self, **kwargs):
        context = super(NeurocityHomeView, self).get_context_data(**kwargs)
        # context['flag'] = self.request.user.userprofile.country.code.lower()
        context['nc_home_active'] = 'active'
        return context

class TutorialView(NeurocityBaseView):

    template_name = "neurocity/tutorial.html"

    def get_context_data(self, **kwargs):
        context = super(TutorialView, self).get_context_data(**kwargs)
        context['nc_tutorial_active'] = 'active'
        return context

class LearnView(NeurocityBaseView):

    template_name = "neurocity/learn.html"

    def get_context_data(self, **kwargs):
        context = super(LearnView, self).get_context_data(**kwargs)
        context['nc_learn_active'] = 'active'
        return context

class DashboardView(NeurocityBaseView):

    template_name = "neurocity/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        context['nc_dashboard_active'] = 'active'
        context['flag'] = self.request.user.userprofile.country.code.lower()
        
        # context['sv_count'] = SegmentVote.objects.filter(
        #     creation_time__gte=datetime.date.today(),
        #     creation_time__lt=datetime.date.today()+datetime.timedelta(days=1)
        # ).count()

        daily_vote_count = SegmentVote.objects.filter(
            creation_time__gte=datetime.date.today(),
            creation_time__lt=datetime.date.today()+datetime.timedelta(days=1)
        ).values('user', 'user__username', 'user__userprofile__country').annotate(uc = Count('user')).order_by('uc')
        result_score = []
        for i, q in enumerate(daily_vote_count):
            result_score.append((i+1, q['user__username'], q['user__userprofile__country'].lower(), q['uc']) )
        context['result_score'] = result_score

        # context['nc_users'] = User.objects.all().count()

        return context

class SegmentOnlyView(NeurocityBaseView):

    template_name = "neurocity/contribute.html"

    def get_context_data(self, **kwargs):
        context = super(SegmentOnlyView, self).get_context_data(**kwargs)

        context['nc_segmentonly'] = True
        segmentkey = int( self.request.GET.get('segmentkey', '0') )
        print 'segmentkey retrieved', segmentkey
        segment = get_segment_by_key( segmentkey )
        # segment = get_random_segment() # TODO: get particular segment
        context['originsection'] = segment.origin_section
        context['targetsection'] = segment.target_section
        context['segmentid'] = segment.segmentid
        context['segmentkey'] = segment.id
        context['tile_base_url'] = 'http://localhost/datastatic/stack2/raw/'
        context['cost'] = segment.cost
        if segment.cost != 0.0:
            context['aiguess'] = '%0.2f' % (1./segment.cost)
        else:
            context['aiguess'] = 0.0
            
        return context

class ContributeView(NeurocityBaseView):

    template_name = "neurocity/contribute.html"

    def get_context_data(self, **kwargs):
        context = super(ContributeView, self).get_context_data(**kwargs)
        context['nc_contribute_active'] = 'active'
        segmentsequence = get_segment_sequence()
        context['segmentsequence'] = json.dumps( segmentsequence )
        context['tile_base_url'] = 'http://localhost:8000/static/stack2/raw/'
                    
        return context

def contact_view(request):

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # TODO: send email if valid
            return HttpResponseRedirect('/')
    else:
        form = ContactForm()

    return render(request, 'neurocity/contact.html', {
        'form': form,
    })


        