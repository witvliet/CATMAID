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
import subprocess

def generate_slice_segment_map():
	""" Generate the equality constraings. Segments ending in slice i
	from the left, and segments tarting in slice i to the right """
	pass

def _segment_convention( origin_section, target_section, segmentid ):
	return '{0}_{1}-{2}'.format(origin_section, target_section, segmentid)

def problem_formulation(seed_x, seed_y):
	""" Generate the problem formulation to send to SOPNET """

	border = 100

	# top-left-low z index corner
	# x1, y1, z1 = seed_x-100, seed_y-100, 0

	# # bottom-right-high z index corner
	# x2, y2, z2 = seed_x+100, seed_y+100, 5

	x1, y1, z1 = 0, 0, 0
	x2, y2, z2 = 800, 800, 2

	# 200: 2 segments
	# 50: 0_580 to 1_576 and 0_444 to 1_231


	print 'process from', x1, y1, z1
	print '...to', x2, y2, z2

	force_explanation = True

	prior_ends = 0
	prior_branchcontinuation = 0 # -10000000000

	# TODO: started, terminated timestamp, store sopnet run in database

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

	# TODO: do not compute equality constraints for last section
	# in the stack because we do not have end segments

	equality_constraints = {}
	for s in ssm:
		if not s['slice_id'] in equality_constraints:
			equality_constraints[ s['slice_id'] ] = {'left': [], 'right': []}
		if s['direction'] == 1:
			equality_constraints[ s['slice_id'] ]['left'].append( s['segment_id'] )
		else:
			equality_constraints[ s['slice_id'] ]['right'].append( -1*s['segment_id'] )

	for s in endssm:
		if not s['slice_id'] in equality_constraints:
			equality_constraints[ s['slice_id'] ] = {'left': [],'right': []}
		if s['direction'] == 1:
			equality_constraints[ s['slice_id'] ]['left'].append( s['segment_id'] )
		else:
			equality_constraints[ s['slice_id'] ]['right'].append( -1*s['segment_id'] )

	# print 'equality constraints', equality_constraints

	print 'nr of maps to segments found for slices', len(allsegments_from_map)
	print 'nr of maps to endsegments found for slices', len(allendsegments_from_map)

	print 'nr of maps to segments found for slices reduced', len(list(set(allsegments_from_map)))
	print 'nr of maps to end segments found for slices reduced', len(list(set(allendsegments_from_map)))

	# retrieve slice information
	segments = Segments.objects.filter(
		id__in = allsegments_from_map ).values('id', 'origin_section', 'target_section', 'cost')

	print 'nr of segments', len(segments)

	endsegments = EndSegments.objects.filter(
		id__in = allendsegments_from_map ).values('id', 'sectionindex', 'cost')

	print 'nr of end segments', len(endsegments)

	allsegments = {}
	allendsegments = {}
	for s in segments:
		allsegments[ s['id'] ] = s
	for s in endsegments:
		allendsegments[ s['id'] ] = s

	print 'nr of all segments', len(allsegments)
	print 'nr of all segments after reduction', len(set(allsegments))

	# retrieve all one-constraints associated with these segments
	constraints = SegmentToConstraintMap.objects.filter(
		segment_id__in = allsegments.keys() ).values('constraint_id')

	print 'nr of constraints found', len(constraints)

	endconstraints = EndSegmentToConstraintMap.objects.filter(
		endsegment_id__in = allendsegments.keys() ).values('constraint_id')

	print 'nr of end constraints found', len(endconstraints)

	# contraint set list
	# subproblem_consistency_contraints = [c['contraint_id'] for c in constraints]

	one_constraints = set([s['constraint_id'] for s in constraints] + [s['constraint_id'] for s in endconstraints])

	print 'nr of constraints', len(one_constraints)

	# retrieve all other segments associated with the constraints
	# and union them with the current segment set
	csm = ConstraintsToSegmentMap.objects.filter(
		id__in = list(one_constraints)
		).values('segments', 'endsegments')

	print 'final number of consistency constraints', len(csm)

	# add newly found segments to the subproblem segments

	complementary_segments = set()
	complementary_endsegments = set()
	for ele in csm:
		for segid in ele['segments']:
			if not segid in allsegments:
				complementary_segments.add( segid )
		for segid in ele['endsegments']:
			if not segid in allendsegments:
				complementary_endsegments.add( segid )

	print 'nr of complementary segments found through constraints not originally in segments', len(complementary_segments)

	# retrieve new segment information
	segments_to_add = Segments.objects.filter(
		id__in = list(complementary_segments) ).values('id', 'cost')

	endsegments_to_add = EndSegments.objects.filter(
		id__in = list(complementary_endsegments) ).values('id', 'cost')

	for s in segments_to_add:
		if not s['id'] in allsegments:
			allsegments[ s['id'] ] = s

	for s in endsegments_to_add:
		if not s['id'] in allendsegments:
			allendsegments[ s['id'] ] = s

	# send problem formulation to sopnet
	f = open('/tmp/test.txt','w')
	f.write('1\n') # nr of subproblems
	f.write('{0}\n'.format(len(allsegments)+len(allendsegments))) # [number of segments]
	for k,v in allsegments.iteritems():
		f.write('{0} {1}\n'.format(k, v['cost'] + prior_branchcontinuation ) )
	for k,v in allendsegments.iteritems():
		f.write('{0} {1}\n'.format(k, v['cost'] + prior_ends ) )
	f.write('{0}\n'.format(len(csm))) # [number of "1"-constraints]
	if force_explanation:
		f.write('==\n')
	else:
		f.write('<=\n')
	for ele in csm:
		segandend = map(str, ele['segments'] + ele['endsegments'])
		f.write('{0} {1}\n'.format(len(segandend), ' '.join(segandend)) )
	f.write('{0}\n'.format(len(equality_constraints))) # [number of "="-constraints]
	for k,v in equality_constraints.iteritems():
		eq_const = v['left'] + v['right']
		if eq_const == 1: # Error, should never have only one end segment associated with slice
			continue
		nr_of_constraints = len(eq_const)
		f.write('{0} {1}\n'.format(nr_of_constraints, ' '.join(map(str, eq_const)) ) )
	f.close()

	# run_async_process.delay()
	process = subprocess.Popen(
		'/home/stephan/dev/sopnet/build/solve_subproblems -i /tmp/test.txt',  #  -v debug
		shell = True,
		stdout=subprocess.PIPE, stderr=subprocess.PIPE )
		# stdout=subprocess.PIPE)

	(stdout, stderr) = process.communicate()
	print 'stdout', 

	if stdout.split('\n')[1] == '0':
		print 'Optimal solution *NOT* found'
		return

	print 'selected segment ids', stdout.split('\n')[2].split(' ')[1:]
	result_segments = stdout.split('\n')[2].split(' ')[1:]
	
	# retrieve slice information
	segments = Segments.objects.filter(
		id__in = result_segments ).values('id', 'origin_section', 'target_section', 
		'origin_slice_id', 'target1_slice_id', 'target2_slice_id', 'segmenttype', 'direction', 'cost')
	endsegments = EndSegments.objects.filter(
		id__in = result_segments ).values('id', 'sectionindex', 'direction', 'slice_id', 'cost')

	print 'good segments', segments
	print 'end segments', endsegments

	import networkx as nx
	graph = nx.Graph()

	for seg in segments:
		if seg['segmenttype'] == 2:
			print 'continuation segment'
			fromkey = '{0}_{1}'.format( seg['origin_section'], seg['origin_slice_id'] )
			tokey = '{0}_{1}'.format( seg['target_section'], seg['target1_slice_id'] )
			graph.add_edge(fromkey, tokey)

		elif seg['segmenttype'] == 3:
			print 'branch segment'
			# direction does not matter because have undirected graph
			fromkey = '{0}_{1}'.format( seg['origin_section'], seg['origin_slice_id'] )
			tokey1 = '{0}_{1}'.format( seg['target_section'], seg['target1_slice_id'] )
			tokey2 = '{0}_{1}'.format( seg['target_section'], seg['target2_slice_id'] )
			graph.add_edge(fromkey, tokey1)
			graph.add_edge(fromkey, tokey2)

	for seg in endsegments:
		print 'endsegment'
		slicekey = '{0}_{1}'.format( seg['sectionindex'], seg['slice_id'] )
		if slicekey in graph:
			print 'slicekey', slicekey, ' in graph. end slice'
		else:
			print 'slicekey', slicekey, ' not in graph. there might be a problem.'
		graph.add_node( slicekey )

	print 'graph'
	print 'nodes:', graph.nodes()
	print 'edges:', graph.edges()

	nx.write_graphml(graph, '/tmp/graph.graphml')

