#!/usr/bin/env python3
"""
票据对比工具 - Python兼容性检查
检查当前Python环境是否满足所有依赖要求
"""

import sys
import importlib
from typing import Dict, List, Tuple


def check_python_version() -> Tuple[bool, str]:
    """检查Python版本"""
    current_version = sys.version_info
    required_major = 3
    required_minor = 7  # dataclasses需要Python 3.7+
    
    if current_version.major >= required_major and current_version.minor >= required_minor:
        return True, f"✅ Python {current_version.major}.{current_version.minor}.{current_version.micro}"
    else:
        return False, f"❌ Python {current_version.major}.{current_version.minor}.{current_version.micro} (需要 Python {required_major}.{required_minor}+)"


def check_standard_library_modules() -> Dict[str, Tuple[bool, str]]:
    """检查标准库模块"""
    modules = {
        'json': '所有版本都支持',
        're': '所有版本都支持', 
        'datetime': '所有版本都支持',
        'typing': 'Python 3.5+',
        'pathlib': 'Python 3.4+',
        'argparse': 'Python 2.7+',
        'dataclasses': 'Python 3.7+ (Python 3.6需要安装backport)'
    }
    
    results = {}
    
    for module_name, version_info in modules.items():
        try:
            importlib.import_module(module_name)
            results[module_name] = (True, f"✅ {module_name} - {version_info}")
        except ImportError:
            results[module_name] = (False, f"❌ {module_name} - 模块不可用")
    
    return results


def check_dataclasses_compatibility() -> Tuple[bool, str]:
    """特别检查dataclasses的兼容性"""
    python_version = sys.version_info
    
    try:
        from dataclasses import dataclass, field
        
        # 测试基本功能
        @dataclass
        class TestClass:
            value: int = field(default=42)
        
        test_obj = TestClass()
        assert test_obj.value == 42
        
        if python_version >= (3, 7):
            return True, "✅ dataclasses - 原生支持 (Python 3.7+)"
        else:
            return True, "✅ dataclasses - backport包支持 (Python 3.6)"
            
    except ImportError:
        if python_version < (3, 7):
            return False, "❌ dataclasses - 需要安装: pip install dataclasses"
        else:
            return False, "❌ dataclasses - 意外的导入错误"
    except Exception as e:
        return False, f"❌ dataclasses - 功能测试失败: {e}"


def check_optional_features() -> Dict[str, Tuple[bool, str]]:
    """检查可选功能的兼容性"""
    features = {}
    
    # 检查typing的Union语法 (Python 3.10+新语法)
    try:
        # 测试新的Union语法 (int | str)
        python_version = sys.version_info
        if python_version >= (3, 10):
            features['union_syntax'] = (True, "✅ 新Union语法 (int | str) - Python 3.10+")
        else:
            features['union_syntax'] = (True, "⚠️  旧Union语法 (Union[int, str]) - Python 3.10以下")
    except:
        features['union_syntax'] = (False, "❌ Union类型注解不支持")
    
    # 检查f-string支持 (Python 3.6+)
    try:
        test_var = "world"
        test_fstring = f"hello {test_var}"
        features['f_strings'] = (True, "✅ f-string - Python 3.6+")
    except:
        features['f_strings'] = (False, "❌ f-string不支持")
    
    return features


def generate_requirements_txt() -> str:
    """生成requirements.txt内容"""
    python_version = sys.version_info
    
    requirements = [
        "# 票据对比工具依赖",
        "# Python 版本要求: >= 3.7",
        "",
    ]
    
    if python_version < (3, 7):
        requirements.extend([
            "# Python 3.6 需要的backport包",
            "dataclasses>=0.6",
            "",
        ])
    
    requirements.extend([
        "# 所有依赖都是Python标准库，无需额外安装",
        "# json - 标准库",
        "# re - 标准库", 
        "# datetime - 标准库",
        "# typing - 标准库 (Python 3.5+)",
        "# pathlib - 标准库 (Python 3.4+)",
        "# argparse - 标准库",
        "# dataclasses - 标准库 (Python 3.7+)",
    ])
    
    return "\n".join(requirements)


def main():
    """主检查函数"""
    print("票据对比工具 - Python兼容性检查")
    print("=" * 50)
    
    # 检查Python版本
    python_ok, python_msg = check_python_version()
    print(f"\nPython版本: {python_msg}")
    
    if not python_ok:
        print("\n⚠️  警告: Python版本过低，可能导致部分功能不可用")
        print("建议升级到Python 3.7或更高版本")
    
    # 检查标准库模块
    print("\n标准库模块检查:")
    module_results = check_standard_library_modules()
    all_modules_ok = True
    
    for module, (ok, msg) in module_results.items():
        print(f"  {msg}")
        if not ok:
            all_modules_ok = False
    
    # 特别检查dataclasses
    print("\n关键模块检查:")
    dataclasses_ok, dataclasses_msg = check_dataclasses_compatibility()
    print(f"  {dataclasses_msg}")
    
    # 检查可选功能
    print("\n语言特性检查:")
    feature_results = check_optional_features()
    
    for feature, (ok, msg) in feature_results.items():
        print(f"  {msg}")
    
    # 总结
    print("\n" + "=" * 50)
    
    if python_ok and all_modules_ok and dataclasses_ok:
        print("✅ 兼容性检查通过！所有依赖都满足要求。")
        print("\n📦 依赖总结:")
        print("- 只使用Python标准库")
        print("- 无需安装额外的第三方包")
        if sys.version_info < (3, 7):
            print("- Python 3.6需要安装: pip install dataclasses")
    else:
        print("❌ 兼容性检查发现问题，请解决后再使用。")
        
        if not python_ok:
            print("- 请升级Python版本到3.7+")
        
        if not dataclasses_ok:
            if sys.version_info < (3, 7):
                print("- 请安装dataclasses: pip install dataclasses")
            else:
                print("- dataclasses模块异常，请检查Python安装")
    
    # 生成requirements.txt
    print(f"\n📄 requirements.txt内容:")
    print("-" * 30)
    print(generate_requirements_txt())
    
    # 使用建议
    print("\n💡 使用建议:")
    print("1. 在Python 3.7+环境中运行最佳")
    print("2. 所有代码只依赖标准库，便于部署")
    print("3. 如需在Python 3.6中使用，安装: pip install dataclasses")
    print("4. 代码可以直接在其他机器上运行，无需复杂环境配置")


if __name__ == "__main__":
    main() 