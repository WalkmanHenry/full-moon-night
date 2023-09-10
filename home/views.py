import os
from django.shortcuts import render
from django.http import HttpResponse

from home.models import *
VALID_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']

def index(request):
    return render(request, 'pages/index.html')


# Images Manager start
def imgmanagement_index(request):
    attachment_path = 'static/attachments/'

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

    print('file check')
    for image in images_in_db:
        # check file exists in static/attachments/ directory
        if not os.path.exists(image.file_path):
            image.is_valid = -1
            image.save()

    context = {
        'attachment_path': attachment_path,
        'images': images_in_db,
    }
    return render(request, 'imgmanagement/index.html', context)