def get_slices_in_region(x1, y1, z1, x2, y2, z2):

	slices = Slices.objects.filter(
		sectionindex__gte = z1,
		sectionindex__lte = z2,
		center_x__gte = x1,
		center_x__lte = x2,
		center_y__gte = y1,
		center_y__lte = y2
		).all().values('id', 'sectionindex', 'node_id', 'slice_id')

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
	print 'run async-----'
	import subprocess
	ls = subprocess.call('/home/stephan/dev/sopnet/build/solve_subproblems -i /tmp/test.txt',  #  -v debug
		shell = True)
		# stdout=subprocess.PIPE)

	print 'run async-----DONE', result
	# ls = ''
	# # ls = subprocess.Popen(['ls','-l'], stdout=subprocess.PIPE)
	# for ln in ls.stdout:
	# 	print 'result is ====', ln
	# 	result += ln

	# return result

	# import subprocess
	# ls = subprocess.Popen(['ls','-l'], stdout=subprocess.PIPE)
	# for ln in ls.stdout:
	# 	print('line:', ln)



# @requires_user_role([UserRole.Annotate, UserRole.Browse])
def run_sopnet(request, project_id=None, stack_id=None):
	# result = run_async_process.delay()
	seed_x = request.POST.get('current_slice_x', 0)
	seed_y = request.POST.get('current_slice_y', 0)
	problem_formulation(seed_x, seed_y)
	return HttpResponse(json.dumps({'message': 'Started async process.'}), mimetype="text/json")

