from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings

import numpy as np
import os, os.path
from contextlib import closing
import h5py
import random
import time
import sys

from catmaid.models import *
from catmaid.objects import *
from catmaid.control.authentication import *
from catmaid.control.common import *

@login_required
def vote(request):

    stack_id = settings.CURRENT_STACK_ID
    stack = get_object_or_404(Stack, pk=stack_id)

    good_segment = int(request.POST.get('good_segment', -1))
    bad_segments = map(int, request.POST.getlist('bad_segments[]', []))
    elapsed_time = int(request.POST.get('elapsed_time', 0))

    if good_segment == -1:
        return HttpResponse(json.dumps({'error':'Invalid segmentkey'}), mimetype='text/json')
    else:
        good_segment = Segments.objects.get(pk=good_segment)
    
    # update good segment
    good_segment.nr_of_votes += 1
    good_segment.good_counter += 1
    good_segment.save()
    
    sv = SegmentVote()
    sv.user = request.user
    sv.stack = stack
    sv.vote = 1
    sv.segment = good_segment
    sv.elapsed_time = elapsed_time
    sv.save()

    # update bad segments
    for bad_segment_id in bad_segments:

        bad_segment = Segments.objects.get(pk=bad_segment_id)
        bad_segment.nr_of_votes += 1
        bad_segment.bad_counter += 1
        bad_segment.save()
        
        sv = SegmentVote()
        sv.user = request.user
        sv.stack = stack
        sv.vote = 1
        sv.segment = bad_segment
        sv.elapsed_time = elapsed_time
        sv.save()

    return HttpResponse(json.dumps({'message':'Voted'}), mimetype='text/json')

# change roles; prevent random vote requests (how?)
# @requires_user_role([UserRole.Annotate, UserRole.Browse])
@login_required
def segment_vote(request):

    project_id = settings.CURRENT_PROJECT_ID
    stack_id = settings.CURRENT_STACK_ID

    project = get_object_or_404(Project, pk=project_id)
    stack = get_object_or_404(Stack, pk=stack_id)

    segmentkey = int(request.POST.get('segmentkey', -1))
    vote = int(request.POST.get('vote', -1))
    comment = request.POST.get('comment', None)
    elapsed_time = int(request.POST.get('elapsed_time', 0))

    if segmentkey == -1:
        return HttpResponse(json.dumps({'error':'Invalid segmentkey'}), mimetype='text/json')
    else:
        segment = Segments.objects.get(pk=segmentkey)

    if vote == -1 or not vote in [1,2,3]:
        return HttpResponse(json.dumps({'error':'Invalid vote'}), mimetype='text/json')
    
    # TODO: increase nr_votes for segment
    # segment.update(...)

    segment.nr_of_votes += 1
    if vote == 1:
        segment.good_counter += 1
    elif vote == 2:
        segment.bad_counter += 1
    segment.save()
    
    sv = SegmentVote()
    sv.user = request.user
    sv.stack = stack
    sv.vote = vote
    sv.segment = segment
    sv.elapsed_time = elapsed_time
    sv.save()

    if not comment is None and len(comment) > 0:
        sc = SegmentComment()
        sc.user = request.user
        sc.project = project
        sc.stack = stack
        sc.segmentvote = sv
        sc.comment = comment
        sc.save()

    return HttpResponse(json.dumps({'message':'Voted'}), mimetype='text/json')

def slicekey( sectionindex, slice_id ):
    return str(sectionindex)+'_'+str(slice_id)

def get_match_segment_sequence_random():

    x = int(random.uniform(settings.CURRENT_EXTENT_MIN_X, settings.CURRENT_EXTENT_MAX_X))
    y = int(random.uniform(settings.CURRENT_EXTENT_MIN_Y, settings.CURRENT_EXTENT_MAX_Y))
    z = int(random.uniform(settings.CURRENT_EXTENT_MIN_Z, settings.CURRENT_EXTENT_MAX_Z))
    border = 30

    project_id = settings.CURRENT_PROJECT_ID
    stack_id = settings.CURRENT_STACK_ID
    stack = get_object_or_404(Stack, pk=stack_id)

    i = 0
    selected_segments = []
    while len(selected_segments) == 0 and i < 10:
        print >> sys.stderr, 'index i', i
        x = int(random.uniform(settings.CURRENT_EXTENT_MIN_X, settings.CURRENT_EXTENT_MAX_X))
        y = int(random.uniform(settings.CURRENT_EXTENT_MIN_Y, settings.CURRENT_EXTENT_MAX_Y))
        z = int(random.uniform(settings.CURRENT_EXTENT_MIN_Z, settings.CURRENT_EXTENT_MAX_Z))
        print >> sys.stderr, 'randomized location', x, y, z
        selected_segments = Segments.objects.filter(
            stack = stack,
            # center_x__range = (x-border,x+border),
            # center_y__range = (y-border,y+border),
            origin_section = z,
            cost__lt = 2.0,
            # nr_of_votes = 0 # TODO: remove later, now only pick segments without a vote
            ).all().order_by('cost').values('origin_section', 'origin_slice_id')
        print 'selected segments', selected_segments.query, 'nr of segments', len(selected_segments)
        border += 20 # grow the border
        i += 1

    if i == 10:
        return []

    # TODO: handle the case that after then iterations, still no good segment found
    origin_section = selected_segments[0]['origin_section']
    origin_slice_id = selected_segments[0]['origin_slice_id']

    return [get_match_segment_sequence( origin_section, origin_slice_id )]

