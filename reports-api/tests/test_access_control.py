import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"

def test_access_control():
    """Тестирование системы контроля доступа"""
    
    print("🧪 Тестирование системы контроля доступа BionicPRO")
    print("=" * 50)
    
    # Тест 1: Пользователь 1001 запрашивает свои данные
    print("\n1. ✅ Пользователь 1001 запрашивает свои данные:")
    headers = {"Authorization": "Bearer user_1001"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/reports/1001/summary?period=week",
            headers=headers
        )
        print(f"   Статус: {response.status_code}")
        if response.status_code == 200:
            print("   Результат: УСПЕХ - доступ разрешен")
        else:
            print(f"   Результат: ОШИБКА - {response.json()}")
    except Exception as e:
        print(f"   Ошибка: {e}")
    
    # Тест 2: Пользователь 1001 пытается запросить данные пользователя 1002
    print("\n2. ❌ Пользователь 1001 пытается запросить данные пользователя 1002:")
    
    try:
        response = requests.get(
            f"{BASE_URL}/reports/1002/summary",
            headers=headers
        )
        print(f"   Статус: {response.status_code}")
        if response.status_code == 403:
            print("   Результат: УСПЕХ - доступ запрещен как и ожидалось")
            print(f"   Ответ: {response.json()}")
        else:
            print(f"   Результат: ОШИБКА - доступ не был запрещен!")
    except Exception as e:
        print(f"   Ошибка: {e}")
    
    # Тест 3: Пользователь 1002 запрашивает свои данные
    print("\n3. ✅ Пользователь 1002 запрашивает свои данные:")
    headers2 = {"Authorization": "Bearer user_1002"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/reports/1002/summary",
            headers=headers2
        )
        print(f"   Статус: {response.status_code}")
        if response.status_code == 200:
            print("   Результат: УСПЕХ - доступ разрешен")
        else:
            print(f"   Результат: ОШИБКА - {response.json()}")
    except Exception as e:
        print(f"   Ошибка: {e}")
    
    # Тест 4: Использование endpoint /me
    print("\n4. ✅ Пользователь 1001 использует endpoint /me:")
    
    try:
        response = requests.get(
            f"{BASE_URL}/reports/me/summary",
            headers=headers
        )
        print(f"   Статус: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Результат: УСПЕХ - получены данные пользователя {data.get('user_id')}")
        else:
            print(f"   Результат: ОШИБКА - {response.json()}")
    except Exception as e:
        print(f"   Ошибка: {e}")
    
    print("\n" + "=" * 50)
    print("Тестирование завершено")

if __name__ == "__main__":
    test_access_control()