from django.db import models

INITIALED_CHOICES = [
    (-1, 'Uninitialized'),
    (0, 'Initializing'),
    (1, 'Initialed'),
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
    is_valid = models.SmallIntegerField(default=1)
    # 1=initialed, -1=uninitialed
    is_initialed = models.SmallIntegerField(choices=INITIALED_CHOICES, default=-1)

    def __str__(self):
        return self.file_path


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
    faction = models.CharField(max_length=255, default='')
    attack = models.SmallIntegerField(default=0)
    health = models.SmallIntegerField(default=0)
    desc = models.CharField(max_length=255,default='')
    image = models.CharField(max_length=255, default='')
    stars = models.SmallIntegerField(default=0)
    features = models.ManyToManyField('FeatureModel', related_name='minions')

    # 1=valid, -1=invalid
    is_valid = models.SmallIntegerField(default=1)
    # 1=checked, -1=unchecked
    is_checked = models.SmallIntegerField(default=-1)

    def __str__(self):
        return self.name


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
