from django.db import models
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from catmaid.models import *
from catmaid.control.authentication import *
from catmaid.control.common import *

from celery.task import task

@task
def run_async_process():
	import subprocess
	ls = subprocess.Popen(['ls','-l'], stdout=subprocess.PIPE)
	for ln in ls.stdout:
		print('line:', ln)

@requires_user_role([UserRole.Annotate, UserRole.Browse])
def run_sopnet(request, project_id=None, stack_id=None):
	result = run_async_process.delay()
	return HttpResponse(json.dumps({'message': 'Started async process.'}), mimetype="text/json")

