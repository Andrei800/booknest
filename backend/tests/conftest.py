"""
Конфигурация pytest для тестов BookNest
"""
import pytest
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
