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
from django.contrib.auth.decorators import login_required

from catmaid.control.segment import *
from catmaid.models import SegmentVote
from neurocity.forms import *

import datetime
import json
from datetime import timedelta, datetime, date
from itertools import groupby

from ratelimit.decorators import ratelimit
from django.shortcuts import redirect

def maxlimit(request):
    return render_to_response('neurocity/maxlimit.html', {},
     context_instance=RequestContext(request))

@login_required
def userstatistics_view(request):

    total_vote_count_for_user = SegmentVote.objects.filter(
        user = request.user
    ).values('id')

    start_date = datetime.now() - timedelta(7)
    end_date = datetime.now()

    def extract_date(entity):
        return entity.creation_time.date()

    entities = SegmentVote.objects.filter(
        creation_time__range = (start_date, end_date)).order_by('creation_time')

    matches = []
    for creation_date, group in groupby(entities, key=extract_date):
        matches.append( (creation_date.strftime("%Y-%m-%d"), len(list(group)) ) )

    return render_to_response('neurocity/statistics.html', {
        'total_nr_of_votes': len(total_vote_count_for_user),
        'matches': matches
        }, context_instance=RequestContext(request))

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

def home_view(request):
    context = {}
    context['nc_home_active'] = 'active'
    context['GOOGLE_TRACKING_ID'] = settings.GOOGLE_TRACKING_ID
    return render(request, 'neurocity/home.html', context)

def tutorial_view(request):
    context = {}
    context['nc_tutorial_active'] = 'active'
    context['GOOGLE_TRACKING_ID'] = settings.GOOGLE_TRACKING_ID
    return render(request, 'neurocity/tutorial.html', context)

def learn_view(request):
    context = {}
    context['nc_learn_active'] = 'active'
    context['GOOGLE_TRACKING_ID'] = settings.GOOGLE_TRACKING_ID
    return render(request, 'neurocity/learn.html', context)

def leaderboard_view(request):
    context = {}
    context['nc_dashboard_active'] = 'active'
    context['flag'] = request.user.userprofile.country.code.lower()
    context['GOOGLE_TRACKING_ID'] = settings.GOOGLE_TRACKING_ID
    # context['sv_count'] = SegmentVote.objects.filter(
    #     creation_time__gte=datetime.date.today(),
    #     creation_time__lt=datetime.date.today()+datetime.timedelta(days=1)
    # ).count()

    daily_vote_count = SegmentVote.objects.filter(
        # creation_time__gte=date.today(),
        # creation_time__lt=date.today()+timedelta(days=1)
    ).values('user', 'user__username', 'user__userprofile__country').annotate(uc = Count('user')).order_by('uc')
    print >> sys.stderr, 'daily_vote_count', daily_vote_count
    result_score = []
    for i, q in enumerate(daily_vote_count):
        result_score.append((i+1, q['user__username'], q['user__userprofile__country'].lower(), q['uc']) )
    context['result_score'] = result_score

    return render(request, 'neurocity/dashboard.html', context)

def _add_stackinfo( context ):
    stack = get_object_or_404(Stack, pk=settings.CURRENT_STACK_ID)
    context[ 'tile_base_url' ] = stack.image_base
    context[ 'tile_source_type' ] = stack.tile_source_type
    if hasattr(settings, 'SEGMENTATION_ZOOM_LEVEL'):
        context[ 'zoom_level' ] = settings.SEGMENTATION_ZOOM_LEVEL
    else:
        context[ 'zoom_level' ] = 0
    return context


# def segmentonly_view(request):
#     context = {}
#     context['nc_segmentonly'] = True
#     segmentkey = int( request.GET.get('segmentkey', '0') )
#     segment = get_segment_by_key( segmentkey )
#     context[ 'segmentsequence' ] = [{
#         'id': segment.id,
#         'segmentid': segment.segmentid,
#         'origin_section': segment.origin_section,
#         'target_section': segment.target_section,
#         'cost': segment.cost
#     }]
#     context = _add_stackinfo( context )
#     return render(request, 'neurocity/contribute.html', context)

@login_required
@ratelimit(ip=True, method=None, rate='50/m')
def match_view(request):
    if request.limited:
        return redirect('maxlimit')
    context = {
        'nc_matchonly': False,
        'nc_match_active': 'active',
        'segmentsequence': json.dumps( get_match_segment_sequence_random() ),
    }
    context = _add_stackinfo( context )
    print >> sys.stderr, context
    return render_to_response('neurocity/match.html', context,
     context_instance=RequestContext(request))

@login_required
@ratelimit(ip=True, method=None, rate='50/m')
def matchonly_view(request):
    sectionindex = int( request.GET.get('sectionindex', '0') )
    slice_id = int( request.GET.get('slice_id', '0') )
    context = {
        'nc_matchonly': True,
        'nc_match_active': 'active',
        'segmentsequence': json.dumps( get_match_segment_sequence_for_slice(
            sectionindex,
            slice_id ) ),
    }
    context = _add_stackinfo( context )
    print >> sys.stderr, context
    return render_to_response('neurocity/match.html', context,
     context_instance=RequestContext(request))

# @ratelimit(ip=True, method=None, rate='50/m')
# def contribute_view(request):
#     if request.limited:
#         return redirect('maxlimit')
#     context = {
#         'nc_contribute_active': 'active',
#         'segmentsequence': json.dumps( get_segment_sequence() ),
#     }
#     context = _add_stackinfo( context )
#     return render_to_response('neurocity/contribute.html', context,
#      context_instance=RequestContext(request))

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
