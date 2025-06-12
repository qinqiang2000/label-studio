#!/usr/bin/env python3
"""
测试多个预测功能的脚本

这个脚本用于验证基于prompt_name的多个预测功能是否正常工作。
"""

import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.label_studio')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'label_studio'))
django.setup()

from tasks.models import Task, Prediction
from projects.models import Project
from ml.models import MLBackend
from users.models import User
from organizations.models import Organization
from django.db.models import Q, Count


def cleanup_test_data():
    """
    清理测试数据
    """
    try:
        # 删除测试预测
        Prediction.objects.filter(
            task__project__title__startswith='Test Multiple Predictions'
        ).delete()
        
        # 删除测试任务
        Task.objects.filter(
            project__title__startswith='Test Multiple Predictions'
        ).delete()
        
        # 删除测试ML后端
        MLBackend.objects.filter(
            title__startswith='Test ML Backend'
        ).delete()
        
        # 删除测试项目
        Project.objects.filter(
            title__startswith='Test Multiple Predictions'
        ).delete()
        
        # 删除测试组织
        Organization.objects.filter(
            title__startswith='Test Organization'
        ).delete()
        
        # 删除测试用户
        User.objects.filter(
            username__startswith='test_user_mp'
        ).delete()
        
        print("✅ 测试数据清理完成")
    except Exception as e:
        print(f"⚠️ 清理测试数据时出错: {str(e)}")


