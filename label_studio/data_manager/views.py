"""Data manager views"""
import os
import logging
from core.version import get_short_version
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse, Http404, FileResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@login_required
def task_page(request, pk):
    response = {'version': get_short_version()}
    return render(request, 'base.html', response)


@require_GET
@login_required
def download_excel_report(request):
    """下载Excel评估报告"""
    file_path = request.GET.get('path')
    
    if not file_path:
        logger.error("下载Excel报告时缺少文件路径参数")
        raise Http404("File path parameter is required")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        logger.error(f"Excel报告文件不存在: {file_path}")
        raise Http404("File was not available on the site")
    
    # 检查文件扩展名
    if not file_path.lower().endswith('.xlsx'):
        logger.error(f"无效的文件类型: {file_path}")
        raise Http404("Invalid file type")
    
    try:
        # 获取文件名
        filename = os.path.basename(file_path)
        
        # 返回文件响应
        response = FileResponse(
            open(file_path, 'rb'),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"成功下载Excel报告: {filename}")
        return response
        
    except Exception as e:
        logger.error(f"下载Excel报告时发生错误: {str(e)}")
        raise Http404("Error occurred while downloading the file")
