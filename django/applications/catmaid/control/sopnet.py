from django.db import models
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from catmaid.models import *
from catmaid.control.authentication import *
from catmaid.control.common import *

from celery.task import task
from itertools import chain

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
	x2, y2, z2 = 1024, 1024, 1

	# bounding box
	# started, terminated timestamp

	# retrieve all slices in the bounding box
	slices = get_slices_in_region(x1, y1, z1, x2, y2, z2)

	print 'nr of slices in subregion', len(slices)

	# retrieve all segments associated with the slices

	ssm = SliceSegmentMap.objects.filter(
		~Q(segmenttype = 1),
		slice_id__in = [s['id'] for s in slices]
		).values('slice_id', 'segment_id', 'direction')

	endssm = SliceSegmentMap.objects.filter(
		slice_id__in = [s['id'] for s in slices],
		segmenttype = 1
		).values('slice_id', 'segment_id', 'direction')

	# TODO, filter based on endsegment or not

	allsegments_from_map = [s['segment_id'] for s in ssm]
	allendsegments_from_map = [s['segment_id'] for s in endssm]

	print 'nr of maps to segments found for slices', len(allsegments_from_map)
	print 'nr of maps to endsegments found for slices', len(allendsegments_from_map)

	print 'nr of maps to segments found for slices reduced', len(list(set(allsegments_from_map)))

	# retrieve slice information
	segments = Segments.objects.filter(
		id__in = allsegments_from_map ).values('id', 'origin_section', 'target_section', 'cost')

	print 'nr of segments', len(segments)

	endsegments = EndSegments.objects.filter(
		id__in = allendsegments_from_map ).values('id', 'sectionindex', 'cost')

	print 'nr of end segments', len(endsegments)

	allsegments = {}
	for s in segments:
		if not s['id'] in allsegments:
			allsegments[ s['id'] ] = s
	for s in endsegments:
		allsegments[ s['id'] ] = s

	print 'nr of all segments', len(allsegments)
	print 'nr of all segments after reduction', len(set(allsegments))

	# generate segments convention string
	# subproblem_segments = {}
	# for segment in segments:
	# 	subproblem_segments[ _segment_convention( segment['origin_section'],
	# 		segment['target_section'], segment['segmentid']) ] = segment

	# print 'first fetch segments list', subproblem_segments

	# retrieve all one-constraints associated with these segments
	constraints = SegmentToConstraintMap.objects.filter(
		segment_id__in = [s['id'] for s in segments] ).values('constraint_id')

	print 'nr of constraints found', len(constraints)

	endconstraints = EndSegmentToConstraintMap.objects.filter(
		endsegment_id__in = [s['id'] for s in endsegments] ).values('constraint_id')

	print 'nr of end constraints found', len(endconstraints)

	# contraint set list
	# subproblem_consistency_contraints = [c['contraint_id'] for c in constraints]

	one_constraints = [s['constraint_id'] for s in constraints] + [s['constraint_id'] for s in endconstraints]
	print 'nr of constraints', len(one_constraints)
	print 'nr of constraints when reduced with set', len(set(one_constraints))

	# retrieve all other segments associated with the constraints
	# and union them with the current segment set
	csm = ConstraintsToSegmentMap.objects.filter(
		id__in = list(set(one_constraints))
		).values('segments', 'endsegments')

	print 'final number of consistency constraints', len(csm)

	# add newly found segments to the subproblem segments

	complementary_segments = set()
	for ele in csm:
		for segid in ele['segments']:
			if not segid in allsegments and not segid in complementary_segments:
				complementary_segments.add( segid )

	print 'nr of complementary segments found through constraints not originally in segments', len(complementary_segments)

	# retrieve new segment information
	segments_to_add = Segments.objects.filter(
		id__in = list(complementary_segments) ).values('id', 'cost')

	for s in segments_to_add:
		if not s['id'] in allsegments:
			allsegments[ s['id'] ] = s

	# TODO: create the equality constraints from slice-to-segment map

	# send problem formulation to sopnet
	f = open('/tmp/test.txt','w')
	f.write('1\n') # nr of subproblems
	f.write('{0}\n'.format(len(allsegments))) # [number of segments]
	for k,v in allsegments.iteritems():
		f.write('{0} {1}\n'.format(k,v['cost']) )
	f.write('{0}\n'.format(len(csm))) # [number of "1"-constraints]
	for ele in csm:
		segandend = ele['segments'] + ele['endsegments']
		f.write('{0} {1}\n'.format(len(segandend), segandend) )
	# [number of "="-constraints]

	f.close()

def get_slices_in_region(x1, y1, z1, x2, y2, z2):

	slices = Slices.objects.filter(
		sectionindex__gte = z1,
		sectionindex__lte = z2,
		center_x__gte = x1,
		center_x__lte = x2,
		center_y__gte = y1,
		center_y__lte = y2
		).all().values('id', 'sectionindex', 'node_id', 'slice_id')

	# print 'slices', slices
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
	problem_formulation()
	return HttpResponse(json.dumps({'message': 'Started async process.'}), mimetype="text/json")

