from django.db import models
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from catmaid.models import *
from catmaid.control.authentication import *
from catmaid.control.common import *

from celery.task import task

def generate_slice_segment_map():
	""" Generate the equality constraings. Segments ending in slice i
	from the left, and segments tarting in slice i to the right """
	pass

def _segment_convention( origin_section, target_section, segmentid ):
	return '{0}_{1}-{2}'.format(origin_section, target_section, segmentid)

def problem_formulation():
	""" Generate the problem formulation to send to SOPNET """

	# top-left-low z index corner
	x1, y1, z1 = 0, 0, 0

	# bottom-right-high z index corner
	x2, y2, z2 = 512, 512, 10

	# bounding box
	# started, terminated timestamp

	# retrieve all slices in the bounding box
	slices = get_slices_in_region(x1, y1, z1, x2, y2, z2)

	# retrieve all segments associated with the slices

	ssm = SlicesSegmentMap.objects.filter(
		).values('slice_id', 'segment_id', 'direction')

	# retrieve slice information
	segments = Segments.objects.filter(
		id__in = [] ).values('id', 'origin_section', 'target_section', 'segmentid', 'cost')

	# generate segments convention string
	subproblem_segments = {}
	for segment in segments:
		subproblem_segments[ _segment_convention( segment['origin_section'],
			segment['target_section'], segment['segmentid']) ] = segment

	print 'first fetch segments list', subproblem_segments

	# retrieve all one-constraints associated with these segments
	constraints = SegmentToConstraintMap.objects.filter(
		segment_node_id__in = subproblem_segments.keys() ).values('constraint_id')

	# contraint set list
	subproblem_consistency_contraints = [c['contraint_id'] for c in constraints]
	# TODO: how to encode ?

	# retrieve all other segments associated with the constraints
	# and union them with the current segment set
	csm = ConstraintToSegmentMap.objects.filter(
		id__in = subproblem_consistency_contraints
		).values('origin_section', 'target_section', 'segments')

	# add newly found segments to the subproblem segments
	complement_segments = []
	for ele in csm:
		for segid in ele['segments']:
			newsegment_id = '{0}_{1}-{2}'.format(ele['origin_section'],
				ele['target_section'],
				segid )
			if not newsegment_id in subproblem_segments:
				complement_segments.append( newsegment_id )

	# retrieve new segment information
	segments = Segments.objects.filter(
		node_id__in = complement_segments ).values('id', 'origin_section', 'target_section', 'segmentid', 'cost')
	for segment in segments:
		subproblem_segments[ _segment_convention( segment['origin_section'],
			segment['target_section'], segment['segmentid'])] = segment

	# create the equality constraints from map

	# send problem formulation to sopnet
	# ----
	# subproblem_segments
	# subproblem_consistency_contraints
	# subproblem_continuation_contraints

def get_slices_in_region(x1, y1, z1, x2, y2, z2):

	slices = Slices.objects.filter(
		sectionindex__gte = z1,
		sectionindex__lte = z2,
		center_x__gte = x1,
		center_x__lte = x2,
		center_y__gte = y1,
		center_y__lte = y2
		).all().values('id', 'sectionindex', 'node_id', 'slice_id')

	print 'slices', slices
	return slices

def get_segments_in_subvolume():

	# top-left-low z index corner
	x1, y1, z1 = 0, 0, 0

	# bottom-right-high z index corner
	x2, y2, z2 = 512, 512, 10

	segments = Segments.objects.filter(
		origin_section__gte = z1,
		target_section__lte = z2,
		center_x__gte = x1,
		center_x__lte = x2,
		center_y__gte = y1,
		center_y__lte = y2
		).all().values('id', 'segmentid', 'origin_section', 'target_section', 'cost')

	print 'segments', segments

@task
def run_async_process():
	import subprocess
	ls = subprocess.Popen(['ls','-l'], stdout=subprocess.PIPE)
	
	for ln in ls.stdout:
		print('line:', ln)

# @requires_user_role([UserRole.Annotate, UserRole.Browse])
def run_sopnet(request, project_id=None, stack_id=None):
	# result = run_async_process.delay()
	get_segments_in_subvolume()
	return HttpResponse(json.dumps({'message': 'Started async process.'}), mimetype="text/json")

