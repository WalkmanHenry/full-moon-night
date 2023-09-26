from django.db import models
from itertools import chain, combinations

INITIALED_CHOICES = [
    (-1, 'Uninitialized'),
    (0, 'Initializing'),
    (1, 'Initialed'),
]
CHECKED_CHOICES = [
    (-1, 'Unchecked'),
    (1, 'Checked'),
]
VALID_CHOICES = [
    (-1, 'Invalid'),
    (1, 'Valid'),
]
FACTION_CHOICES = [
    (1, '中立'),
    (2, '战士'),
    (3, '野兽'),
    (4, '机械'),
    (5, '自然族'),
    (6, '幽灵'),
    (7, '龙'),
]


class ImageModel(models.Model):
    """
    This model represents an image with a unique file path.

    Fields:
    - file_path: The unique path to the image file.
    - alias: An alternative name or descriptor for the image.
    - is_valid: Indicates whether the image is valid (1) or invalid (-1).
    - is_initialed: Indicates whether the image has been initialized (1) or not (-1).
    """

    image_id = models.AutoField(primary_key=True)
    file_path = models.CharField(max_length=255, unique=True)
    alias = models.CharField(max_length=255)
    # 1=valid, -1=invalid
    is_valid = models.SmallIntegerField(choices=VALID_CHOICES, default=1)
    # 1=initialed, -1=uninitialed
    is_initialed = models.SmallIntegerField(choices=INITIALED_CHOICES, default=-1)

    def __str__(self):
        return self.file_path

    class Meta:
        db_table = 'fmn_image'


class MinionModel(models.Model):
    """
    This model represents a minion with certain attributes and features.

    Fields:
    - name: The name of the minion.
    - attack: The attack value of the minion.
    - health: The health value of the minion.
    - desc: A description of the minion.
    - image: A path to an image representing the minion.
    - stars: A value representing the rarity or power level of the minion.
    - features: The features associated with the minion (ManyToMany relationship with FeatureModel).
    - is_valid: Indicates whether the minion is valid (1) or invalid (-1).
    - is_checked: Indicates whether the minion has been checked (1) or unchecked (-1).
    """

    minion_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, default='')
    # faction = models.CharField(max_length=255, default='Neutral')
    faction = models.SmallIntegerField(choices=FACTION_CHOICES, default=0)
    attack = models.SmallIntegerField(default=0)
    health = models.SmallIntegerField(default=0)
    desc = models.CharField(max_length=255, default='')
    image = models.CharField(max_length=255, default='')
    stars = models.SmallIntegerField(default=0)
    features = models.ManyToManyField('FeatureModel', related_name='minions')

    # 1=valid, -1=invalid
    is_valid = models.SmallIntegerField(choices=VALID_CHOICES, default=1)
    # 1=checked, -1=unchecked
    is_checked = models.SmallIntegerField(choices=CHECKED_CHOICES, default=-1)

    @classmethod
    def generate_combinations_and_offsets(cls, factions):
        """
        根据给定的 factions 列表，生成所有可能的组合和对应的偏移值。
            factions = [1, 2, 6]
            offset_values = generate_combinations_and_offsets(factions)

            # 输出所有可能的组合和对应的偏移值
            for combo, offset in offset_values.items():
                print(f"{combo}: {offset}")

        :param factions: 一个整数列表，表示 faction。
        :return: 一个字典，其中键是字符串格式的组合，值是该组合对应的偏移值。
        """
        # 获取所有可能的组合，不包括空集
        faction_combinations = chain.from_iterable(combinations(factions, r) for r in range(1, len(factions) + 1))

        # 计算每个组合的偏移值
        offset_values = []
        for combo in faction_combinations:
            offset_value = MinionModel.generate_factions_code(combo)
            offset_values.append(offset_value)
        return offset_values

    @classmethod
    def generate_factions_code(cls, factions):
        return sum(10 ** (int(faction) - 1) for faction in factions)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Minion"
        verbose_name_plural = "Minion"
        db_table = 'fmn_minion'


class FeatureModel(models.Model):
    """
    This model represents a feature that can be associated with minions.

    Fields:
    - feature: A short code representing the feature.
    - functional: A description of the functionality associated with the feature.
    """

    feature_id = models.AutoField(primary_key=True)
    feature = models.CharField(max_length=6)
    functional = models.CharField(max_length=255, default='')

    def __str__(self):
        return self.feature

    class Meta:
        verbose_name = "Features"
        verbose_name_plural = "Features"
        db_table = 'fmn_feature'


class FormationModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, default='')
    factions = models.IntegerField(default=0)
    search_minion = models.TextField(default='')

    class Meta:
        db_table = 'fmn_formation'


class PositionModel(models.Model):
    id = models.AutoField(primary_key=True)
    formation = models.ForeignKey(FormationModel, on_delete=models.CASCADE)  # 外键，连接到FormationModel
    position_number = models.PositiveIntegerField()  # 位置编号（1-6）
    minions = models.ManyToManyField('MinionModel')  # 多对多关系，一个位置可以有多个随从

    class Meta:
        db_table = 'fmn_position'
        unique_together = ['formation', 'position_number']  # (formation, position_number)的组合必须是唯一的
