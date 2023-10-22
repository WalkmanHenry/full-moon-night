"""
Analyze images by asynchronously tasks
@FileName:   tasks.py
run: celery -A home worker -l info -P solo
"""
import hashlib
import os
from celery import shared_task, Celery
from home.models import *
from django.conf import settings

# 导入图像处理的相关功能
from home.utils.full_moon import *


# tasks = Celery('tasks', broker=settings.CELERY_BROKER_URL)


@shared_task()
def initial_image_task(image_id):
    """
    初始化图像任务
    :param image_id: 图像id
    :return:
    """
    # 获取ImageModel对象
    image = ImageModel.objects.get(image_id=image_id)
    # 图像类型, 1:随从牌, 2:装备牌
    image_type = 1

    # 判断图像是否已经初始化
    if not image:
        print(f"image_id: {image_id} 数据不存在")
        return False

    if image.is_initialed == 0:
        print(f"image_id: {image_id} 正在被占用")
        return False

    # 设置状态，以避免重复处理
    image.is_initialed = 0
    image.save()

    from django.forms.models import model_to_dict
    from home.utils.full_moon import full_moon
    matches = []

    card_directory = settings.ATTACHMENT_ROOT + 'cards/'
    os.makedirs(card_directory, exist_ok=True)
    fm = full_moon(settings.ATTACHMENT_ROOT)
    result = {'code': 200, 'message': 'success', 'data': 'test'}

    image_data = model_to_dict(image)
    result['data'] = image_data

    image_path = image.file_path
    # 判断文件是否存在
    if not os.path.exists(image_path):
        result['code'] = 404
        result['message'] = 'image file not found'

    # convert FACTION_CHOICES to dict
    factions_dict = {}
    card_result = {}
    for faction in FACTION_CHOICES:
        factions_dict[faction[1]] = faction[0]

    # 第一步，先识别卡牌
    card_list = fm.get_cards(image_path)

    # 第二步，ocr文字识别
    ocr_result = fm.get_ocr_result(image_path)
    card_text_results = [[] for _ in range(len(card_list))]
    for text in ocr_result:
        for i, card in enumerate(card_list):
            if fm.check_point_in_card(card, text[0][0]):
                # 到卡牌顶端的距离
                pixel_to_top = text[0][0][1] - card[1]
                pixel_to_left = text[0][0][0] - card[0]
                text_obj = {
                    'top': pixel_to_top,
                    'left': pixel_to_left,
                    'text': text[1],
                }
                if pixel_to_top < 18:
                    text_obj['type'] = 'name'
                elif pixel_to_top > 430:
                    if 50 < pixel_to_left < 150:
                        text_obj['type'] = 'faction'
                    # 如果值为"装备牌",则设定image_type=2
                    if text_obj['text'] == '装备牌':
                        image_type = 2

                elif 315 <= pixel_to_top < 395:
                    text_obj['type'] = 'desc'

                card_text_results[i].append(text_obj)
                # print(f"text {text[0][0]} card {i}")
                break

    # 第三步，识别星星数
    stars = fm.get_stars(image_path)
    # result['stars_count'] = len(stars)

    if image_type == 1:
        """
        随从牌处理
        """
        # 第四步，attack & health
        attack_health = fm.get_attack_and_health(image.file_path)
        # 第五步，将前四步的数据整合，以卡牌为容器进行归集
        card_values = fm.assign_values_to_cards(attack_health, card_list)
        for i, card in enumerate(card_text_results):
            # make sure the card's id is unique
            card_id = hashlib.md5(image_path.encode('utf-8')).hexdigest()[:6] + "__" + str(i)

            card_dict = {
                'card_id': card_id,
                'name': '',
                'faction': '',
                'desc': '',
                'star': 0,
                'attack': 0,
                'health': 0,
            }
            # 5.1 整合名称、介绍、种族、攻击、生命值
            if int(i) < len(card_values):
                if 'attack' in card_values[i]:
                    card_dict['attack'] = card_values[i]['attack']
                if 'health' in card_values[i]:
                    card_dict['health'] = card_values[i]['health']

            for text_row in card:
                if 'type' not in text_row:
                    continue

                if text_row['type'] == 'name':
                    card_dict['name'] = text_row['text']
                    continue
                elif text_row['type'] == 'faction':
                    card_dict['faction'] = text_row['text']
                elif text_row['type'] == 'desc':
                    if 'desc' not in card_dict:
                        card_dict['desc'] = ''
                    card_dict['desc'] += text_row['text'].strip('\n')

            card_dict['star'] = 0
            # 5.2 整合星级
            for star in stars:
                if fm.check_point_in_card(card_list[i], star[0]):
                    card_dict['star'] += 1

            # 第六步，剪裁卡牌
            card_file_path = os.path.join(card_directory, card_id + '.jpg')
            # print(f"save:{card_list[i]} to {card_file_path}")
            fm.save_image(image_path, card_list[i], card_file_path)

            # 第七步，写入数据库
            # 先通过card_file_path检查是否已经存在记录，如果存在则要作废
            if MinionModel.objects.filter(image=card_file_path, is_valid=1).exists():
                MinionModel.objects.filter(image=card_file_path).update(is_valid=-1)

            if card_dict['faction'] in factions_dict:
                faction = factions_dict[card_dict['faction']]
            else:
                faction = 0

            card_data = MinionModel.objects.create(
                name=card_dict['name'],
                ocrname=card_dict['name'],
                desc=card_dict['desc'],
                faction=faction,
                attack=card_dict['attack'],
                health=card_dict['health'],
                stars=card_dict['star'],
                is_valid=1,
                image=card_file_path,
            )

            card_result[card_id] = card_dict

    if image_type == 2:  # 对应于装备牌
        for i, card in enumerate(card_text_results):
            # 为卡牌生成唯一id
            card_id = hashlib.md5(image_path.encode('utf-8')).hexdigest()[:6] + "__" + str(i)

            # 初始化卡牌字典
            equipment_dict = {
                'card_id': card_id,
                'name': '',
                'desc': '',
                'star': 0,
            }

            # 整合名称、介绍
            for text_row in card:
                if 'type' not in text_row:
                    continue

                if text_row['type'] == 'name':
                    equipment_dict['name'] = text_row['text']
                    continue
                elif text_row['type'] == 'desc':
                    if 'desc' not in equipment_dict:
                        equipment_dict['desc'] = ''
                    equipment_dict['desc'] += text_row['text'].strip('\n')

            # 整合星级
            for star in stars:
                if fm.check_point_in_card(card_list[i], star[0]):
                    equipment_dict['star'] += 1

            # 剪裁卡牌
            equipment_file_path = os.path.join(card_directory, card_id + '.jpg')
            fm.save_image(image_path, card_list[i], equipment_file_path)

            # 写入数据库
            if EquipmentModel.objects.filter(image=equipment_file_path, is_valid=1).exists():
                EquipmentModel.objects.filter(image=equipment_file_path).update(is_valid=-1)

            # 创建装备牌数据
            equipment_data = EquipmentModel.objects.create(
                name=equipment_dict['name'],
                ocrname=equipment_dict['name'],
                desc=equipment_dict['desc'],
                stars=equipment_dict['star'],
                is_valid=1,
                image=equipment_file_path,
            )

            # 如果有特性，还要将特性与装备牌关联起来
            if 'features' in equipment_dict:
                for feature in equipment_dict['features']:
                    equipment_data.features.add(feature)  # 假定feature是一个FeatureModel对象

            equipment_data.save()  # 保存装备牌数据
            card_result[card_id] = equipment_dict  # 将装备牌数据添加到结果中


    image.is_initialed = 1
    image.save()
    return card_result


@shared_task
def cut_card_task(image_path):
    try:
        # Extract the base name of the image file (without extension)
        image_basename = os.path.basename(image_path)
        image_name_without_ext = os.path.splitext(image_basename)[0]

        # Create output directory if not exists
        output_directory = settings.ATTACHMENT_ROOT + 'cards/'
        os.makedirs(output_directory, exist_ok=True)

        img = cv2.imread(image_path)
        if img is None:
            raise Exception("Could not open or find the image")

        # 1. 获取卡牌
        fm = full_moon(settings.ATTACHMENT_ROOT)
        found_cards = fm.get_cards(img)

        # 2. 保存图片
        for i, card in enumerate(found_cards):
            print(f"card: [{i}] {card} to {output_directory}")
            output_file_path = os.path.join(output_directory, f"{image_name_without_ext}_{i + 1}.jpg")

            chop_image = img[card[1]:card[3], card[0]:card[2]]
            cv2.imwrite(output_file_path, chop_image)

        return "Processing completed successfully."
    except Exception as e:
        return str(e)
