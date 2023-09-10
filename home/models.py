from django.db import models


class ImageModel(models.Model):
    image_id = models.AutoField(primary_key=True)
    file_path = models.CharField(max_length=255, unique=True)
    alias = models.CharField(max_length=255)
    # 1=valid, -1=invalid
    is_valid = models.SmallIntegerField(default=1)

    def __str__(self):
        return self.file_path
