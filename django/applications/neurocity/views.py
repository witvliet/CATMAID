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