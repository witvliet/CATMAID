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
import networkx as nx

def _segment_convention( origin_section, target_section, segmentid ):
	return '{0}_{1}-{2}'.format(origin_section, target_section, segmentid)

def problem_formulation(seed_x, seed_y, seed_z, stack_id):
	""" Generate the problem formulation to send to SOPNET """

	border = 100
	zsection_back = 2
	zsection_forward = 10

	z1 = seed_z - zsection_back
	if z1 < 0:
		z1 = 0
	z2 = seed_z + zsection_forward

	# top-left-low z index corner
	x1, y1 = seed_x-border, seed_y-border

	# bottom-right-high z index corner
	x2, y2 = seed_x+border, seed_y+border

	print 'subproblem bounding box is'
	print x1, y1, z1
	print x2, y2, z2

	# x1, y1, z1 = 0, 0, 0
	# x2, y2, z2 = 200, 200, 5
	# x2, y2, z2 = 50, 50, 1

	force_explanation = True

	# prior_ends = 0
	# prior_branchcontinuation = 0 # -10000000000
	prior_continuation = 5e6
	prior_ends = 25e6

	# TODO: started, terminated timestamp, store sopnet run in database

	# TODO: do not compute equality constraints for last section
	# in the stack because we do not have end segments

	# retrieve all slices in the bounding box
	slices = get_slices_in_region(x1, y1, z1, x2, y2, z2)

	# retrieve all segments associated with the slices
	ssm = SliceSegmentMap.objects.filter(
		~Q(segmenttype = 1),
		slice_id__in = [s['id'] for s in slices]
		).values('slice_id', 'segment_id', 'direction')

	endssm = SliceSegmentMap.objects.filter(
		slice_id__in = [s['id'] for s in slices],
		segmenttype = 1
		).values('slice_id', 'segment_id', 'direction')

	allsegments_from_map = [s['segment_id'] for s in ssm]
	endsegment_ids = [s['segment_id'] for s in endssm]

	equality_constraints = {}
	for s in ssm:
		if not s['slice_id'] in equality_constraints:
			equality_constraints[ s['slice_id'] ] = {'left': [], 'right': []}
		if s['direction'] == 1:
			equality_constraints[ s['slice_id'] ]['right'].append( -1*s['segment_id'] )
		else:
			equality_constraints[ s['slice_id'] ]['left'].append( s['segment_id'] )

	for s in endssm:
		if not s['slice_id'] in equality_constraints:
			equality_constraints[ s['slice_id'] ] = {'left': [],'right': []}
		if s['direction'] == 1:
			equality_constraints[ s['slice_id'] ]['right'].append( -1*s['segment_id'] )
		else:
			equality_constraints[ s['slice_id'] ]['left'].append( s['segment_id'] )

	assert len(equality_constraints) == len(slices)

	# retrieve slice information
	segments = Segments.objects.filter(
		id__in = allsegments_from_map ).values('id', 'origin_section', 'target_section', 'cost')

	endsegments = EndSegments.objects.filter(
		id__in = endsegment_ids ).values('id', 'sectionindex', 'cost', 'direction')

	allsegments = {}
	allendsegments = {}
	for s in segments:
		allsegments[ s['id'] ] = s
	for s in endsegments:
		allendsegments[ s['id'] ] = s

	assert 2 * len(slices) == len(endssm)
	assert 2 * len(slices) == len(allendsegments)

	# retrieve all one-constraints associated with these segments
	constraints = SegmentToConstraintMap.objects.filter(
		segment_id__in = allsegments.keys() ).values('constraint_id')

	endconstraints = EndSegmentToConstraintMap.objects.filter(
		endsegment_id__in = [k for k,v in allendsegments.items() if v['direction'] == True ] ).values('constraint_id')

	one_constraints = set([s['constraint_id'] for s in constraints] + 
		[s['constraint_id'] for s in endconstraints])

	# retrieve all other segments associated with the constraints
	# and union them with the current segment set
	csm = ConstraintsToSegmentMap.objects.filter(
		id__in = list(one_constraints)
		).values('segments', 'endsegments')

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

	# retrieve new segment information
	segments_to_add = Segments.objects.filter(
		id__in = list(complementary_segments) ).values('id', 'cost', 'direction')

	endsegments_to_add = EndSegments.objects.filter(
		id__in = list(complementary_endsegments) ).values('id', 'cost', 'direction', 'sectionindex')

	# for es in endsegments_to_add:
	# 	assert es['direction'] == True

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
		f.write('{0} {1}\n'.format(k, v['cost'] + prior_continuation ) )
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

	process = subprocess.Popen(
		'/home/stephan/dev/sopnet/build/solve_subproblems -i /tmp/test.txt',  #  -v debug
		shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE )

	(stdout, stderr) = process.communicate()

	if stdout.split('\n')[1] == '0':
		print 'Optimal solution *NOT* found'
		return

	result_segments = stdout.split('\n')[2].split(' ')[1:]
	
	# retrieve slice information
	segments = Segments.objects.filter(
		id__in = result_segments ).values('id', 'origin_section', 'target_section', 
		'origin_slice_id', 'target1_slice_id', 'target2_slice_id', 'segmenttype', 'direction', 'cost',
		'segmentid' )

	endsegments = EndSegments.objects.filter(
		id__in = result_segments ).values('id', 'sectionindex', 'direction', 'slice_id', 'cost')

	print 'Result of SOPNET solve'
	print 'Segments:', segments
	print 'EndSegments:', endsegments

	graph = nx.DiGraph()

	for seg in segments:
		if seg['segmenttype'] == 2:
			# print 'continuation segment'
			fromkey = '{0}_{1}'.format( seg['origin_section'], seg['origin_slice_id'] )
			tokey = '{0}_{1}'.format( seg['target_section'], seg['target1_slice_id'] )
			node_id = '{0}_{1}-{2}'.format( seg['origin_section'], seg['target_section'], seg['segmentid'] )
			seg['segment_node_id'] = node_id
			graph.add_edge(fromkey, tokey, seg)

		elif seg['segmenttype'] == 3:
			# print 'branch segment'
			# direction does not matter because have undirected graph
			fromkey = '{0}_{1}'.format( seg['origin_section'], seg['origin_slice_id'] )
			tokey1 = '{0}_{1}'.format( seg['target_section'], seg['target1_slice_id'] )
			tokey2 = '{0}_{1}'.format( seg['target_section'], seg['target2_slice_id'] )
			node_id = '{0}_{1}-{2}'.format( seg['origin_section'], seg['target_section'], seg['segmentid'] )
			seg['segment_node_id'] = node_id
			graph.add_edge(fromkey, tokey1, seg)
			graph.add_edge(fromkey, tokey2, seg)

	for seg in endsegments:
		# print 'endsegment'
		slicekey = '{0}_{1}'.format( seg['sectionindex'], seg['slice_id'] )
		if not slicekey in graph:
			graph.add_node( slicekey, seg ) # selected single slice end segment
		else:
			graph.node[ slicekey ] = seg
		
	# print 'graph'
	# print 'nodes:', graph.nodes()
	# print 'edges:', graph.edges()
	subgraphs = nx.weakly_connected_component_subgraphs(graph)

	print 'number of connected subgraphs', len(subgraphs)

	# nx.write_graphml(graph, '/tmp/graph.graphml')
	slicedata = {}
	segmentdata = {}
	for i,graph in enumerate(subgraphs):
		print 'size of connected component', len(graph.nodes())
		if len(graph.nodes()) < 5:
			continue
		slicedata[ i + 10 ] = graph.nodes(data=True)
		segmentdata[ i + 10 ] = graph.edges(data=True)
	# slicedata[ 10 ] = subgraphs[0].nodes(data=True)
	# segmentdata[ 10 ] = subgraphs[0].edges(data=True)

	return HttpResponse(json.dumps({'slices': slicedata, 'segments': segmentdata}), mimetype="text/json")

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
def run_sopnet(request, stack_id=None):
	seed_x = float(request.POST.get('current_slice_x', 0))
	seed_y = float(request.POST.get('current_slice_y', 0))
	seed_z = int(request.POST.get('current_slice_z', 0))
	return problem_formulation(seed_x, seed_y, seed_z, stack_id)
