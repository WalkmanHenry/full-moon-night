from django.contrib import admin
from home.models import MinionModel
from django.utils.html import format_html


# Register your models here.


class MinionAdmin(admin.ModelAdmin):
    list_display = ('display_image', 'name', 'faction', 'attack', 'health')

    def display_image(self, obj):
        return format_html( '<img src="/{}" width="200" />', obj.image)

    display_image.short_description = 'Image'


admin.site.register(MinionModel, MinionAdmin)
