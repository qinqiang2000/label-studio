# 字段级备注功能实现指南

## 概述

字段级备注功能允许用户为JSON格式任务数据的每个字段添加错误类型标记和备注说明。本指南详细描述了该功能的完整实现架构和数据流。

## 功能特性

- ✅ 为JSON字段添加错误类型标记（缺失、错误、不确定、其他）
- ✅ 为每个字段添加详细备注说明
- ✅ 支持已提交和未提交任务的字段备注
- ✅ 字段备注在submit/update后正确保持
- ✅ 支持draft保存和版本切换
- ✅ 实时保存和乐观更新UI

## 核心架构

### 1. 数据存储结构

#### 前端MST Store
```javascript
// Annotation.js
field_annotations: types.optional(types.frozen(), {}),

// 数据结构示例
field_annotations: {
  "field_name": {
    errorTypes: ["缺失", "错误"],
    reason: "字段值不符合预期格式"
  }
}
```

#### 后端数据库
```python
# models.py
class Annotation(models.Model):
    field_annotations = models.JSONField(default=dict, blank=True)

class AnnotationDraft(models.Model):
    field_annotations = models.JSONField(default=dict, blank=True)
```

### 2. 数据流架构

#### Submit/Update完整数据流
```
用户填写字段备注
    ↓
MST Actions更新annotation.field_annotations
    ↓
serializeAnnotation()包装到result[0].meta.field_annotations
    ↓
后端Serializer提取并保存到数据库field_annotations字段
    ↓
后端to_representation()重新包装到result[0].meta.field_annotations
    ↓
前端deserializeResults()从meta中提取并恢复到MST
    ↓
字段备注正确显示
```

#### 数据导出完整流程
```
数据库中的annotation.field_annotations字段
    ↓
后端序列化器包装到result[0].meta.field_annotations
    ↓
导出API返回包含字段备注的JSON数据
    ↓
extract_valid_text()从result[0].meta中提取字段备注
    ↓
process_text_data()将字段备注映射到Excel列
    ↓
Excel文件中的_err和_note列显示字段备注
```

## 关键文件和实现

### 1. 前端核心文件

#### `/web/libs/editor/src/stores/Annotation/Annotation.js`

**MST字段定义**：
```javascript
field_annotations: types.optional(types.frozen(), {}),
```

**MST Actions**：
```javascript
// 字段备注更新actions
setFieldAnnotations(annotations) {
  self.field_annotations = annotations || {};
},

updateFieldAnnotation(fieldKey, annotation) {
  self.field_annotations = {
    ...self.field_annotations,
    [fieldKey]: annotation
  };
},
```

**序列化方法**：
```javascript
serializeAnnotation(options) {
  const result = self.results.map((r) => r.serialize(options))...;
  
  // 包含字段备注数据到序列化结果中
  if (self.field_annotations && Object.keys(self.field_annotations).length > 0) {
    if (result.length > 0) {
      if (!result[0].meta) {
        result[0].meta = {};
      }
      result[0].meta.field_annotations = self.field_annotations;
    } else {
      // 创建专门的字段备注result
      result.push({
        id: guidGenerator(),
        from_name: "__field_annotations__",
        to_name: "__field_annotations__",
        type: "field_annotations",
        value: {},
        meta: { field_annotations: self.field_annotations }
      });
    }
  }
  
  return result;
}
```

**反序列化方法**：
```javascript
deserializeResults(json, options) {
  // 从反序列化数据中恢复字段备注
  let recoveredFieldAnnotations = {};
  objAnnotation.forEach((obj) => {
    // 检查meta中是否包含字段备注
    if (obj.meta && obj.meta.field_annotations) {
      recoveredFieldAnnotations = { ...recoveredFieldAnnotations, ...obj.meta.field_annotations };
    }
    // 检查专门存储字段备注的result
    if (obj.type === "field_annotations" && obj.meta && obj.meta.field_annotations) {
      recoveredFieldAnnotations = { ...recoveredFieldAnnotations, ...obj.meta.field_annotations };
    }
  });

  // 使用action设置恢复的字段备注
  if (Object.keys(recoveredFieldAnnotations).length > 0) {
    self.setFieldAnnotations(recoveredFieldAnnotations);
  }
}
```

