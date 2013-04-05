from django.views.generic import TemplateView

class SegmentDecisionView(TemplateView):
    """ This view returns a page to decide on the correctness of a segment.
    """
    template_name = "neurocity/segmentdecision.html"

    def get_context_data(self, **kwargs):
        context = super(self.__class__, self).get_context_data(**kwargs)
        # TODO: segmentid
        context['origin_section'] = 0
        context['origin_sliceid'] = 123
        context['target_section'] = 0
        return context

class NeurocityHomeView(TemplateView):

    template_name = "neurocity/home.html"

    def get_context_data(self, **kwargs):
        context = super(NeurocityHomeView, self).get_context_data(**kwargs)
        # context['latest_articles'] = Article.objects.all()[:5]
        return context

class LearnView(TemplateView):

    template_name = "neurocity/learn.html"

    def get_context_data(self, **kwargs):
        context = super(LearnView, self).get_context_data(**kwargs)
        return context

class TestView(TemplateView):

    template_name = "neurocity/test.html"

    def get_context_data(self, **kwargs):
        context = super(TestView, self).get_context_data(**kwargs)
        return context

class ContributeView(TemplateView):

    template_name = "neurocity/contribute.html"

    def get_context_data(self, **kwargs):
        context = super(Contribute, self).get_context_data(**kwargs)
        return context