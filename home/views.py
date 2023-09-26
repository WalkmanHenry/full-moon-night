import hashlib
import os, json, traceback

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from admin_soft.utils import JsonResponse

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


def cards_index(request):
    """
    卡片列表
    """
    context = {}

    context['stars'] = (1, 2, 3, 4, 5, 6)
    context['factions'] = FACTION_CHOICES

    # get features
    context['features'] = FeatureModel.objects.all()

    return render(request, 'cards/index.html', context)


def cards_list(request):
    response = {
        'code': 200,
        'message': 'OK',
        'data': []
    }

    try:
        minions = MinionModel.objects.filter(is_valid=1)

        stars = request.GET.getlist('stars[]')
        if stars:
            minions = minions.filter(stars__in=stars)

        factions = request.GET.getlist('faction[]')
        if factions:
            minions = minions.filter(faction__in=factions)

        query = request.GET.get('query')
        if query:
            minions = minions.filter(Q(name__icontains=query) | Q(desc__icontains=query))

        feature = request.GET.get('feature')
        if feature:
            minions = minions.filter(features__feature=feature)

        order_by = request.GET.get('order_by')
        if order_by:
            if order_by == 'stars':
                minions = minions.order_by('stars', 'faction')
            elif order_by == 'stars-desc':
                minions = minions.order_by('-stars', 'faction')
            elif order_by == 'faction':
                minions = minions.order_by('faction', 'stars')
            elif order_by == 'faction-desc':
                minions = minions.order_by('faction', '-stars')
        else:
            minions = minions.order_by('stars', 'faction')

        response['data'] = [{
            'minion_id': minion.minion_id,
            'name': minion.name,
            'stars': minion.stars,
            'attack': minion.attack,
            'health': minion.health,
            'faction': minion.faction,
            'desc': minion.desc,
            'image': minion.image,
            'features': [feature.feature for feature in minion.features.all()],
        } for minion in minions]

    except Exception as e:
        response['code'] = 500
        response['message'] = str(e)

    response['count'] = len(response['data'])
    return JsonResponse(response)


def formation_save(request):
    response = {'code': 400, 'message': 'Bad Request'}

    try:
        data = json.loads(request.body.decode('utf-8'))
        name = data.get('name')
        if not name:
            name = 'Another Formation'

        # 先获取所有的Minion所涉及的种族
        all_minion_ids = []

        filtered_data = {position_number: minion_ids for position_number, minion_ids in data.items() if
                         position_number != 'name'}
        for position_number, minion_ids in filtered_data.items():
            if position_number == 'name':
                continue
            for id in minion_ids:
                all_minion_ids.append(id)

        if len(all_minion_ids) == 0:
            response['message'] = 'Bad Request: No minion in formation'
            return JsonResponse(response)

        minions = MinionModel.objects.filter(minion_id__in=all_minion_ids)
        unique_factions = minions.values_list('faction', flat=True).distinct()
        # 将所有的minions的name相连接作为search_name字段方便后期搜索
        search_name = ','.join([minion.name for minion in minions])

        faction_int = 0
        # 从所有的minion中取得不重复的fation数据
        for x in list(unique_factions):
            faction_int += 10 ** (x - 1)

        formation = FormationModel.objects.create(name=name, factions=faction_int, search_minion=search_name)

    except (json.JSONDecodeError, TypeError):
        response['message'] = 'Bad Request: Invalid JSON'
        return JsonResponse(response)

    for position_number, minion_ids in filtered_data.items():
        try:
            position_number = int(position_number.replace('position', ''))
        except ValueError:
            response['message'] = 'Bad Request: No minion in formation'
            return JsonResponse(response)

        try:
            minions = MinionModel.objects.filter(minion_id__in=minion_ids)
        except ObjectDoesNotExist:
            response['code'] = 404
            response['message'] = 'Not found: No minion found.'
            return JsonResponse(response)

        position = PositionModel.objects.create(formation=formation, position_number=position_number)
        position.minions.set(minions)

    response['code'] = 200
    response['message'] = 'Success'
    return JsonResponse(response)


def formation_index(request):
    """
    Formation
    """
    context = {
    }

    context['factions'] = FACTION_CHOICES

    return render(request, 'formation/index.html', context)


def formation_list(request):
    # Initialize response dictionary
    response = {
        'code': 400,
        'message': 'Bad Request.',
        'data': []
    }
    try:
        # Get factions from request parameters if available
        factions = request.GET.getlist('factions[]')

        # If factions are provided, filter the formations by those factions
        if factions:
            factions = list(map(int, factions))
            formations = FormationModel.objects.filter(factions__in=factions)
        else:  # Otherwise, retrieve all formations
            formations = FormationModel.objects.all()

        # sort by
        if 'sort' in request.GET and request.GET.get('sort') == 'asc':
            formations.order_by('id')
        else:
            formations.order_by('-id')

        formations.order_by('-id')
        for formation in formations:
            positions = formation.positionmodel_set.all()

            # Extracting positions with their associated minion ids
            positions_data = {}
            for position in positions:
                positions_data[position.position_number] = list(position.minions.values_list('minion_id', flat=True))

            response['code'] = 200
            response['message'] = 'Success'
            response['data'].append({
                'formation_id': formation.id,
                'name': formation.name,
                'factions': formation.factions,
                'positions': positions_data
            })

    except Exception as e:
        response['code'] = 500
        response['message'] = f'Error: {str(e)}'

    return JsonResponse(response)


def formation_list(request):
    # Initialize response dictionary
    response = {
        'code': 400,
        'message': 'Bad Request.',
        'data': []
    }
    factions = request.GET.getlist('faction[]')
    f = MinionModel.generate_combinations_and_offsets(factions)
    try:
        # Get all minions
        minions = MinionModel.objects.all()
        # set minions' id:image to response['minions']
        response['minions'] = {}
        for minion in minions:
            response['minions'][minion.minion_id] = minion.image
        # Get factions from request parameters if available
        factions = request.GET.getlist('faction[]')
        factions_in = MinionModel.generate_combinations_and_offsets(factions)

        # If factions are provided, filter the formations by those factions
        if factions:
            formations = FormationModel.objects.filter(factions__in=factions_in)
        else:  # Otherwise, retrieve all formations
            formations = FormationModel.objects

        query = request.GET.get('query')
        if query:
            formations = formations.filter(Q(name__icontains=query) | Q(search_minion__icontains=query))

        # sort by
        if 'sort' in request.GET and request.GET.get('sort') == 'asc':
            formations = formations.order_by('id')
        else:
            formations = formations.order_by('-id')

        for formation in formations:
            positions = formation.positionmodel_set.all()

            # Extracting positions with their associated minion ids
            positions_data = {}
            for position in positions:
                positions_data[position.position_number] = list(position.minions.values_list('minion_id', flat=True))

            response['code'] = 200
            response['message'] = 'Success'
            response['data'].append({
                'formation_id': formation.id,
                'name': formation.name,
                'factions': formation.factions,
                'positions': positions_data
            })

    except Exception as e:
        response['code'] = 500
        response['message'] = f'Error: {str(e)}'

    return JsonResponse(response)


def formation_remove(request):
    response = {
        'code': 404,
        'message': 'Not Found',
        'data': {}
    }
    id = request.GET.get('id')
    if id:
        # 删除formation和关联的数据
        try:
            formation = FormationModel.objects.get(id=id)
            response['code'] = 200
            response['message'] = 'Success'
            formation.delete()

        except:
            response['code'] = 500
            response['message'] = 'Error in remove formation'

    return JsonResponse(response)
