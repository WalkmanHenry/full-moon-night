import hashlib
import os, json, traceback

from admin_soft.utils import JsonResponse
from django.db import connection
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse
from home.utils.full_moon import *
from .tasks import *

from home.models import *

VALID_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']


def index(request):
    return render(request, 'pages/index.html')


def hello(request):
    context = {

    }
    return HttpResponse('Hello World!')


# Images Manager start
def imgmanagement_index(request):
    attachment_path = settings.ATTACHMENT_ROOT

    # get all files in static/attachments/
    file_list = os.listdir(attachment_path)

    for file_name in file_list:
        file_path = os.path.join(attachment_path, file_name)
        # check if the file is an image
        ext = os.path.splitext(file_name)[1]
        if ext.lower() not in VALID_IMAGE_EXTENSIONS:
            continue

        # check if the image is already in database
        image_data, created = ImageModel.objects.get_or_create(file_path=file_path)

    # sign -1 to is_invalid in db
    images_in_db = ImageModel.objects.filter(is_valid=1)
    existing_files = [os.path.join(attachment_path, image.file_path) for image in images_in_db]

    for image in images_in_db:
        image.init = image.get_is_initialed_display()

        # check file exists in static/attachments/ directory
        if not os.path.exists(image.file_path):
            image.is_valid = -1
            image.save()

    context = {
        'attachment_path': attachment_path,
        'images': images_in_db,
    }

    return render(request, 'imgmanagement/index.html', context)


def imgmanagement_cornernumbers(request):
    """
    Show Conernumber page
    """
    context = {}
    attack_images = {}
    health_images = {}
    file_path = 'static/attachments/stuffs/'
    attack_file_path = file_path + 'attack/'
    health_file_path = file_path + 'health/'

    file_list = os.listdir(attack_file_path)
    for file_name in file_list:
        # check if the file is an image
        file_name_split = file_name.split('.')
        ext = '.' + file_name_split[-1]
        if ext.lower() not in VALID_IMAGE_EXTENSIONS:
            continue
        value = file_name_split[0]
        attack_images[value] = attack_file_path + file_name

    # 先将keys转为int
    attack_keys = list(map(int, attack_images.keys()))
    # 使用sorted函数对字典的键进行排序
    sorted_keys = sorted(attack_keys)
    # 创建一个新的有序字典，以保存排序后的结果
    sorted_attack_images = {}

    # 遍历排序后的键，将对应的键值对添加到新的有序字典中
    for key in sorted_keys:
        sorted_attack_images[key] = attack_images[str(key)]

    file_list = os.listdir(health_file_path)
    for file_name in file_list:
        # check if the file is an image
        file_name_split = file_name.split('.')
        ext = '.' + file_name_split[-1]
        if ext.lower() not in VALID_IMAGE_EXTENSIONS:
            continue
        value = file_name_split[0]
        health_images[value] = health_file_path + file_name

    # 先将keys转为int
    health_keys = list(map(int, health_images.keys()))
    # 使用sorted函数对字典的键进行排序
    sorted_keys = sorted(health_keys)
    # 创建一个新的有序字典，以保存排序后的结果
    sorted_health_images = {}
    for key in sorted_keys:
        sorted_health_images[key] = health_images[str(key)]

    context['attack_images'] = sorted_attack_images
    context['health_images'] = sorted_health_images
    context['attachment_path'] = file_path
    return render(request, 'imgmanagement/cornernumbers.html', context)


def imgmanagement_imageinit(request):
    """
        Initialize the image

    """
    # get id
    id = int(request.GET.get('id'))
    # request.GET.get('force') or -1
    force = request.GET.get('force')
    if force and force.isdigit():
        force = int(force)
    else:
        force = -1

    # get the image file
    context = {
        'force': force,
    }
    response = {
        'code': 404,
        'message': 'not found',
    }

    # 获取图片
    try:
        image = ImageModel.objects.get(image_id=id)
        if force == 1:
            # force to reinitialize
            image.is_initialed = -1
            image.save()

        # print(image)
        # initial_image_task.delay(id)
        initial_image_task.delay(id)
        print('tasks')

        context['image_id'] = image.image_id
        context['file_path'] = image.file_path
        context['is_valid'] = image.is_valid
        context['is_initialed'] = image.is_initialed

        response['code'] = 200
        response['message'] = 'success'
        response['data'] = context
        return HttpResponse(json.dumps(response), content_type="application/json")
    except:
        print('error:')
        traceback.print_exc()
        return HttpResponse(json.dumps(response), content_type="application/json")


def imgmanagement_cutcard(request):
    """
    裁剪卡片
    """
    if request.method == 'POST':
        # Get the image file name from the POST data
        image_file_name = request.POST.get('image_file_name')
    else:
        image_file_name = request.GET.get('image_file_name')

    if image_file_name:
        # Construct the full path of the image file
        file_path = os.path.join(settings.ATTACHMENT_ROOT, image_file_name)
        if os.path.exists(file_path):
            # Trigger the Celery task to process the image
            cut_card_task.delay(file_path)

            return JsonResponse({'message': 'Processing initiated.'}, status=200)
        else:
            return JsonResponse({'error': 'File not found.'}, status=404)
    else:
        return JsonResponse({'error': 'No image file name provided.'}, status=400)