#### `/web/libs/editor/src/tags/control/TextArea/TextArea.jsx`

**UI组件和保存逻辑**：
```javascript
// 字段备注状态管理
const [fieldAnnotations, setFieldAnnotations] = useState({});

// 保存字段备注到MST
const handleSaveFieldAnnotation = useCallback(async () => {
  // 构建更新后的字段备注数据
  const updatedAnnotations = {
    ...fieldAnnotations,
    [currentFieldKey]: finalAnnotation,
  };

  // 使用MST action更新
  annotation.setFieldAnnotations(updatedAnnotations);
  
  // 智能保存到后端draft
  const response = await fetch(`/api/drafts/${draftId}`, {
    method: 'PATCH',
    body: JSON.stringify({
      field_annotations: updatedAnnotations
    })
  });
}, [annotation, fieldAnnotations]);
```

### 2. 后端核心文件

#### `/label_studio/tasks/serializers.py`

**AnnotationSerializer**：
```python
def create(self, validated_data):
    # 从result数据中提取field_annotations
    result_data = validated_data.get('result', [])
    field_annotations = {}
    
    if result_data and isinstance(result_data, list):
        for result_item in result_data:
            if isinstance(result_item, dict):
                if 'meta' in result_item and isinstance(result_item['meta'], dict):
                    if 'field_annotations' in result_item['meta']:
                        field_annotations.update(result_item['meta']['field_annotations'])
    
    # 保存到validated_data中
    if field_annotations:
        validated_data['field_annotations'] = field_annotations
    
    return super().create(validated_data)

def to_representation(self, instance):
    """将field_annotations重新包装到result.meta中"""
    data = super().to_representation(instance)
    
    # 如果annotation有field_annotations数据，需要将其包装到result的meta中
    if hasattr(instance, 'field_annotations') and instance.field_annotations:
        result_data = data.get('result', [])
        
        if result_data and isinstance(result_data, list) and len(result_data) > 0:
            # 将字段备注添加到第一个result的meta中
            if 'meta' not in result_data[0]:
                result_data[0]['meta'] = {}
            
            result_data[0]['meta']['field_annotations'] = instance.field_annotations
        else:
            # 创建专门用于存储字段备注的result
            result_data.append({
                'id': f'field_annotations_{instance.id}',
                'from_name': '__field_annotations__',
                'to_name': '__field_annotations__',
                'type': 'field_annotations',
                'value': {},
                'meta': {
                    'field_annotations': instance.field_annotations
                }
            })
        
        data['result'] = result_data
    
    return data
```

**AnnotationDraftSerializer同样的逻辑**。

### 3. 数据导出核心文件

#### `/label_studio/data_export/ext_export.py`

**导出格式扩展和集成**：
```python
# 扩展 Format 枚举，添加自定义导出格式
PIAOZONE_EXCEL = 'PIAOZONE_EXCEL'
extend_enum(Format, PIAOZONE_EXCEL, 1000)

# 注册自定义导出格式信息
Converter._FORMAT_INFO[getattr(Format, PIAOZONE_EXCEL)] = {
    "title": PIAOZONE_EXCEL,
    "description": "发票云自定义的Excel导出格式，方便做线下标注",
    "link": f"https://yourdoc.com/{PIAOZONE_EXCEL}",
}

# monkey patch convert 方法，处理自定义格式
def new_convert(self, input_data, output_data, format, is_dir=True, **kwargs):
    if format == getattr(Format, PIAOZONE_EXCEL):
        export_to_excel(input_data, output_data)
        return
    return old_convert(self, input_data, output_data, format, is_dir, **kwargs)
```

#### `/label_studio/data_export/ext_export_converter.py`

**字段备注提取逻辑**：
```python
def extract_valid_text(items_list):
    """
    从annotations或predictions中提取有效的JSON文本、字段备注和任务备注
    :return: (有效的JSON文本, 字段备注, 任务备注)
    """
    invoices_json_text = "[]"
    field_annotations = {}
    task_comment = ""
    
    for item in items_list:
        if "result" in item and item["result"]:
            for result_item in item["result"]:
                # 处理 invoices_json 数据时提取字段备注
                if from_name == "invoices_json" and "text" in value:
                    # 提取字段备注 - 从result的meta字段中获取
                    field_annotations = result_item.get("meta", {}).get("field_annotations", {})
    
    return invoices_json_text, field_annotations, task_comment
```

