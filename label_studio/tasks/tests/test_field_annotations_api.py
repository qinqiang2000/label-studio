"""
测试字段备注API功能
"""
import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from projects.models import Project
from tasks.models import Annotation, Task
from users.models import User


class FieldAnnotationsAPITestCase(APITestCase):
    """字段备注API测试用例"""

    def setUp(self):
        """测试前的设置"""
        # 创建用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 创建项目
        self.project = Project.objects.create(
            title='Test Project',
            created_by=self.user,
            label_config='<View><Text name="text" value="$text"/><TextArea name="textarea" toName="text"/></View>'
        )
        
        # 创建任务
        self.task = Task.objects.create(
            data={'text': 'Test text content'},
            project=self.project
        )
        
        # 创建标注
        self.annotation = Annotation.objects.create(
            task=self.task,
            project=self.project,
            completed_by=self.user,
            result=[]
        )
        
        # 设置身份验证
        self.client.force_authenticate(user=self.user)
        
        # API URL
        self.api_url = reverse('tasks:api-annotations:annotation-field-annotations', 
                             kwargs={'pk': self.annotation.pk})

    def test_get_empty_field_annotations(self):
        """测试获取空的字段备注"""
        response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'field_annotations': {}})

    def test_get_field_annotations_with_data(self):
        """测试获取包含数据的字段备注"""
        # 设置标注结果，包含字段备注
        field_annotations = {
            'textarea': {
                'errorTypes': ['spelling_error'],
                'reason': 'Test reason'
            }
        }
        
        self.annotation.result = [{
            'meta': {
                'field_annotations': field_annotations
            }
        }]
        self.annotation.save()
        
        response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['field_annotations'], field_annotations)

    def test_put_field_annotations_empty_result(self):
        """测试在空结果上保存字段备注"""
        field_annotations = {
            'textarea': {
                'errorTypes': ['grammar_error'],
                'reason': 'Grammar issue found'
            }
        }
        
        response = self.client.put(
            self.api_url,
            data={'field_annotations': field_annotations},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['field_annotations'], field_annotations)
        
        # 验证数据库中的保存
        self.annotation.refresh_from_db()
        self.assertEqual(len(self.annotation.result), 1)
        self.assertIn('meta', self.annotation.result[0])
        self.assertEqual(
            self.annotation.result[0]['meta']['field_annotations'],
            field_annotations
        )
        self.assertEqual(self.annotation.updated_by, self.user)

    def test_put_field_annotations_existing_result(self):
        """测试在现有结果上更新字段备注"""
        # 设置初始结果
        self.annotation.result = [{
            'type': 'textarea',
            'value': {'text': ['some text']},
            'meta': {
                'field_annotations': {
                    'old_field': {
                        'errorTypes': ['old_error'],
                        'reason': 'Old reason'
                    }
                }
            }
        }]
        self.annotation.save()
        
        # 更新字段备注
        new_field_annotations = {
            'textarea': {
                'errorTypes': ['new_error'],
                'reason': 'New reason'
            },
            'another_field': {
                'errorTypes': ['another_error'],
                'reason': 'Another reason'
            }
        }
        
        response = self.client.put(
            self.api_url,
            data={'field_annotations': new_field_annotations},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['field_annotations'], new_field_annotations)
        
        # 验证数据库中的更新
        self.annotation.refresh_from_db()
        self.assertEqual(
            self.annotation.result[0]['meta']['field_annotations'],
            new_field_annotations
        )

    def test_put_field_annotations_multiple_results(self):
        """测试在多个结果项中更新字段备注"""
        # 设置多个结果项
        self.annotation.result = [
            {
                'type': 'textarea',
                'value': {'text': ['first text']}
            },
            {
                'type': 'choice',
                'value': {'choices': ['option1']},
                'meta': {
                    'field_annotations': {
                        'old_field': {
                            'errorTypes': ['old_error'],
                            'reason': 'Old reason'
                        }
                    }
                }
            }
        ]
        self.annotation.save()
        
        # 更新字段备注
        new_field_annotations = {
            'textarea': {
                'errorTypes': ['updated_error'],
                'reason': 'Updated reason'
            }
        }
        
        response = self.client.put(
            self.api_url,
            data={'field_annotations': new_field_annotations},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证更新了包含meta的结果项
        self.annotation.refresh_from_db()
        self.assertEqual(
            self.annotation.result[1]['meta']['field_annotations'],
            new_field_annotations
        )

    def test_put_field_annotations_no_meta_result(self):
        """测试在没有meta的结果上保存字段备注"""
        # 设置没有meta的结果
        self.annotation.result = [
            {
                'type': 'textarea',
                'value': {'text': ['some text']}
            }
        ]
        self.annotation.save()
        
        field_annotations = {
            'textarea': {
                'errorTypes': ['new_error'],
                'reason': 'New reason'
            }
        }
        
        response = self.client.put(
            self.api_url,
            data={'field_annotations': field_annotations},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证创建了新的meta结果项
        self.annotation.refresh_from_db()
        self.assertEqual(len(self.annotation.result), 2)
        # 最后一个结果项应该包含meta
        self.assertEqual(
            self.annotation.result[1]['meta']['field_annotations'],
            field_annotations
        )

    def test_get_field_annotations_not_found(self):
        """测试获取不存在的标注的字段备注"""
        non_existent_url = reverse('tasks:api-annotations:annotation-field-annotations', 
                                 kwargs={'pk': 99999})
        
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_field_annotations_not_found(self):
        """测试更新不存在的标注的字段备注"""
        non_existent_url = reverse('tasks:api-annotations:annotation-field-annotations', 
                                 kwargs={'pk': 99999})
        
        response = self.client.put(
            non_existent_url,
            data={'field_annotations': {}},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthorized_access(self):
        """测试未授权访问"""
        self.client.force_authenticate(user=None)
        
        # GET请求
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # PUT请求
        response = self.client.put(
            self.api_url,
            data={'field_annotations': {}},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put_invalid_data(self):
        """测试使用无效数据更新字段备注"""
        # 测试缺少field_annotations字段
        response = self.client.put(
            self.api_url,
            data={},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['field_annotations'], {})

    def test_field_annotations_with_complex_data(self):
        """测试复杂字段备注数据的保存和获取"""
        complex_field_annotations = {
            'textarea1': {
                'errorTypes': ['spelling_error', 'grammar_error'],
                'reason': 'Multiple issues found in this field',
                'severity': 'high',
                'suggestions': ['suggestion1', 'suggestion2']
            },
            'textarea2': {
                'errorTypes': ['format_error'],
                'reason': 'Format needs adjustment',
                'severity': 'medium',
                'metadata': {
                    'reviewer': 'test_reviewer',
                    'timestamp': '2023-01-01T00:00:00Z'
                }
            }
        }
        
        # 保存复杂数据
        response = self.client.put(
            self.api_url,
            data={'field_annotations': complex_field_annotations},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['field_annotations'], complex_field_annotations)
        
        # 重新获取并验证
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['field_annotations'], complex_field_annotations)