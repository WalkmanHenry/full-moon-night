# Import necessary modules from the standard library.
import hashlib
import os, json, traceback

# Import Django-specific utilities and functions.
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict

from django.db import connection
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from django.shortcuts import get_object_or_404
from django.http import JsonResponse

# Import utility functions from the specified modules.
from admin_soft.utils import JsonResponse

# Import functions from the 'home.utils.full_moon' module.
from home.utils.full_moon import *

# Import tasks related to the current module.
from .tasks import *

# Import database models from the 'home' app.
from home.models import *

# Define a list of valid image extensions.
VALID_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']


# Define the main index view function.
def index(request):
    """
    Render the main index page.

    Parameters:
    - request: HTTP request object.

    Returns:
    - Rendered HTML page.
    """
    return render(request, 'pages/index.html')


def hello(request):
    context = {

    }
    return HttpResponse('Hello World!')


# Images Manager start

def imgmanagement_index(request):
    """
    Render the image management index page.

    This function lists all files in the 'static/attachments/' directory,
    checks if they are images and if they exist in the database.

    Parameters:
    - request: HTTP request object.

    Returns:
    - Rendered HTML page for image management.
    """
    attachment_path = settings.ATTACHMENT_ROOT
    file_list = os.listdir(attachment_path)

    for file_name in file_list:
        file_path = os.path.join(attachment_path, file_name)
        ext = os.path.splitext(file_name)[1]
        if ext.lower() not in VALID_IMAGE_EXTENSIONS:
            continue

        image_data, created = ImageModel.objects.get_or_create(file_path=file_path)

    images_in_db = ImageModel.objects.filter(is_valid=1).order_by('is_initialed')
    existing_files = [os.path.join(attachment_path, image.file_path) for image in images_in_db]

    for image in images_in_db:
        image.init = image.get_is_initialed_display()
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
    Render the Corner Numbers page for images.

    Lists and processes all files in specific subdirectories and sorts the images
    by their filenames.

    Parameters:
    - request: HTTP request object.

    Returns:
    - Rendered HTML page for Corner Numbers of images.
    """
    context = {}
    attack_images = {}
    health_images = {}
    file_path = 'static/attachments/stuffs/'
    attack_file_path = file_path + 'attack/'
    health_file_path = file_path + 'health/'

    file_list = os.listdir(attack_file_path)
    for file_name in file_list:
        file_name_split = file_name.split('.')
        ext = '.' + file_name_split[-1]
        if ext.lower() not in VALID_IMAGE_EXTENSIONS:
            continue
        value = file_name_split[0]
        attack_images[value] = attack_file_path + file_name

    attack_keys = list(map(int, attack_images.keys()))
    sorted_keys = sorted(attack_keys)
    sorted_attack_images = {str(key): attack_images[str(key)] for key in sorted_keys}

    file_list = os.listdir(health_file_path)
    for file_name in file_list:
        file_name_split = file_name.split('.')
        ext = '.' + file_name_split[-1]
        if ext.lower() not in VALID_IMAGE_EXTENSIONS:
            continue
        value = file_name_split[0]
        health_images[value] = health_file_path + file_name

    health_keys = list(map(int, health_images.keys()))
    sorted_keys = sorted(health_keys)
    sorted_health_images = {str(key): health_images[str(key)] for key in sorted_keys}

    context['attack_images'] = sorted_attack_images
    context['health_images'] = sorted_health_images
    context['attachment_path'] = file_path

    return render(request, 'imgmanagement/cornernumbers.html', context)


def imgmanagement_imageinit(request):
    """
    View to handle the initialization of a specific image.

    This view retrieves an image by its ID and optionally re-initializes it
    based on the 'force' parameter from the request. If the force reinitialization
    is requested, the view updates the 'is_initialed' status of the image in the
    database. The image initialization is handled asynchronously by adding the task
    to a queue.

    Parameters:
    - request: Django HTTP request object. It is expected to contain:
               - image ID as 'id'
               - an optional 'force' parameter to force reinitialization

    Returns:
    - HttpResponse: A JSON response indicating the result of the operation. The
                    response will either confirm the initialization action or
                    provide an error message.
    """

    # Extract the image ID and 'force' parameter from the request.
    id = int(request.GET.get('id'))
    force = request.GET.get('force')
    if force and force.isdigit():
        force = int(force)
    else:
        force = -1

    # Prepare the initial context and response objects.
    context = {
        'force': force,
    }
    response = {
        'code': 404,
        'message': 'Not Found',
    }

    try:
        # Retrieve the image by its ID from the database.
        image = ImageModel.objects.get(image_id=id)

        # If force reinitialization is requested, update the 'is_initialed' field.
        if force == 1:
            image.is_initialed = -1
            image.save()

        # Queue the image initialization task for asynchronous processing.
        initial_image_task.delay(id)

        # Update the context with the details of the retrieved image.
        context['image_id'] = image.image_id
        context['file_path'] = image.file_path
        context['is_valid'] = image.is_valid
        context['is_initialed'] = image.is_initialed

        # Update the response to indicate successful processing.
        response['code'] = 200
        response['message'] = 'success'
        response['data'] = context

        return HttpResponse(json.dumps(response), content_type="application/json")
    except Exception as e:
        # Log the error and traceback details.
        print('error:', e)
        traceback.print_exc()

        # Return an error response in JSON format.
        return HttpResponse(json.dumps(response), content_type="application/json")


def imgmanagement_cutcard(request):
    """
    View to handle card image cutting.

    This view retrieves the name of an image file from the request, either from
    POST data or GET parameters. If the image file exists, a Celery task is
    triggered to process the image cutting asynchronously.

    Parameters:
    - request: Django HTTP request object. It is expected to contain:
               - image file name as 'image_file_name', either in POST data or GET parameters.

    Returns:
    - JsonResponse: A JSON response indicating the result of the operation. The
                    response will either confirm the cutting action, inform
                    about a missing file, or indicate a missing file name parameter.
    """

    # Determine the request method to extract the image file name accordingly
    if request.method == 'POST':
        image_file_name = request.POST.get('image_file_name')
    else:
        image_file_name = request.GET.get('image_file_name')

    # If an image file name is provided, proceed with processing
    if image_file_name:
        file_path = os.path.join(settings.ATTACHMENT_ROOT, image_file_name)
        if os.path.exists(file_path):
            cut_card_task.delay(file_path)
            return JsonResponse({'message': 'Processing initiated.'}, status=200)
        else:
            return JsonResponse({'error': 'File not found.'}, status=404)
    else:
        return JsonResponse({'error': 'No image file name provided.'}, status=400)


def cards_index(request):
    """
    View to display a list of cards.

    This view populates the context with information about card stars, factions,
    and features, and renders a template to display a list of cards.

    Parameters:
    - request: Django HTTP request object.

    Returns:
    - HttpResponse: Rendered template displaying the list of cards.
    """

    context = {}

    # Pre-populate context with fixed data for stars and factions
    context['stars'] = (1, 2, 3, 4, 5, 6)
    context['factions'] = FACTION_CHOICES

    # Retrieve card features from the database and add to the context
    context['features'] = FeatureModel.objects.all()

    return render(request, 'cards/index.html', context)


def cards_list(request):
    """
    View to retrieve and filter a list of cards (minions) based on specific criteria.

    The available filter criteria include stars, faction, query (for name and description),
    feature, and ordering preferences. The response provides a detailed list of minions
    based on the applied filters.

    Parameters:
    - request: Django HTTP request object. Expected GET parameters:
               - stars[]: List of preferred star ratings.
               - faction[]: List of preferred factions.
               - query: String to match against minion names and descriptions.
               - feature: Specific feature to filter by.
               - order_by: Ordering preference (e.g., 'stars', 'stars-desc', etc.).

    Returns:
    - JsonResponse: A JSON response containing the filtered list of minions and metadata.
    """
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
    """
    View to save a formation of cards (minions) with specific positions.

    The formation is defined by the provided list of minions and their designated positions.
    Additional metadata about the formation, such as the involved factions and a search-friendly
    name (concatenation of minion names), are also generated and stored.

    Parameters:
    - request: Django HTTP request object. Expected JSON body content:
               - name: Name of the formation (optional).
               - positionX: List of minion IDs assigned to the Xth position.
               (X can be any integer value representing a position number.)

    Returns:
    - JsonResponse: A JSON response indicating the result of the formation-saving process.
                    The response will either confirm successful saving or provide error details.
    """
    response = {'code': 400, 'message': 'Bad Request'}

    try:
        # Parse JSON data from the request body
        data = json.loads(request.body.decode('utf-8'))

        formation_id = data.get('formation_id', None)

        # Check if formation_id exists in the database
        existing_formation = None
        if formation_id:
            try:
                existing_formation = FormationModel.objects.get(formation_id=formation_id)
            except FormationModel.DoesNotExist:
                pass

        # Determine whether to create or update based on the presence of formation_id and its existence in the database
        if existing_formation:
            save_model = 'update'
            formation = existing_formation
        else:
            save_model = 'create'

        # Get formation name from data; default to 'Another Formation' if not provided
        name = data.get('name', 'Another Formation')

        # Collect all minion IDs from the provided formation data
        all_minion_ids = []
        all_equipment_ids = []

        # Filter out the 'name' key and only consider position-related keys
        for position_key, position_data in data.items():
            if "position" in position_key:
                all_minion_ids.extend(position_data.get('minions', []))
                all_equipment_ids.extend(position_data.get('equipments', []))

        # If no minions are provided, return an error response
        if not all_minion_ids:
            response['message'] = 'Bad Request: No minion in formation'
            return JsonResponse(response)

        # Fetch all minions corresponding to the provided IDs
        minions = MinionModel.objects.filter(minion_id__in=all_minion_ids)

        # Get a list of unique factions among the fetched minions
        unique_factions = minions.values_list('faction', flat=True).distinct()

        # Concatenate all minion names for easy searching in the future
        search_name = ','.join([minion.name for minion in minions])

        # Compute a unique integer representing the involved factions
        faction_int = sum([10 ** (x - 1) for x in unique_factions])

        if save_model == 'create':
            # Create a new formation record with the given name, factions, and search name
            formation = FormationModel.objects.create(name=name, factions=faction_int, search_minion=search_name)
        else:
            # Updating an existing formation
            formation.name = name
            formation.factions = faction_int
            formation.search_minion = search_name
            formation.save()

            # Remove old position data related to this formation
            PositionModel.objects.filter(formation=formation).delete()


    except (json.JSONDecodeError, TypeError):
        # If there's an error in parsing the JSON data, return an error response
        response['message'] = 'Bad Request: Invalid JSON'
        return JsonResponse(response)

    # Loop over each position in the filtered data to create position records
    for position_key, position_data in data.items():
        if "position" in position_key:
            try:
                position_number = int(position_key.replace('position', ''))
            except ValueError:
                response['message'] = 'Bad Request: Invalid position number'
                return JsonResponse(response)

            try:
                minions = MinionModel.objects.filter(minion_id__in=position_data.get('minions', []))
                equipments = EquipmentModel.objects.filter(equipment_id__in=position_data.get('equipments', []))
            except ObjectDoesNotExist:
                response['code'] = 404
                response['message'] = 'Not Found: No minion or equipment found.'
                return JsonResponse(response)

            position = PositionModel.objects.create(formation=formation, position_number=position_number)
            position.minions.set(minions)
            position.equipments.set(equipments)  # Save the relationship with equipments

    # If everything went well, set the response to indicate success
    response['code'] = 200
    response['message'] = 'Success'
    return JsonResponse(response)


def formation_index(request):
    """
    View to display the formation index page, with a list of available factions.

    Parameters:
    - request: Django HTTP request object.

    Returns:
    - HttpResponse: Rendered HTML template for the formation index.
    """
    context = {}

    # Assign the global FACTION_CHOICES to the context to be used in the template.
    context['factions'] = FACTION_CHOICES

    return render(request, 'formation/index.html', context)


def formation_list(request):
    """
    View to retrieve a list of formations based on the given query parameters.

    Parameters:
    - request: Django HTTP request object. Accepts optional GET parameters:
               - faction[]: List of faction identifiers to filter formations.
               - query: Text search query to match against formation names or involved minions.
               - sort: Sorting order ("asc" for ascending based on formation_id).

    Returns:
    - JsonResponse: A JSON response with a list of formations and any associated details.
                    The response will either confirm successful retrieval or provide error details.
    """
    # Initialize the response dictionary.
    response = {
        'code': 400,
        'message': 'Bad Request.',
        'data': []
    }

    try:
        # Retrieve all minions from the database.
        minions = MinionModel.objects.all()

        # Create a dictionary mapping minion IDs to their associated image.
        response['minions'] = {minion.minion_id: minion.image for minion in minions}

        # Retrieve all equipments from the database.
        equipments = EquipmentModel.objects.all()

        # Create a dictionary mapping equipment IDs to their associated image.
        response['equipments'] = {equipment.equipment_id: equipment.image for equipment in equipments}

        # Retrieve factions from request parameters.
        factions = request.GET.getlist('faction[]')
        factions_in = MinionModel.generate_combinations_and_offsets(factions)

        # If factions are provided, filter formations by those factions.
        if factions:
            formations = FormationModel.objects.filter(factions__in=factions_in)
        else:  # If no factions are provided, retrieve all formations.
            formations = FormationModel.objects.all()

        # If a query is provided, filter formations by name or associated minion names.
        query = request.GET.get('query')
        if query:
            formations = formations.filter(Q(name__icontains=query) | Q(search_minion__icontains=query))

        # Determine sorting order based on the 'sort' parameter.
        if request.GET.get('sort') == 'asc':
            formations = formations.order_by('formation_id')
        else:
            formations = formations.order_by('-formation_id')

        # Loop over each formation to retrieve its details.
        for formation in formations:
            # Fetch all positions associated with the current formation.
            positions = formation.positionmodel_set.all()

            # Extract the positions and their associated minion IDs.
            positions_data = {}
            for position in positions:
                positions_data[position.position_number] = []
                positions_data[position.position_number].append(
                    list(position.minions.values_list('minion_id', flat=True)))
                positions_data[position.position_number].append(
                    list(position.equipments.values_list('equipment_id', flat=True)))

            # Append formation details to the response data list.
            response['data'].append({
                'formation_id': formation.formation_id,
                'name': formation.name,
                'factions': formation.factions,
                'positions': positions_data
            })

        # Update the response code and message to indicate success.
        response['code'] = 200
        response['message'] = 'Success'

    # If there's any exception during the above operations, capture and return the error details.
    except Exception as e:
        response['code'] = 500
        response['message'] = f'Error: {str(e)}'

    return JsonResponse(response)


def formation_get(request):
    formation_id = request.GET.get('id')
    response = {
        'code': 404,
        'message': 'Not Found',
    }

    # 尝试获取指定ID的阵型
    formation = get_object_or_404(FormationModel, formation_id=formation_id)

    # 提取阵型中的每个位置的数据
    positions_data = []
    positions = PositionModel.objects.filter(formation=formation).prefetch_related('minions', 'minions__features',
                                                                                   'equipments', 'equipments__features')

    for position in positions:
        position_dict = {
            'position_number': position.position_number,
            'minions': [],
            'equipments': []
        }

        # 提取每个位置上的随从数据和与随从关联的特征数据
        for minion in position.minions.all():
            features = [feature.feature for feature in minion.features.all()]
            position_dict['minions'].append({
                'id': minion.minion_id,
                'name': minion.name,
                'attack': minion.attack,
                'health': minion.health,
                'desc': minion.desc,
                'stars': minion.stars,
                'features': features,
                'image': minion.image
            })

        # 提取每个位置上的装备数据和与装备关联的特征数据
        for equipment in position.equipments.all():
            features = [feature.feature for feature in equipment.features.all()]
            position_dict['equipments'].append({
                'id': equipment.equipment_id,
                'name': equipment.name,
                'desc': equipment.desc,
                'stars': equipment.stars,
                'features': features,
                'image': equipment.image
            })

        positions_data.append(position_dict)

    response['code'] = 200
    response['message'] = 'Success'
    response['data'] = {
        'formation_name': formation.name,
        'positions': positions_data
    }

    return JsonResponse(response)


def formation_remove(request):
    """
    Remove a formation identified by its ID from the database.

    Parameters:
    - request: Django HTTP request object. Expected GET parameter:
               - id: The ID of the formation to be removed.

    Returns:
    - JsonResponse: A JSON response indicating the result of the deletion process.
    """
    response = {
        'code': 404,
        'message': 'Not Found',
        'data': {}
    }
    id = request.GET.get('id')
    if id:
        try:
            # Retrieve and delete the formation by its ID.
            formation = FormationModel.objects.get(formation_id=id)
            formation.delete()
            response['code'] = 200
            response['message'] = 'Success'

        except:
            response['code'] = 500
            response['message'] = 'Error in removing formation'

    return JsonResponse(response)


def cards_management(request):
    """
    Render a card management page with available stars, factions, and features.

    Parameters:
    - request: Django HTTP request object.

    Returns:
    - HttpResponse: Rendered HTML template for card management.
    """
    context = {}
    context['stars'] = (1, 2, 3, 4, 5, 6)
    context['factions'] = FACTION_CHOICES

    # Retrieve all available features.
    context['features'] = FeatureModel.objects.all()

    return render(request, 'cards/management.html', context)


def cards_multimodify(request):
    """
    Update multiple cards' attributes and potentially associate them with a specific feature.

    Parameters:
    - request: Django HTTP POST request. The request body should contain details of the cards
               and optionally a feature ID to be associated with selected cards.

    Returns:
    - HttpResponse: Rendered HTML template showing a message about the operation's result.
    """
    cards = {}
    cards_ids = []

    # Extract card details from the request POST data.
    for key, rowset in request.POST.items():
        key_row = key.split('_')
        if len(key_row) > 1:
            key_int = int(key_row[1])
            cards_ids.append(key_int)
            if key_int not in cards:
                cards[key_int] = {}
            if key_row[0] == 'name':
                cards[key_int]['name'] = rowset
            elif key_row[0] == 'state':
                cards[key_int]['state'] = rowset
            elif key_row[0] == 'desc':
                cards[key_int]['desc'] = rowset

    # Check if a feature is specified and retrieve it.
    feature_id = request.POST.get('feature', None)
    feature = FeatureModel.objects.get(feature_id=feature_id) if feature_id else None

    if cards_ids:
        # Retrieve and update minions/cards based on the given details.
        minions = MinionModel.objects.filter(minion_id__in=cards_ids)
        for minion in minions:
            to_update = False
            if minion.desc != cards[minion.minion_id]['desc']:
                to_update = True
                minion.desc = cards[minion.minion_id]['desc']
            if minion.name != cards[minion.minion_id]['name']:
                to_update = True
                minion.name = cards[minion.minion_id]['name']

            # Save the updated card details.
            if to_update:
                minion.save()

            # Associate the card with the specified feature, if applicable.
            if int(cards[minion.minion_id]['state']) == 1 and feature:
                minion.features.add(feature)

    message = {
        'title': 'Success',
        'message': 'Successfully updated cards.',
        'url': '/cards/management',
        'timeout': 2,
    }
    return render(request, 'message.html', message)


def equipment_list(request):
    """
    Retrieve a list of equipment based on filters provided in the request.

    Parameters:
    - request: Django HTTP request object. Possible GET parameters include:
               - stars[]: List of star ratings to filter equipment.
               - query: Text to filter equipment by name or description.
               - feature: Feature to filter equipment.
               - order_by: Ordering mechanism (either 'stars' or 'stars-desc').

    Returns:
    - JsonResponse: A JSON response containing the list of equipment and metadata.
    """
    response = {
        'code': 200,
        'message': 'OK',
        'data': []
    }

    try:
        # Filter valid equipment.
        equipments = EquipmentModel.objects.filter(is_valid=1)

        # Apply filtering based on stars if provided.
        stars = request.GET.getlist('stars[]')
        if stars:
            equipments = equipments.filter(stars__in=stars)

        # Filter equipment based on query string in either name or description.
        query = request.GET.get('query')
        if query:
            equipments = equipments.filter(Q(name__icontains=query) | Q(desc__icontains=query))

        # Filter equipment based on associated feature.
        feature = request.GET.get('feature')
        if feature:
            equipments = equipments.filter(features__feature=feature)

        # Sort the equipment based on the provided ordering mechanism or default to 'stars'.
        order_by = request.GET.get('order_by')
        if order_by:
            if order_by == 'stars':
                equipments = equipments.order_by('stars')
            elif order_by == 'stars-desc':
                equipments = equipments.order_by('-stars')
        else:
            equipments = equipments.order_by('stars')

        # Prepare the data for the response.
        response['data'] = [{
            'equipment_id': equipment.equipment_id,
            'name': equipment.name,
            'stars': equipment.stars,
            'desc': equipment.desc,
            'image': equipment.image,
            'features': [feature.feature for feature in equipment.features.all()],
        } for equipment in equipments]

    except Exception as e:
        response['code'] = 500
        response['message'] = str(e)

    response['count'] = len(response['data'])
    return JsonResponse(response)


def equipment_management(request):
    """
    Render an equipment management page with available stars, factions, and features.

    Parameters:
    - request: Django HTTP request object.

    Returns:
    - HttpResponse: Rendered HTML template for equipment management.
    """
    context = {}
    context['stars'] = (1, 2, 3, 4, 5, 6)
    context['factions'] = FACTION_CHOICES

    # Retrieve all available features.
    context['features'] = FeatureModel.objects.all()

    return render(request, 'equipment/management.html', context)


def equipment_multimodify(request):
    """
    Modify multiple equipment records based on POST data.

    Parameters:
    - request: Django HTTP request object with POST data containing:
               - Key-value pairs of equipment attributes to modify.
               - Feature ID to potentially associate with the equipment.

    Returns:
    - HttpResponse: Rendered HTML message indicating success or failure.
    """

    # Parsing POST data to extract equipment details for modifications.
    cards = {}
    cards_ids = []
    for key, rowset in request.POST.items():
        key_row = key.split('_')
        if len(key_row) > 1:
            key_int = int(key_row[1])
            cards_ids.append(key_int)
            if not key_int in cards:
                cards[key_int] = {}
            if key_row[0] == 'name':
                cards[key_int]['name'] = rowset
            elif key_row[0] == 'state':
                cards[key_int]['state'] = rowset
            elif key_row[0] == 'desc':
                cards[key_int]['desc'] = rowset

    # Retrieve feature based on provided feature ID.
    feature_id = request.POST.get('feature', None)
    feature = FeatureModel.objects.get(feature_id=feature_id) if feature_id else None

    # If there are any equipment IDs to modify, process them.
    if cards_ids:
        equipments = EquipmentModel.objects.filter(equipment_id__in=cards_ids)
        for equipment in equipments:
            to_update = False

            # Check if equipment's description has changed.
            if equipment.desc != cards[equipment.equipment_id]['desc']:
                to_update = True
                equipment.desc = cards[equipment.equipment_id]['desc']

            # Check if equipment's name has changed.
            if equipment.name != cards[equipment.equipment_id]['name']:
                to_update = True
                equipment.name = cards[equipment.equipment_id]['name']

            # If any changes detected, save the equipment.
            if to_update:
                print(f"({equipment.equipment_id}) {equipment.name} updated.")
                equipment.save()

            # If state equals 1 and there's a feature, add the feature to the equipment.
            if int(cards[equipment.equipment_id]['state']) == 1 and feature:
                print(
                    f"({equipment.equipment_id}) state: {cards[equipment.equipment_id]['state']}. update featue:{feature} {feature.feature_id}")
                equipment.features.add(feature)

    # Return a message indicating successful update.
    message = {
        'title': 'Success',
        'message': 'Successfully updated cards.',
        'url': '/equipment/management',
        'timeout': 2,
    }
    return render(request, 'message.html', message)
