# 评估字段配置管理指引

## 功能概述

本文档详细说明如何管理Label Studio中文档评估功能的字段配置，包括添加、修改、删除字段以及部署注意事项。

## 技术架构

### 1. 配置存储结构

评估字段配置采用双层结构：

#### JSON配置文件 (主要配置源)
- 路径：`label_studio/evaluation_configs/config/`
- 文件：`invoice.json`, `bank_receipt.json`, `receipt.json`, `custom.json`
- 用途：定义各文档类型的字段、验证规则、显示属性等

#### 数据库配置 (运行时配置)
- 模型：`EvaluationFieldConfig`
- 用途：存储从JSON文件加载的配置，供API和前端使用
- 表：`evaluation_field_configs`

#### 前端硬编码配置 (兜底配置)
- 文件：`web/apps/labelstudio/src/components/EvaluationFieldsConfig/EvaluationFieldsConfig.jsx`
- 用途：当后端API失败时的兜底配置

### 2. 配置加载流程

```
JSON配置文件 → 管理命令加载 → 数据库 → API → 前端显示
     ↓
  兜底配置 ← ← ← ← ← API失败时 ← ← ← ← ← 前端
```

## 字段管理操作指引

### 增加新字段

#### 步骤1：修改JSON配置文件
```bash
# 编辑对应文档类型的配置文件
vim label_studio/evaluation_configs/config/invoice.json
```

在配置文件中添加字段：

```json
{
  "required_fields": [
    "docType",
    "invoiceDate", 
    "totalAmount",
    "currency",
    "billToName",
    "billFromName",  // 新增字段
    "totalTaxAmount"
  ],
  "field_display_properties": {
    "labels": {
      "billFromName": "Bill From Name"  // 新增显示标签
    },
    "types": {
      "billFromName": "string"  // 新增字段类型
    }
  }
}
```

#### 步骤2：更新前端兜底配置
```bash
# 编辑前端配置文件
vim web/apps/labelstudio/src/components/EvaluationFieldsConfig/EvaluationFieldsConfig.jsx
```

在3个位置添加新字段：
```javascript
// 第48行附近
fields: ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "billFromName", "totalTaxAmount"],

// 第72行附近  
fields: ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "billFromName", "totalTaxAmount"],

// 第93行附近
fields: ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "billFromName", "totalTaxAmount"],
```

#### 步骤3：重新加载配置到数据库
```bash
poetry run python label_studio/manage.py reload_configs --force
```

#### 步骤4：验证配置生效
```bash
# 验证API返回新字段
curl -s -H "Authorization: Token YOUR_TOKEN" \
  "http://127.0.0.1:8080/api/frontend/evaluation-configs/presets/" | \
  python -c "
import json, sys
data = json.load(sys.stdin)
invoice = data.get('invoice', {})
print('新字段在配置中:', 'billFromName' in invoice.get('fields', []))
"
```

### 修改现有字段

#### 移动字段位置（必需↔可选）
```json
// 从required_fields移动到optional_fields
{
  "required_fields": ["docType", "totalAmount"],  // 移除字段
  "optional_fields": ["billFromName"]             // 添加字段
}
```

#### 修改字段属性
```json
{
  "field_display_properties": {
    "labels": {
      "billFromName": "开票方名称"  // 修改显示标签
    },
    "types": {
      "billFromName": "text"      // 修改字段类型
    }
  }
}
```

### 删除字段

1. 从JSON配置的所有相关数组中移除字段
2. 删除display_properties中的相关配置
3. 更新前端兜底配置
4. 重新加载配置

### 新增文档类型

#### 步骤1：创建新配置文件
```bash
# 创建新文档类型配置
cat > label_studio/evaluation_configs/config/contract.json << 'EOF'
{
  "name": "Contract",
  "key": "contract", 
  "description": "合同文档评估配置",
  "required_fields": [
    "docType",
    "contractNumber",
    "contractDate",
    "partyA",
    "partyB"
  ],
  "optional_fields": [
    "contractAmount",
    "signDate"
  ],
  "field_display_properties": {
    "labels": {
      "docType": "Document Type",
      "contractNumber": "Contract Number", 
      "contractDate": "Contract Date",
      "partyA": "Party A",
      "partyB": "Party B",
      "contractAmount": "Contract Amount",
      "signDate": "Sign Date"
    },
    "types": {
      "docType": "string",
      "contractNumber": "string",
      "contractDate": "date", 
      "partyA": "string",
      "partyB": "string",
      "contractAmount": "number",
      "signDate": "date"
    }
  },
  "evaluation_settings": {
    "comparison_method": "field_by_field",
    "matching_strategy": {
      "type": "field_based",
      "primary_fields": ["contractNumber", "contractDate"]
    }
  }
}
EOF
```

#### 步骤2：更新前端配置
在`EvaluationFieldsConfig.jsx`中添加新文档类型的兜底配置。

