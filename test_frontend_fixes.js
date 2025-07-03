/**
 * 测试前端硬编码配置更新
 * 这个脚本验证所有前端硬编码的银行回单配置是否包含了所需的字段
 */

const fs = require('fs');
const path = require('path');

// 需要检查的字段
const requiredFields = ['tradeId', 'recieptNum', 'logNum', 'tradeDate', 'amount', 'paymentName', 'paymentBank', 'paymentAccount', 'payeeName', 'payeeBank', 'payeeAccount', 'currency'];

// 检查的文件
const filesToCheck = [
  'web/apps/labelstudio/src/components/EvaluationFieldsConfig/EvaluationFieldsConfig.jsx',
  'web/apps/labelstudio/src/pages/CreateProject/CreateProject.jsx'
];

console.log('=== 检查前端硬编码配置更新 ===\n');

filesToCheck.forEach(file => {
  const fullPath = path.join(__dirname, file);
  
  if (!fs.existsSync(fullPath)) {
    console.log(`❌ 文件不存在: ${file}`);
    return;
  }
  
  const content = fs.readFileSync(fullPath, 'utf8');
  
  // 查找bank_receipt配置
  const bankReceiptMatches = content.match(/bank_receipt:\s*{[^}]*fields:\s*\[([^\]]*)\][^}]*}/g);
  
  if (bankReceiptMatches) {
    console.log(`📄 ${file}`);
    
    bankReceiptMatches.forEach((match, index) => {
      // 提取字段数组
      const fieldsMatch = match.match(/fields:\s*\[([^\]]*)\]/);
      if (fieldsMatch) {
        const fieldsStr = fieldsMatch[1];
        const fields = fieldsStr
          .split(',')
          .map(f => f.trim().replace(/['"]/g, ''))
          .filter(f => f.length > 0);
        
        console.log(`  配置 ${index + 1}: ${fields.length} 个字段`);
        console.log(`  字段: [${fields.join(', ')}]`);
        
        // 检查缺失字段
        const missingFields = requiredFields.filter(f => !fields.includes(f));
        if (missingFields.length > 0) {
          console.log(`  ❌ 缺失字段: ${missingFields.join(', ')}`);
        } else {
          console.log(`  ✅ 所有必需字段都存在`);
        }
        console.log();
      }
    });
  } else {
    console.log(`📄 ${file} - 未找到bank_receipt配置`);
  }
});

console.log('=== 检查完成 ===');
console.log('\n建议：');
console.log('1. 重新构建前端代码');
console.log('2. 清除浏览器缓存');
console.log('3. 重启应用服务器');
console.log('4. 测试选择银行回单时是否显示所有12个字段');