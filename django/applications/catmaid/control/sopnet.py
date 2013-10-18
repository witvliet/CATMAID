from django.db import models
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from catmaid.models import *
from catmaid.control.authentication import *
from catmaid.control.common import *

from celery.task import task

import subprocess

# Blocksize which tile the image space of the stack in non-overlapping, adjacent blocks

BLOCKSIZE_X = 512
BLOCKSIZE_Y = 512
BLOCKSIZE_Z = 20

@task
def run_slice_extractor():
	# check (e.g. in the database Block table) if slices have already been extracted for this block
	# if not, call SOPNET SliceExtractor tool with bounding box request and return
	pass

@task
def run_segment_extractor():
	pass

@task
def run_suproblem_solver():
	# check if the segment are already extracted for the block, if not either
	# 1. create a new run_segment_extractor task and run it. wait for it to finish
	# 2. report back to the caller that the segment extractor has to complete first
	#    for the subproblem solver to run

# example task
# call it asynchronously with result = run_async_process.delay()
@task
def run_async_process():
	ls = subprocess.Popen(['ls','-l'], stdout=subprocess.PIPE)
	for ln in ls.stdout:
		print('line:', ln)

def request_solution(request, project_id=None, stack_id=None):

	# coordinates where the user clicked
	x = int(request.GET.get('x', 0))
	y = int(request.GET.get('x', 0))
	z = int(request.GET.get('z', 0))

	# retrieve the index of the block (core-region) associated with this location
	block_i = x / BLOCKSIZE_X
	block_j = y / BLOCKSIZE_Y
	block_k = z / BLOCKSIZE_Z

	# if the block has not been solved already, run it
	run_suproblem_solver.delay()

    return HttpResponse(json.dumps({'message': 'Started the solution process.'}), mimetype="text/json")


