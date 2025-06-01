import os
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from rest_framework import status

logger = logging.getLogger(__name__)

class LocalFileUploadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        logger.info(f"📤 开始处理项目 {project_id} 的文件上传")
        logger.info(f"📤 接收到的文件keys: {list(request.FILES.keys())}")
        logger.info(f"📤 文件总数: {len(request.FILES)}")
        
        # 1. 检查环境变量
        root = os.environ.get("LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT")
        if not root:
            return Response({"error": "LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT not set"}, status=500)
        # 2. 目标目录
        target_dir = os.path.join(root, str(project_id))
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"📤 目标目录: {target_dir}")
        
        # 3. 保存文件
        uploaded_files = []
        
        for file_key, file in request.FILES.items():
            logger.info(f"📤 处理文件: {file_key} -> {file.name}")
            hash_filename = file.name  # 前端已经生成hash文件名
            save_path = os.path.join(target_dir, hash_filename)
            
            # 防止目录穿越
            if not os.path.abspath(save_path).startswith(os.path.abspath(target_dir)):
                logger.error(f"📤 非法文件名: {hash_filename}")
                return Response({"error": "Invalid filename"}, status=400)
            
            # 检查文件是否已存在（去重）
            if os.path.exists(save_path):
                logger.info(f"📤 文件已存在，跳过上传: {hash_filename}")
            else:
                # 保存文件
                with open(save_path, "wb") as f:
                    for chunk in file.chunks():
                        f.write(chunk)
                logger.info(f"📤 文件保存成功: {hash_filename}")
            
            uploaded_files.append(hash_filename)
        
        logger.info(f"📤 所有文件上传完成，共 {len(uploaded_files)} 个文件")
        return JsonResponse({"files": uploaded_files}) 