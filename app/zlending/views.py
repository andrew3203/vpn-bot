from django.shortcuts import render
import json
import logging
from django.views import View
from django.http import JsonResponse


logger = logging.getLogger(__name__)


class LendingView(View):

    def post(self, request, *args, **kwargs):
        return JsonResponse({"ok": "POST request processed"})
    
    def get(self, request, *args, **kwargs):  # for debug
        return render(request, 'zlending/index.html')




def privacy(request):
    return render(request, 'zlending/privacy.html')


def handler404(request, *args, **argv):
    return render(request, 'zlending/404.html', status=404)

