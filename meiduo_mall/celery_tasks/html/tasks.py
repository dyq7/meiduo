from celery_tasks.main import app
from django.template import loader
from django.conf import settings
import os

from goods.models import SKU
from goods.utils import get_categories


@app.task(name='generate_static_sku_detail_html')
def  generate_static_sku_detail_html(sku_id):
    #生成静态商品详情页面

    #商品分类菜单
    categories=get_categories()

    #获取当前sku的信息
    sku=SKU.objects.get(id=sku_id)
    sku.images=sku.skuimage_set.all()

    #导航信息 频道
    goods=sku.goods
    goods.channel=goods.category1.goodschannel_set.all()[0]

    sku_specs =sku.skuspecification_set.order_by('spec_id')
    sku_key=[]
    for spec in sku_specs:
        sku_key.append(spec.option.id)

    skus=goods.sku_set.all()

    spec_sku_map = {}

    for s in skus:
        s_specs=s.skuspecification_set.order_by('spec_id')

        key = []
        for spec in s_specs:
            key.append(spec.option.id)
        # 向规格参数-sku字典添加记录
        spec_sku_map[tuple(key)] = s.id
    specs = goods.goodsspecification_set.order_by('id')

    # 若当前sku的规格信息不完整，则不再继续
    if len(sku_key) < len(specs):
        return
    for index, spec in enumerate(specs):
        # 复制当前sku的规格键
        key = sku_key[:]
        # 该规格的选项
        options = spec.specificationoption_set.all()
        for option in options:
            # 在规格参数sku字典中查找符合当前规格的sku
            key[index] = option.id
            option.sku_id = spec_sku_map.get(tuple(key))

        spec.options = options

    # 渲染模板，生成静态html文件
    context = {
        'categories': categories,
        'goods': goods,
        'specs': specs,
        'sku': sku
    }

    template = loader.get_template('detail.html')
    html_text = template.render(context)
    file_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'goods/'+str(sku_id)+'.html')
    with open(file_path, 'w') as f:
        f.write(html_text)