**Excel字段备注处理逻辑**：
```python
def process_text_data(text, field_annotations, worksheet, start_row, ...):
    """
    将字段备注填入对应的_err和_note列
    """
    # 处理每个动态字段及其备注列
    for field_name in dynamic_field_names:
        # 处理该字段的备注信息
        annotation_key = f"ticket_{ticket_index}_{field_name}"
        if annotation_key in field_annotations:
            annotation = field_annotations[annotation_key]
            
            # 填入错误类型到_err列
            if annotation.get("errorTypes"):
                error_types = annotation["errorTypes"]
                if isinstance(error_types, list):
                    error_value = "; ".join(error_types)
                worksheet.cell(row=current_row, column=col_idx + 1, value=error_value)
            
            # 填入原因到_note列
            if annotation.get("reason"):
                worksheet.cell(row=current_row, column=col_idx + 2, value=annotation["reason"])
```

**Excel文件结构**：
- **Annotations工作表**：包含字段备注列(`field_err`, `field_note`)和任务备注列(`task_comment`)
- **Predictions工作表**：仅包含基础字段，不包含备注列
- **列命名规则**：`{field_name}`, `{field_name}_err`, `{field_name}_note`
- **字段备注键格式**：`ticket_{index}_{field_name}`

### 4. 数据库迁移

#### `/label_studio/tasks/migrations/0058_add_field_annotations_to_annotation.py`
```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0057_previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='annotation',
            name='field_annotations',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
```

#### `/label_studio/tasks/migrations/0059_add_field_annotations_to_annotation_draft.py`
```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0058_add_field_annotations_to_annotation'),
    ]

    operations = [
        migrations.AddField(
            model_name='annotationdraft',
            name='field_annotations',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
```

## 部署和升级指南

### 1. 新环境部署步骤

#### 步骤1：代码部署
```bash
# 1. 更新代码库
git pull origin your-branch

# 2. 安装/更新Python依赖
poetry install

# 3. 构建前端
cd web
yarn install
yarn ls:build
cd ..
```

#### 步骤2：数据库迁移（⚠️ 关键步骤）
```bash
# 1. 加载环境变量
source .env

# 2. 检查迁移状态
poetry run python label_studio/manage.py showmigrations tasks

# 3. 执行数据库迁移
poetry run python label_studio/manage.py migrate

# 4. 验证迁移结果
poetry run python label_studio/manage.py showmigrations tasks
```

#### 步骤3：验证部署
```bash
# 1. 检查系统配置
poetry run python label_studio/manage.py check

# 2. 启动服务
poetry run python label_studio/manage.py runserver

# 3. 测试字段备注功能
# - 创建新任务
# - 添加字段备注
# - Submit/Update验证数据持久化
# - 测试导出功能（Excel格式包含字段备注）
```

### 2. 现有环境升级步骤

#### 升级前检查
```bash
# 1. 备份数据库
# 根据使用的数据库类型进行备份
# PostgreSQL: pg_dump
# MySQL: mysqldump  
# SQLite: 复制db.sqlite3文件

# 2. 检查当前迁移状态
poetry run python label_studio/manage.py showmigrations tasks

# 3. 确认服务状态
poetry run python label_studio/manage.py check
```

#### 执行升级
```bash
# 1. 停止服务
# 根据部署方式停止Label Studio服务

# 2. 更新代码
git pull origin your-branch

# 3. 更新依赖
poetry install

# 4. 执行数据库迁移 ⚠️
poetry run python label_studio/manage.py migrate

# 5. 构建前端
cd web && yarn ls:build && cd ..

# 6. 重启服务
# 根据部署方式重启Label Studio服务
```

### 3. 迁移验证

