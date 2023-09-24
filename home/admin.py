from django.contrib import admin
from home.models import MinionModel
from django.utils.html import format_html
from django.db.models import Count


# Register your models here.


class DuplicatesFilter(admin.SimpleListFilter):
    title = 'duplicates'  # 过滤器的显示名称
    parameter_name = 'duplicates'  # URL中使用的参数名称

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Show Duplicates'),  # ('值', '显示名称')
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            # 首先找出重复的名字
            duplicate_names_subquery = (
                queryset
                .values('name')  # 对'name'字段进行分组
                .annotate(name_count=Count('name'))  # 计算每个'name'的数量
                .filter(name_count__gt=1, is_valid=1)  # 过滤出数量大于1的
            )

            # 提取所有重复的name
            duplicate_names = [item['name'] for item in duplicate_names_subquery]

            # 然后，过滤出原始queryset中'name'在duplicate_names中的对象
            return queryset.filter(name__in=duplicate_names)


class MinionAdmin(admin.ModelAdmin):
    list_display = ('display_image_list', 'display_features','stars', 'faction', 'is_checked')
    readonly_fields = ['display_image']  # 图像显示字段设为只读
    list_filter = ['is_checked', 'is_valid', DuplicatesFilter , 'faction']
    search_fields = ['name', 'desc']
    list_per_page = 20

    def make_checked(modeladmin, request, queryset):
        queryset.update(is_checked=1)

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Check Duplicates'),  # ('值', '显示名称')

        )

    def get_queryset(self, request):
        """重写以默认只包含is_valid为1的对象"""
        qs = super().get_queryset(request)
        is_valid = request.GET.get('is_valid__exact', 1)
        data = qs.filter(is_valid=is_valid)

        return data

    # 列表显示的图像
    def display_image_list(self, obj):
        return format_html('<img src="/{}" width="180" />', obj.image)

    display_image_list.short_description = 'Image'

    # 表单显示的图像
    def display_image(self, obj):
        if obj.image:
            return format_html(
                '<div style="position: fixed; right: 240px; top: 140px;"><img src="/{}" width="300" /></div>',
                obj.image)
        return ''

    def display_features(self, obj):
        result = format_html('<b>{}</b>', obj.name)  # name 是 bold 格式并且在新的一行
        fs = obj.features.all()
        if fs:
            features_str = format_html(','.join([feature.feature for feature in fs]))  # 每个 feature 在新的一行
            result += format_html('({})', features_str)  # 括号里的内容在新的一行
        result += format_html('<br>[ {} / {} ]', obj.attack, obj.health)  # 括号里的内容在新的一行
        result += format_html('<br><span>{}</span>', obj.desc)  # desc 是 italic 格式
        return result

    display_image.short_description = 'Image'
    display_features.short_description = 'Info'
    actions = [make_checked]


admin.site.register(MinionModel, MinionAdmin)