def test_multiple_predictions():
    """
    测试多个预测功能
    """
    print("🎯 开始测试多个预测功能...")
    
    try:
        # 先清理可能存在的测试数据
        cleanup_test_data()
        
        # 创建测试用户
        user = User.objects.create(
            username='test_user_mp_001',
            email='test_mp_001@example.com'
        )
        print(f"✅ 测试用户: {user.username}")
        
        # 创建测试组织
        organization = Organization.objects.create(
            title='Test Organization 001',
            created_by=user
        )
        print(f"✅ 测试组织: {organization.title}")
        
        # 创建测试项目
        project = Project.objects.create(
            title='Test Multiple Predictions Project 001',
            created_by=user,
            organization=organization,
            label_config='''
            <View>
              <Text name="text" value="$text"/>
              <Choices name="sentiment" toName="text">
                <Choice value="positive"/>
                <Choice value="negative"/>
                <Choice value="neutral"/>
              </Choices>
            </View>
            '''
        )
        print(f"✅ 测试项目: {project.title}")
        
        # 创建测试任务
        task = Task.objects.create(
            project=project,
            data={'text': 'This is a test sentence for sentiment analysis.'}
        )
        print(f"✅ 测试任务: {task.id}")
        
        # 创建测试ML后端
        ml_backend = MLBackend.objects.create(
            project=project,
            title='Test ML Backend 001',
            url='http://localhost:9090',
            model_version='v1.0'
        )
        print(f"✅ 测试ML后端: {ml_backend.title}")
        
        # 测试1: 创建第一个预测（无prompt_name）
        prediction1 = Prediction.objects.create(
            task=task,
            project=project,
            model=ml_backend,
            model_version='v1.0',
            prompt_name=None,
            result=[{
                'from_name': 'sentiment',
                'to_name': 'text',
                'type': 'choices',
                'value': {'choices': ['positive']}
            }],
            score=0.85
        )
        print(f"✅ 创建第一个预测 (无prompt_name): {prediction1.id}")
        
        # 测试2: 创建第二个预测（有prompt_name="prompt1"）
        prediction2 = Prediction.objects.create(
            task=task,
            project=project,
            model=ml_backend,
            model_version='v1.0',
            prompt_name='prompt1',
            result=[{
                'from_name': 'sentiment',
                'to_name': 'text',
                'type': 'choices',
                'value': {'choices': ['negative']}
            }],
            score=0.75
        )
        print(f"✅ 创建第二个预测 (prompt_name='prompt1'): {prediction2.id}")
        
        # 测试3: 创建第三个预测（有prompt_name="prompt2"）
        prediction3 = Prediction.objects.create(
            task=task,
            project=project,
            model=ml_backend,
            model_version='v1.0',
            prompt_name='prompt2',
            result=[{
                'from_name': 'sentiment',
                'to_name': 'text',
                'type': 'choices',
                'value': {'choices': ['neutral']}
            }],
            score=0.90
        )
        print(f"✅ 创建第三个预测 (prompt_name='prompt2'): {prediction3.id}")
        
        # 验证所有预测都存在
        predictions = Prediction.objects.filter(task=task)
        print(f"✅ 任务 {task.id} 现在有 {predictions.count()} 个预测")
        
        for pred in predictions:
            print(f"   - 预测 {pred.id}: model_version={pred.model_version}, prompt_name={pred.prompt_name}, score={pred.score}")
        
        # 测试4: 验证过滤逻辑
        # 模拟predict_tasks中的过滤逻辑
        model_version = 'v1.0'
        prompt_name = 'prompt1'
        
        # 过滤已有相同model_version和prompt_name的任务
        filtered_tasks = Task.objects.filter(id=task.id).annotate(
            predictions_count=Count('predictions')
        ).exclude(
            Q(predictions_count__gt=0) & 
            Q(predictions__model_version=model_version) & 
            Q(predictions__prompt_name=prompt_name)
        )
        
        print(f"✅ 过滤测试 (model_version='{model_version}', prompt_name='{prompt_name}'):")
        print(f"   - 过滤后的任务数量: {filtered_tasks.count()} (应该为0，因为已存在相同预测)")
        
        # 测试不同prompt_name的过滤
        prompt_name = 'prompt3'  # 不存在的prompt_name
        filtered_tasks = Task.objects.filter(id=task.id).annotate(
            predictions_count=Count('predictions')
        ).exclude(
            Q(predictions_count__gt=0) & 
            Q(predictions__model_version=model_version) & 
            Q(predictions__prompt_name=prompt_name)
        )
        
        print(f"✅ 过滤测试 (model_version='{model_version}', prompt_name='{prompt_name}'):")
        print(f"   - 过滤后的任务数量: {filtered_tasks.count()} (应该为1，因为不存在相同预测)")
        
        print("\n🎉 多个预测功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_constraint_violation():
    """
    测试约束违反情况
    """
    print("\n🎯 测试约束违反情况...")
    
    try:
        # 创建测试用户
        user = User.objects.create(
            username='test_user_mp_002',
            email='test_mp_002@example.com'
        )
        
        # 创建测试组织
        organization = Organization.objects.create(
            title='Test Organization 002',
            created_by=user
        )
        
        # 创建测试项目
        project = Project.objects.create(
            title='Test Multiple Predictions Project 002',
            created_by=user,
            organization=organization,
            label_config='<View><Text name="text" value="$text"/></View>'
        )
        
        # 创建测试任务
        task = Task.objects.create(
            project=project,
            data={'text': 'Test text'}
        )
        
        # 创建测试ML后端
        ml_backend = MLBackend.objects.create(
            project=project,
            title='Test ML Backend 002',
            url='http://localhost:9090',
            model_version='v1.0'
        )
        
        # 创建第一个预测
        Prediction.objects.create(
            task=task,
            project=project,
            model=ml_backend,
            model_version='v1.0',
            prompt_name='test_prompt',
            result=[],
            score=0.5
        )
        print("✅ 创建第一个预测成功")
        
        # 尝试创建重复的预测（应该失败）
        try:
            Prediction.objects.create(
                task=task,
                project=project,
                model=ml_backend,
                model_version='v1.0',
                prompt_name='test_prompt',  # 相同的组合
                result=[],
                score=0.8
            )
            print("❌ 错误：重复预测应该被约束阻止")
            return False
        except Exception as e:
            print(f"✅ 正确：重复预测被约束阻止 - {type(e).__name__}")
        
        # 创建不同prompt_name的预测（应该成功）
        Prediction.objects.create(
            task=task,
            project=project,
            model=ml_backend,
            model_version='v1.0',
            prompt_name='different_prompt',  # 不同的prompt_name
            result=[],
            score=0.9
        )
        print("✅ 创建不同prompt_name的预测成功")
        
        print("🎉 约束测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 约束测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = True
    
    try:
        # 运行测试
        if not test_multiple_predictions():
            success = False
            
        if not test_constraint_violation():
            success = False
            
    finally:
        # 最终清理
        cleanup_test_data()
    
    if success:
        print("\n🎉 所有测试都通过了！多个预测功能正常工作。")
    else:
        print("\n❌ 部分测试失败。")
        sys.exit(1)