#### 验证迁移成功
```bash
# 1. 检查迁移状态
poetry run python label_studio/manage.py showmigrations tasks
# 应该看到0058和0059迁移已应用 [X]

# 2. 验证数据表结构
poetry run python label_studio/manage.py dbshell
# 执行: \d tasks_annotation (PostgreSQL) 或 DESCRIBE tasks_annotation (MySQL)
# 应该看到field_annotations字段

# 3. Python验证
poetry run python label_studio/manage.py shell
>>> from tasks.models import Annotation, AnnotationDraft
>>> Annotation._meta.get_field('field_annotations')
>>> AnnotationDraft._meta.get_field('field_annotations')
```

#### 功能验证
1. **创建新任务**：验证字段备注UI显示正常
2. **添加备注**：测试字段备注保存功能
3. **Submit/Update**：确认备注数据不丢失
4. **页面刷新**：验证备注数据持久化
5. **导出功能验证**：
   - 导出Excel格式，检查`_err`和`_note`列是否包含字段备注
   - 验证字段备注键格式：`ticket_{index}_{field_name}`
   - 确认Annotations工作表包含备注列，Predictions工作表不包含

### 4. 回滚方案（紧急情况）

#### 数据库回滚
```bash
# 1. 停止服务

# 2. 回滚数据库迁移
poetry run python label_studio/manage.py migrate tasks 0057

# 3. 恢复旧版本代码
git checkout previous-commit

# 4. 重启服务
```

#### 注意事项
- ⚠️ 回滚会丢失所有字段备注数据
- 建议先备份包含字段备注的annotation数据
- 考虑将字段备注导出为JSON格式保存

### 5. 生产环境最佳实践

#### 部署前准备
```bash
# 1. 在测试环境完整测试
# 2. 准备回滚计划
# 3. 通知用户维护窗口
# 4. 完整备份生产数据库
```

#### 部署时机
- 选择系统使用率低的时间窗口
- 准备足够的维护时间
- 确保技术团队在线支持

#### 监控检查
- 数据库连接正常
- API响应时间正常  
- 前端功能正常加载
- 错误日志监控

## 关键实现要点

### 1. MST State Tree保护规则
- ❌ 直接赋值：`annotation.field_annotations = value`
- ✅ 使用Actions：`annotation.setFieldAnnotations(value)`

### 2. 数据一致性保证
- 前端MST中存储在`annotation.field_annotations`
- 序列化时包装到`result[0].meta.field_annotations`
- 后端提取并存储到数据库`field_annotations`字段
- 后端输出时重新包装到`result[0].meta.field_annotations`
- 前端反序列化时从meta中恢复

### 3. Draft处理策略
- 智能draft创建：先尝试直接保存，失败则创建draft
- 乐观更新：先更新UI，后台异步保存
- 预优化：提前创建draft提升保存速度

### 4. 错误处理
- 前端静默处理API错误，不影响用户体验
- 保存失败时恢复UI状态
- 提供视觉反馈（保存成功/失败提示）

## 调试和排查

### 常见问题
1. **字段备注丢失**：检查`to_representation`方法是否正确包装
2. **MST保护错误**：确保使用Actions而非直接赋值
3. **Draft保存失败**：检查CSRF token和API权限
4. **序列化问题**：检查`field_annotations`字段类型
5. **导出功能问题**：
   - 检查`extract_valid_text`函数是否正确提取字段备注
   - 验证Excel文件中`_err`和`_note`列是否正确填充
   - 确认字段备注键格式匹配：`ticket_{index}_{field_name}`

### 调试日志
- 前端：搜索`[AnnotationSerializer]`、`[DeserializeResults]`
- 后端：查看Django日志中的序列化器输出
- 导出：检查`extract_valid_text`和`process_text_data`函数输出

## 扩展指南

### 添加新的错误类型
1. 修改前端错误类型常量
2. 更新UI选择器组件
3. 后端无需修改（使用JSON存储）

### 支持其他控件类型
1. 复制TextArea的字段备注逻辑
2. 适配对应控件的数据结构
3. 确保MST Actions的一致性

### 性能优化
1. 实现字段备注的批量保存
2. 优化draft创建时机
3. 添加更智能的缓存策略

## 版本兼容性

该实现向后兼容，支持：
- 没有字段备注的旧数据
- 老版本客户端（忽略字段备注数据）
- 混合使用新旧功能的环境

---

*最后更新：2025-08-06*
*版本：v1.0*