/**
 * 字段备注API工具类的单元测试
 */

// Mock fetch API
global.fetch = jest.fn();

// Mock EvaluationConfigAPI
const mockEvaluationConfigAPI = {
  createHeaders: jest.fn(() => ({
    'Content-Type': 'application/json',
    'Authorization': 'Token test-token'
  }))
};

// Mock the import
jest.mock('../../../utils/api', () => ({
  EvaluationConfigAPI: mockEvaluationConfigAPI
}));

// 导入要测试的类
import { FieldAnnotationAPI } from '../TextArea';

describe('FieldAnnotationAPI', () => {
  beforeEach(() => {
    // 清除所有mock的状态
    fetch.mockClear();
    mockEvaluationConfigAPI.createHeaders.mockClear();
    
    // Mock console methods
    global.console = {
      ...console,
      log: jest.fn(),
      error: jest.fn()
    };
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('saveFieldAnnotations', () => {
    const annotationId = 123;
    const testFieldAnnotations = {
      textarea1: {
        errorTypes: ['spelling_error'],
        reason: 'Test reason'
      }
    };

    it('should successfully save field annotations', async () => {
      // Mock成功的响应
      const mockResponse = {
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({
          field_annotations: testFieldAnnotations
        })
      };
      fetch.mockResolvedValue(mockResponse);

      const result = await FieldAnnotationAPI.saveFieldAnnotations(annotationId, testFieldAnnotations);

      // 验证请求参数
      expect(fetch).toHaveBeenCalledWith(
        `/api/annotations/${annotationId}/field-annotations/`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Token test-token'
          },
          body: JSON.stringify({ field_annotations: testFieldAnnotations })
        }
      );

      // 验证结果
      expect(result.success).toBe(true);
      expect(result.data.field_annotations).toEqual(testFieldAnnotations);
      expect(console.log).toHaveBeenCalledWith('🔄 [API] 开始保存字段备注到服务器');
      expect(console.log).toHaveBeenCalledWith('✅ [API] 字段备注保存成功:', expect.any(Object));
    });

    it('should handle HTTP error responses', async () => {
      // Mock HTTP错误响应
      const mockResponse = {
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: jest.fn().mockResolvedValue('Invalid data')
      };
      fetch.mockResolvedValue(mockResponse);

      const result = await FieldAnnotationAPI.saveFieldAnnotations(annotationId, testFieldAnnotations);

      // 验证错误处理
      expect(result.success).toBe(false);
      expect(result.error).toBe('HTTP 400: Bad Request - Invalid data');
      expect(console.error).toHaveBeenCalledWith('❌ [API] 字段备注保存失败:', expect.any(Error));
    });

    it('should handle network errors', async () => {
      // Mock网络错误
      const networkError = new Error('Network error');
      fetch.mockRejectedValue(networkError);

      const result = await FieldAnnotationAPI.saveFieldAnnotations(annotationId, testFieldAnnotations);

      // 验证错误处理
      expect(result.success).toBe(false);
      expect(result.error).toBe('Network error');
      expect(console.error).toHaveBeenCalledWith('❌ [API] 字段备注保存失败:', networkError);
    });

    it('should handle response.json() errors', async () => {
      // Mock成功响应但JSON解析失败
      const mockResponse = {
        ok: true,
        status: 200,
        json: jest.fn().mockRejectedValue(new Error('JSON parse error'))
      };
      fetch.mockResolvedValue(mockResponse);

      const result = await FieldAnnotationAPI.saveFieldAnnotations(annotationId, testFieldAnnotations);

      // 验证错误处理
      expect(result.success).toBe(false);
      expect(result.error).toBe('JSON parse error');
    });

    it('should create correct headers using EvaluationConfigAPI', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({})
      };
      fetch.mockResolvedValue(mockResponse);

      await FieldAnnotationAPI.saveFieldAnnotations(annotationId, testFieldAnnotations);

      // 验证调用了EvaluationConfigAPI.createHeaders
      expect(mockEvaluationConfigAPI.createHeaders).toHaveBeenCalled();
    });

    it('should handle empty field annotations', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({ field_annotations: {} })
      };
      fetch.mockResolvedValue(mockResponse);

      const result = await FieldAnnotationAPI.saveFieldAnnotations(annotationId, {});

      expect(result.success).toBe(true);
      expect(result.data.field_annotations).toEqual({});
    });

    it('should handle complex field annotations data', async () => {
      const complexFieldAnnotations = {
        textarea1: {
          errorTypes: ['spelling_error', 'grammar_error'],
          reason: 'Multiple issues found',
          severity: 'high',
          suggestions: ['suggestion1', 'suggestion2']
        },
        textarea2: {
          errorTypes: ['format_error'],
          reason: 'Format needs adjustment',
          metadata: {
            reviewer: 'test_reviewer',
            timestamp: '2023-01-01T00:00:00Z'
          }
        }
      };

      const mockResponse = {
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({ field_annotations: complexFieldAnnotations })
      };
      fetch.mockResolvedValue(mockResponse);

      const result = await FieldAnnotationAPI.saveFieldAnnotations(annotationId, complexFieldAnnotations);

      expect(result.success).toBe(true);
      expect(result.data.field_annotations).toEqual(complexFieldAnnotations);

      // 验证请求体包含完整的复杂数据
      const expectedBody = JSON.stringify({ field_annotations: complexFieldAnnotations });
      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expectedBody
        })
      );
    });
  });

  describe('loadFieldAnnotations', () => {
    const annotationId = 123;

    it('should successfully load field annotations', async () => {
      const testFieldAnnotations = {
        textarea1: {
          errorTypes: ['spelling_error'],
          reason: 'Test reason'
        }
      };

      const mockResponse = {
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({
          field_annotations: testFieldAnnotations
        })
      };
      fetch.mockResolvedValue(mockResponse);

      const result = await FieldAnnotationAPI.loadFieldAnnotations(annotationId);

      // 验证请求参数
      expect(fetch).toHaveBeenCalledWith(
        `/api/annotations/${annotationId}/field-annotations/`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Token test-token'
          }
        }
      );

      // 验证结果
      expect(result.success).toBe(true);
      expect(result.data.field_annotations).toEqual(testFieldAnnotations);
    });

    it('should handle empty field annotations', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        json: jest.fn().mockResolvedValue({ field_annotations: {} })
      };
      fetch.mockResolvedValue(mockResponse);

      const result = await FieldAnnotationAPI.loadFieldAnnotations(annotationId);

      expect(result.success).toBe(true);
      expect(result.data.field_annotations).toEqual({});
    });

    it('should handle 404 errors', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: jest.fn().mockResolvedValue('Annotation not found')
      };
      fetch.mockResolvedValue(mockResponse);

      const result = await FieldAnnotationAPI.loadFieldAnnotations(annotationId);

      expect(result.success).toBe(false);
      expect(result.error).toBe('HTTP 404: Not Found - Annotation not found');
    });
  });
});