def get_match_segment_sequence_for_slice( sectionindex, slice_id ):
    print 'sectionindex is', sectionindex, 'sliceid', slice_id
    return [get_match_segment_sequence( sectionindex, slice_id )]

def get_match_segment_sequence(origin_section, origin_slice_id):

    project_id = settings.CURRENT_PROJECT_ID
    stack_id = settings.CURRENT_STACK_ID

    stack = get_object_or_404(Stack, pk=stack_id)
    sliceinfo = StackSliceInfo.objects.get(stack=stack)

    target_section = None

    # TODO: using SliceSegmentMap and also include the EndSegment (but then start with slice)
    segments = Segments.objects.filter(
        origin_section = origin_section,
        origin_slice_id = origin_slice_id,
        direction = 1,
        stack = stack,
        ).order_by('cost').values('id', 'segmentid', 'segmenttype',
            'origin_section', 'origin_slice_id',
            'target_section', 'target1_slice_id', 'target2_slice_id', 'cost')

    # retrieve slice information for each fetched slice

    slice_node_ids = [ str(origin_section) + '_' + str(origin_slice_id) ]
    for segment in segments:
        if segment['segmenttype'] == 2:
            slice_node_ids.append( slicekey( segment['target_section'], segment['target1_slice_id'] ) )
            target_section = segment['target_section']
        elif segment['segmenttype'] == 3:
            slice_node_ids.append( slicekey( segment['target_section'], segment['target1_slice_id'] ) )
            slice_node_ids.append( slicekey( segment['target_section'], segment['target2_slice_id'] ) )
            target_section = segment['target_section']

    # print 'nodeids', slice_node_ids

    slices = list( Slices.objects.filter(
        stack = stack,
        node_id__in = slice_node_ids ) )

    # find maximal bounding box across all slices
    # TODO: check, should not individually call database again
    min_x, min_y, max_x, max_y = slices[0].min_x, slices[0].min_y, slices[0].max_x, slices[0].max_y
    origin_slice = {
            'min_x': slices[0].min_x, 'max_x': slices[0].max_x,
            'min_y': slices[0].min_y, 'max_y': slices[0].max_y,
            'slicepath': slice_path2( slices[0].node_id, sliceinfo ),
            'width': slices[0].max_x - slices[0].min_x,
            'height': slices[0].max_y - slices[0].min_y,
            'origin_slice_id': slices[0].slice_id }

    targetslices = {}
    for slice in slices[1:]:
        min_x = min(min_x, slice.min_x)
        min_y = min(min_y, slice.min_y)
        max_x = max(max_x, slice.max_x)
        max_y = max(max_y, slice.max_y)
        targetslices[ slice.node_id ] = {
            'min_x': slice.min_x, 'max_x': slice.max_x,
            'min_y': slice.min_y, 'max_y': slice.max_y,
            'slicepath': slice_path2( slice.node_id, sliceinfo ),
            'width': slice.max_x - slice.min_x,
            'height': slice.max_y - slice.min_y }

    target_segments = []
    for segment in segments:
        segmententry = {
            'segmenttype': segment['segmenttype'],
            'cost': segment['cost'],
            'primarykey': segment['id'],
            'slice_ids': []
        }
        if segment['segmenttype'] == 2:
            segmententry['slice_ids'].append( targetslices[ slicekey( segment['target_section'], segment['target1_slice_id'] ) ] )
        elif segment['segmenttype'] == 3:
            segmententry['slice_ids'].append( targetslices[ slicekey( segment['target_section'], segment['target1_slice_id'] ) ] )
            segmententry['slice_ids'].append( targetslices[ slicekey( segment['target_section'], segment['target2_slice_id'] ) ] )

        target_segments.append( segmententry )

    totalbb = {
            'min_x': min_x, 'max_x': max_x,
            'min_y': min_y, 'max_y': max_y,
            'width': max_x - min_x,
            'height': max_y - min_y }

    result = {
        'origin_section': origin_section,
        'target_section': target_section,
        'totalbb': totalbb,
        'tile_width': stack.tile_width,
        'tile_height': stack.tile_height,
        'origin_slice': origin_slice,
        'target_segments': target_segments
    }
    print >> sys.stderr, 'results', result
    return result


def get_segment_sequence():

    project_id = settings.CURRENT_PROJECT_ID
    stack_id = settings.CURRENT_STACK_ID

    # assumes the primary keys of the segments table
    # are monotonically increasing and continuous
    # dummy random selection strategy:
    # - find a randint in (1,max_nr_of_segments) to
    #   retrieve a segment without any filtering

    stack = get_object_or_404(Stack, pk=stack_id)
    project = get_object_or_404(Project, pk=project_id)

    # do performance evaluation on this
    # TODO: if filter based on nr_of_votes, should use
    # read uncommitted to not cause deadlock
    # TODO: performance with a sort_by with a limit
    # TODO: use center_x/y and origin/target section to
    #       confine to region of interest 
    # segments = Segments.objects.filter(
    #         # stack = stack,
    #         # project = project,
    #         cost__lt = 2.0).all().values('id', 'segmentid', 'origin_section', 'target_section', 'cost')

    result = []
    # for i in range(10):
    #     result.append( random.choice( segments ) )
    return result

