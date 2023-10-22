from django.db import models
from itertools import chain, combinations

# Choices for image initialization status
INITIALED_CHOICES = [
    (-1, 'Uninitialized'),
    (0, 'Initializing'),
    (1, 'Initialed'),
]

# Choices for checking status
CHECKED_CHOICES = [
    (-1, 'Unchecked'),
    (1, 'Checked'),
]

# Choices for validation status
VALID_CHOICES = [
    (-1, 'Invalid'),
    (1, 'Valid'),
]

# Choices for faction types
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
    is_valid = models.SmallIntegerField(choices=VALID_CHOICES, default=1)
    is_initialed = models.SmallIntegerField(choices=INITIALED_CHOICES, default=-1)

    def __str__(self):
        return self.file_path

    class Meta:
        db_table = 'fmn_image'


class MinionModel(models.Model):
    """
    This model represents a minion with attributes and features.

    Fields:
    - name: The name of the minion.
    - attack: The attack value of the minion.
    - health: The health value of the minion.
    - desc: A description of the minion.
    - image: An image representing the minion.
    - stars: The rarity or power level of the minion.
    - features: Features associated with the minion (ManyToMany with FeatureModel).
    - is_valid: Indicates if the minion is valid (1) or invalid (-1).
    - is_checked: Indicates if the minion has been checked (1) or unchecked (-1).
    """

    minion_id = models.AutoField(primary_key=True)
    ocrname = models.CharField(max_length=255, default='')
    name = models.CharField(max_length=255, default='')
    faction = models.SmallIntegerField(choices=FACTION_CHOICES, default=0)
    attack = models.SmallIntegerField(default=0)
    health = models.SmallIntegerField(default=0)
    desc = models.CharField(max_length=255, default='')
    image = models.CharField(max_length=255, default='')
    stars = models.SmallIntegerField(default=0)
    features = models.ManyToManyField('FeatureModel', related_name='minions', blank=True, null=True)
    is_valid = models.SmallIntegerField(choices=VALID_CHOICES, default=1)
    is_checked = models.SmallIntegerField(choices=CHECKED_CHOICES, default=-1)

    @classmethod
    def generate_combinations_and_offsets(cls, factions):
        """
        Generate all possible combinations and offsets for given factions.

        :param factions: List of integers representing factions.
        :return: A dictionary with string formatted combinations as keys and offsets as values.
        """
        faction_combinations = chain.from_iterable(combinations(factions, r) for r in range(1, len(factions) + 1))
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
    Model representing a feature that can be associated with minions.

    Fields:
    - feature: A code representing the feature.
    - functional: A description of the functionality of the feature.
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
    formation_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, default='')
    factions = models.IntegerField(default=0)
    search_minion = models.TextField(default='')

    class Meta:
        db_table = 'fmn_formation'


class PositionModel(models.Model):
    """
    Represents a specific position within a formation.

    Each formation have 6 positions.
    """

    # Unique ID for the position
    position_id = models.AutoField(primary_key=True)

    # A foreign key linking to the FormationModel, representing the formation this position belongs to
    formation = models.ForeignKey(FormationModel, on_delete=models.CASCADE)

    # Represents the position number (e.g., 1-6) within a formation
    position_number = models.PositiveIntegerField()

    # Many-to-many relationship: One position can be associated with multiple minions
    minions = models.ManyToManyField('MinionModel')

    # Many-to-many relationship: One position can be associated with multiple equipments
    equipments = models.ManyToManyField('EquipmentModel')

    class Meta:
        db_table = 'fmn_position'

        # Ensures that each position number is unique within a specific formation
        unique_together = ['formation', 'position_number']


class EquipmentModel(models.Model):
    """
    Represents an equipment item.

    Each equipment has a name, description, star rating, and can be associated with multiple features.
    Equipment can also be flagged as valid/invalid and checked/unchecked.
    """

    # Unique ID for the equipment
    equipment_id = models.AutoField(primary_key=True)

    # Name of the equipment
    name = models.CharField(max_length=255, default='')
    ocrname = models.CharField(max_length=255, default='')

    # Description of the equipment
    desc = models.CharField(max_length=255, default='')

    # Star rating of the equipment (e.g., 2 stars)
    stars = models.SmallIntegerField(default=2)

    # Many-to-many relationship: An equipment item can be associated with multiple features
    features = models.ManyToManyField('FeatureModel', related_name='equipment')

    # Image associated with the equipment
    image = models.CharField(max_length=255, default='')

    # Flag to indicate if the equipment is valid (1) or invalid (-1)
    is_valid = models.SmallIntegerField(choices=VALID_CHOICES, default=1)

    # Flag to indicate if the equipment has been checked (1) or unchecked (-1)
    is_checked = models.SmallIntegerField(choices=CHECKED_CHOICES, default=-1)

    class Meta:
        db_table = 'fmn_equipment'
