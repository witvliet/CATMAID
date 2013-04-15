from django.views.generic import TemplateView
from django.utils.translation import ugettext as _

from django.shortcuts import render_to_response
from django.template import RequestContext

from neurocity.control.segment import get_random_segment

def language_view(request):
    return render_to_response('neurocity/setlanguage.html', {
            # flag: request.user.userprofile.country.code.lower()
        }, context_instance=RequestContext(request))

def about_view(request):
    return render_to_response('neurocity/about.html', {},
                          context_instance=RequestContext(request))

def terms_view(request):
    return render_to_response('neurocity/terms.html', {},
                          context_instance=RequestContext(request))


class NeurocityHomeView(TemplateView):

    template_name = "neurocity/home.html"

    def get_context_data(self, **kwargs):
        context = super(NeurocityHomeView, self).get_context_data(**kwargs)
        # context['latest_articles'] = Article.objects.all()[:5]
        context['flag'] = self.request.user.userprofile.country.code.lower()
        return context

class LearnView(NeurocityHomeView):

    template_name = "neurocity/learn.html"

    def get_context_data(self, **kwargs):
        context = super(LearnView, self).get_context_data(**kwargs)
        return context

class DashboardView(NeurocityHomeView):

    template_name = "neurocity/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        return context

class ContributeView(NeurocityHomeView):

    template_name = "neurocity/contribute.html"

    def get_context_data(self, **kwargs):
        context = super(ContributeView, self).get_context_data(**kwargs)
        segment = get_random_segment()

        context['originsection'] = segment.origin_section
        context['targetsection'] = segment.target_section
        context['segmentid'] = segment.segmentid
        context['segmentkey'] = segment.id
        context['cost'] = segment.cost

        return context