def get_segment( project, stack, origin_section, target_section, segment_id ):
    """ TODO: add segment node_id column to database """
    segments = Segments.objects.filter(
            # stack = stack,
            # project = project,
            origin_section = origin_section,
            target_section = target_section,
            segmentid = segment_id ).all()
    if len(segments) == 0:
        return None
    else:
        return segments[0] # what if more than one found?

def get_segment_by_key( segmentkey ):
    return Segments.objects.get( pk = segmentkey )

def slice_path( node_id, sliceinfo ):
    sectionindex, slice_id = node_id.split('_')
    fnametuple = tuple(str(slice_id))
    fname = fnametuple[-1] + '.' + sliceinfo.file_extension
    fpathslice = fnametuple[:-1]
    slice_path_local = os.path.join( 
        str(sliceinfo.slice_base_path).rstrip('\n'), 
        str(sectionindex), 
        '/'.join(fpathslice),
        fname )
    return slice_path_local

def slice_path2( node_id, sliceinfo ):
    sectionindex, slice_id = node_id.split('_')
    fnametuple = tuple(str(slice_id))
    fname = fnametuple[-1] + '.' + sliceinfo.file_extension
    fpathslice = fnametuple[:-1]
    slice_path_url = os.path.join( 
        str(sliceinfo.slice_base_url).rstrip('\n'), 
        str(sectionindex), 
        '/'.join(fpathslice),
        fname )
    return slice_path_url

@login_required
def get_segment_boundingbox(request):

    project_id = settings.CURRENT_PROJECT_ID
    stack_id = settings.CURRENT_STACK_ID
    
    stack = get_object_or_404(Stack, pk=stack_id)
    project = get_object_or_404(Project, pk=project_id)
    sliceinfo = StackSliceInfo.objects.get(stack=stack)

    segmentid = request.GET.get('segmentid', '0')
    originsection = int(request.GET.get('originsection', '0'))
    targetsection = int(request.GET.get('targetsection', '0'))
    edge = int(request.GET.get('edge', '0'))

    # segment = get_segment( project, stack, originsection, targetsection, segmentid )
    segment = get_segment_by_key( segmentid )

    slice_node_ids = [ str(segment.origin_section) + '_' + str(segment.origin_slice_id) ]
    sections = [ segment.origin_section ]
    if segment.segmenttype == 2:
        slice_node_ids.append( str(segment.target_section) + '_' + str(segment.target1_slice_id) )
        sections.append( segment.target_section )
        slicelist = [0] if edge == 0 else [1]
    elif segment.segmenttype == 3:
        slice_node_ids.append( str(segment.target_section) + '_' + str(segment.target1_slice_id) )
        slice_node_ids.append( str(segment.target_section) + '_' + str(segment.target2_slice_id) )
        sections.append( segment.target_section )
        sections.append( segment.target_section )
        slicelist = [0] if edge == 0 else [1,2]

    # print 'nodeids', slice_node_ids

    slices = list( Slices.objects.filter(
        # stack = stack,
        project = project,
        node_id__in = slice_node_ids ) )

    # find maximal bounding box across all slices
    min_x, min_y, max_x, max_y = slices[0].min_x, slices[0].min_y, slices[0].max_x, slices[0].max_y
    originsection = [{
            'min_x': slices[0].min_x, 'max_x': slices[0].max_x,
            'min_y': slices[0].min_y, 'max_y': slices[0].max_y,
            'slicepath': slice_path2( slices[0].node_id, sliceinfo ),
            'width': slices[0].max_x - slices[0].min_x,
            'height': slices[0].max_y - slices[0].min_y }]

    targetsection = []
    for slice in slices[1:]:
        min_x = min(min_x, slice.min_x)
        min_y = min(min_y, slice.min_y)
        max_x = max(max_x, slice.max_x)
        max_y = max(max_y, slice.max_y)
        targetsection.append({
            'min_x': slice.min_x, 'max_x': slice.max_x,
            'min_y': slice.min_y, 'max_y': slice.max_y,
            'slicepath': slice_path2( slice.node_id, sliceinfo ),
            'width': slice.max_x - slice.min_x,
            'height': slice.max_y - slice.min_y })

    totalbb = {
            'min_x': min_x, 'max_x': max_x,
            'min_y': min_y, 'max_y': max_y,
            'width': max_x - min_x,
            'height': max_y - min_y }

    return HttpResponse(json.dumps({
        'segmenttype': segment.segmenttype,
        'originsection': originsection,
        'targetsection': targetsection,
        'totalbb': totalbb,
        'tile_width': stack.tile_width,
        'tile_height': stack.tile_height 
    }), mimetype="text/json")
