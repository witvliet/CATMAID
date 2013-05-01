from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

import numpy as np
import os, os.path
from contextlib import closing
import h5py
import random
import time

from catmaid.models import *
from catmaid.objects import *
from catmaid.control.authentication import *
from catmaid.control.common import *


# change roles; prevent random vote requests (how?)
# @requires_user_role([UserRole.Annotate, UserRole.Browse])
@login_required
def segment_vote(request):

    project_id = 11
    stack_id = 15

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

    sv = SegmentVote()
    sv.user = request.user
    sv.project = project
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

def get_segment_sequence():
    """ Sampling from the data volume """

    segments = Segments.objects.filter(
            stack = stack,
            project = p,
            randomforest_cost__lt = 0.5).all()[:100]

    # TODO: intelligent sampling of the segments
    segment = random.choice( segments ) #segments[0]
    print 'segment selected', segment.segmentid, segment.id

    return segment

def get_random_segment():

    project_id = 11
    stack_id = 15
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
    segments = Segments.objects.filter(
            stack = stack,
            project = project,
            cost__lt = 2.0).all()

    # TODO: intelligent sampling of the segments
    segment = random.choice( segments ) # random.choice( segments ) #segments[0]
    print 'retrieve a segment', segment
    # print 'segment selected', segment.origin_section, segment.target_section, segment.segmentid
    return segment

def get_segment( project, stack, origin_section, target_section, segment_id ):
    """ TODO: add segment node_id column to database """
    segments = Segments.objects.filter(
            stack = stack,
            project = project,
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

    project_id = 11
    stack_id = 15

    stack = get_object_or_404(Stack, pk=stack_id)
    project = get_object_or_404(Project, pk=project_id)
    sliceinfo = StackSliceInfo.objects.get(stack=stack)

    segmentid = request.GET.get('segmentid', '0')
    originsection = int(request.GET.get('originsection', '0'))
    targetsection = int(request.GET.get('targetsection', '0'))
    edge = int(request.GET.get('edge', '0'))

    segment = get_segment( project, stack, originsection, targetsection, segmentid )

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

    print 'nodeids', slice_node_ids

    slices = list( Slices.objects.filter(
        stack = stack,
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