#### 步骤3：加载配置
```bash
poetry run python label_studio/manage.py reload_configs --force
```

## 部署指引

### 部署到新环境

#### 1. 常规部署流程
```bash
# 1. 部署代码文件
git pull origin main

# 2. 安装依赖
poetry install

# 3. 重新加载评估配置 (关键步骤)
poetry run python label_studio/manage.py reload_configs --force

# 4. 重启服务
systemctl restart label-studio
```

#### 2. 环境差异处理

**首次部署到新环境:**
```bash
# 清除所有现有配置，重新加载
poetry run python label_studio/manage.py reload_configs --clear --force
```

**增量更新现有环境:**
```bash  
# 只更新变更的配置
poetry run python label_studio/manage.py reload_configs --force
```

#### 3. 验证部署成功
```bash
# 检查配置加载状态
poetry run python label_studio/manage.py reload_configs

# 验证API响应
curl -H "Authorization: Token YOUR_TOKEN" \
  "http://YOUR_DOMAIN/api/frontend/evaluation-configs/presets/"
```

### 配置文件修改清单

任何字段配置修改都需要变更以下文件：

1. **JSON配置文件**: `label_studio/evaluation_configs/config/*.json`
2. **前端兜底配置**: `web/apps/labelstudio/src/components/EvaluationFieldsConfig/EvaluationFieldsConfig.jsx`
3. **数据库配置**: 通过`reload_configs`命令更新

## 常见问题排查

### Q1: 前端显示的字段没有更新
**原因**: 可能API获取配置失败，使用了兜底配置
**解决**:
1. 检查后端API是否正常：`curl API_ENDPOINT`  
2. 检查数据库配置是否更新：`poetry run python label_studio/manage.py reload_configs`
3. 更新前端兜底配置

### Q2: 重新加载配置失败
**原因**: JSON配置文件格式错误
**解决**:
1. 检查JSON语法：`python -m json.tool config_file.json`
2. 检查必需字段是否缺失
3. 查看错误日志：`poetry run python label_studio/manage.py reload_configs --force`

### Q3: 评估功能不识别新字段
**原因**: 评估逻辑需要数据中存在该字段
**解决**:
1. 确保标注和预测数据包含新字段
2. 检查字段名称拼写是否正确
3. 验证字段类型匹配

### Q4: 部署后配置丢失
**原因**: 忘记执行`reload_configs`命令
**解决**:
1. 立即执行：`poetry run python label_studio/manage.py reload_configs --force`
2. 将此命令加入部署脚本

## 配置文件格式参考

### 完整的JSON配置文件格式
```json
{
  "name": "Document Type Name",
  "key": "document_type_key", 
  "description": "文档类型描述",
  "required_fields": [
    "field1",
    "field2"
  ],
  "optional_fields": [
    "field3", 
    "field4"
  ],
  "field_display_properties": {
    "labels": {
      "field1": "Field 1 Display Name",
      "field2": "Field 2 Display Name"
    },
    "types": {
      "field1": "string|number|date|boolean",
      "field2": "string"
    }
  },
  "field_validation_rules": {
    "field1": {
      "required": true,
      "type": "string",
      "allowed_values": ["value1", "value2"]
    }
  },
  "evaluation_settings": {
    "comparison_method": "field_by_field",
    "tolerance": {
      "numeric_field": 0.01
    },
    "matching_strategy": {
      "type": "field_based",
      "primary_fields": ["key_field1", "key_field2"],
      "mode": "field_based",
      "verbose": true
    }
  }
}
```

## 最佳实践

1. **字段命名**: 使用驼峰命名法，保持一致性
2. **配置备份**: 修改前备份原配置文件
3. **渐进部署**: 先在测试环境验证，再部署生产
4. **版本控制**: 所有配置文件纳入Git管理
5. **文档更新**: 配置变更后及时更新文档

## 支持的文档类型

### 发票 (Invoice)
**字段**: `docType`, `invoiceDate`, `totalAmount`, `currency`, `billToName`, `billFromName`, `totalTaxAmount`, `invoiceNumber`, `buyerName`, `sellerName`, `taxRate`, `subtotal`, `description`

### 银行回单 (Bank Receipt)  
**字段**: `tradeId`, `recieptNum`, `logNum`, `tradeDate`, `amount`, `paymentName`, `paymentBank`, `paymentAccount`, `payeeName`, `payeeBank`, `payeeAccount`, `currency`, `tradePurpose`, `feeAmount`, `balance`, `序号`

### 收据 (Receipt)
**字段**: `docType`, `totalAmount`, `invoiceDate`, `currency`, `receiptNumber`, `storeName`, `storeAddress`, `items`, `paymentMethod`, `序号`

### 自定义 (Custom)
**用途**: 用户自定义字段配置，适用于特殊文档类型

---

*最后更新: 2025-01-03*