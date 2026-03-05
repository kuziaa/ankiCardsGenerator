#!/usr/bin/env python3
"""
Скрипт для быстрого старта проекта.
Проверяет зависимости и выполняет генерацию деки.
"""

import subprocess
import sys
from pathlib import Path

def check_python_version():
    """Проверяет версию Python."""
    if sys.version_info < (3, 7):
        print("❌ Требуется Python 3.7 или выше")
        print(f"   Текущая версия: {sys.version}")
        return False
    print(f"✅ Python версия: {sys.version.split()[0]}")
    return True

def check_requirements():
    """Проверяет наличие необходимых пакетов."""
    required = ['genanki', 'gtts', 'PIL', 'requests']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package} установлен")
        except ImportError:
            print(f"❌ {package} не установлен")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Установите недостающие пакеты:")
        print(f"   pip install -r requirements.txt")
        return False
    
    return True

def check_config():
    """Проверяет наличие конфигурационного файла."""
    config_path = Path("config.properties")
    sample_path = Path("config.properties.sample")
    
    if not config_path.exists():
        if sample_path.exists():
            print("⚠️  config.properties не найден")
            print(f"   Скопируйте из шаблона: cp config.properties.sample config.properties")
        else:
            print("❌ Ни config.properties, ни config.properties.sample не найдены")
            return False
        return False
    
    print("✅ config.properties найден")
    return True

def check_csv():
    """Проверяет наличие CSV файла с данными."""
    csv_path = Path("src/resources/cards.csv")
    
    if not csv_path.exists():
        print(f"❌ CSV файл не найден: {csv_path}")
        return False
    
    # Проверяем что файл не пустой
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if len(lines) < 2:  # Хотя бы заголовок и одна строка
        print(f"⚠️  CSV файл почти пуст ({len(lines)} строк)")
        return False
    
    print(f"✅ CSV файл найден ({len(lines)} строк)")
    return True

def main():
    """Основная функция проверки и запуска."""
    print("=" * 60)
    print("Anki Cards Generator - Проверка окружения")
    print("=" * 60)
    print()
    
    checks = [
        ("Python версия", check_python_version),
        ("Зависимости", check_requirements),
        ("Конфигурация", check_config),
        ("CSV файл", check_csv),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n📋 Проверка: {check_name}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ Ошибка при проверке: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 60)
    print("Результаты проверки:")
    print("=" * 60)
    
    all_passed = True
    for check_name, result in results:
        status = "✅ OK" if result else "❌ ОШИБКА"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✨ Все проверки пройдены!")
        print("\n🚀 Для запуска выполните:")
        print("   cd src")
        print("   python anki_generator.py")
    else:
        print("\n⚠️  Устраните ошибки перед запуском")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
