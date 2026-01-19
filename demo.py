import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
import random

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath("."))

from src.models.regression import RollingRegression
from src.models.own_price_tracker import OwnPriceTracker
from src.alert.alert_manager import AlertManager


class DemoDataGenerator:
    """Генератор демонстрационных данных с гарантированным оповещением."""

    def __init__(self):
        self.eth_price = 2500.0
        self.btc_price = 50000.0
        self.timestamp = datetime.now()
        self.minute_counter = 0
        self.alert_triggered = False
        self.trigger_alert_at = random.randint(
            10, 20
        )  # Случайная минута для оповещения

    def generate_data(self):
        """Сгенерировать новые данные."""
        self.minute_counter += 1

        # Базовая доходность BTC
        btc_change = random.uniform(-0.002, 0.002)

        # Для демонстрации оповещения создадим значительное собственное движение ETH
        # после определенного момента
        if not self.alert_triggered and self.minute_counter >= self.trigger_alert_at:
            # Создаем значительное положительное собственное движение ETH (2%)
            eth_change = btc_change * 1.5 + 0.02  # Добавляем 2% собственного движения
            print(
                f"\n⚠️ Генерирую значительное собственное движение ETH для демонстрации оповещения!"
            )
        else:
            # Обычная корреляция с небольшим шумом
            eth_change = btc_change * 1.5 + random.uniform(-0.001, 0.001)

        self.btc_price *= 1 + btc_change
        self.eth_price *= 1 + eth_change
        self.timestamp += timedelta(minutes=1)

        return {
            "eth_price": self.eth_price,
            "btc_price": self.btc_price,
            "timestamp": self.timestamp,
            "eth_return": eth_change,
            "btc_return": btc_change,
            "minute": self.minute_counter,
        }


async def demo_mode():
    """Демонстрационный режим работы программы с гарантированным оповещением."""
    print("\n" + "=" * 70)
    print("ETH Own Movement Tracker - DEMO MODE (с гарантированным оповещением)")
    print("=" * 70)

    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Инициализируем компоненты с меньшим окном для быстрой демонстрации
    regression = RollingRegression(window_size=5, min_window=2)
    tracker = OwnPriceTracker(initial_index=100.0)
    alert_manager = AlertManager(cooldown_minutes=0)  # Без задержки для демо

    generator = DemoDataGenerator()

    print("\nДемонстрация работы системы:")
    print("- Анализируется зависимость ETH от BTC")
    print("- Рассчитывается собственная цена ETH (без влияния BTC)")
    print("- При изменении собственной цены на 0.5% за 5 минут выводится оповещение")
    print(f"- Оповещение будет сгенерировано на минуте {generator.trigger_alert_at}")
    print("-" * 70)

    try:
        for i in range(30):  # 30 минут демо
            # Генерируем данные
            data = generator.generate_data()

            print(f"\nМинута {data['minute']}:")
            print(f"  ETH: ${data['eth_price']:.2f} ({data['eth_return'] * 100:+.3f}%)")
            print(f"  BTC: ${data['btc_price']:.2f} ({data['btc_return'] * 100:+.3f}%)")

            # Обновляем регрессию
            result = regression.update(
                data["timestamp"], data["eth_return"], data["btc_return"]
            )

            if result:
                # Обновляем трекер
                current_index = tracker.update(data["timestamp"], result.epsilon)

                # Проверяем оповещения (для демо используем 5 минут и порог 0.5%)
                change_percent = tracker.get_index_change(minutes=5)

                # Выводим статистику
                print(f"  Регрессия: β={result.beta:.4f}, ε={result.epsilon:.6f}")
                print(f"  Индекс собственной цены ETH: {current_index:.4f}")

                if change_percent is not None:
                    print(f"  Изменение за 5 минут: {change_percent:+.3f}%")

                    # Проверяем порог 0.5% для демо
                    if abs(change_percent) >= 0.5:
                        # Помечаем, что оповещение сработало
                        if not generator.alert_triggered:
                            generator.alert_triggered = True
                            print(
                                f"\n🎯 ИЗМЕНЕНИЕ НА {abs(change_percent):.2f}%! ДОЛЖНО СРАБОТАТЬ ОПОВЕЩЕНИЕ!"
                            )

                        # Отправляем оповещение
                        alert_manager.send_price_change_alert(
                            change_percent,
                            current_index,
                            is_positive=change_percent > 0,
                        )
                else:
                    print(f"  Ожидание данных... (нужно 5 минут истории)")

            else:
                print(
                    f"  Сбор данных для регрессии... ({regression.get_window_size()}/{regression.min_window})"
                )

            # Если оповещение сработало, немного замедлим демо для наглядности
            if (
                generator.alert_triggered
                and data["minute"] == generator.trigger_alert_at
            ):
                print("\n" + "=" * 70)
                print("✅ ОПОВЕЩЕНИЕ УСПЕШНО СРАБОТАЛО!")
                print("✅ Система корректно отслеживает собственные движения ETH")
                print("✅ При изменении на 0.5%+ за 5 минут выводится оповещение")
                print("=" * 70)
                await asyncio.sleep(3)  # Пауза для наглядности

            await asyncio.sleep(1)  # Ждем 1 секунду вместо 1 минуты

    except KeyboardInterrupt:
        print("\n\nДемо остановлено пользователем")

    # Итоги демонстрации
    print("\n" + "=" * 70)
    print("ИТОГИ ДЕМОНСТРАЦИИ:")
    print("=" * 70)

    if generator.alert_triggered:
        print("✅ Тест пройден: оповещение успешно сработало")
        print(
            "✅ Система корректно отслеживает значительные изменения собственной цены ETH"
        )
        print("✅ При изменении индекса на 0.5%+ за 5 минут выводится оповещение")
    else:
        print("⚠️ Оповещение не сработало")
        print("ℹ️  Это могло произойти, если:")
        print("   - Не накопилось достаточно данных (минимум 5 минут)")
        print("   - Изменение индекса было менее 0.5%")
        print("   - В реальной системе порог составляет 1% за 60 минут")

    # Статистика
    print(f"\n📊 Статистика за демо:")
    print(f"   - Всего минут обработано: {generator.minute_counter}")
    print(f"   - Размер окна регрессии: {regression.get_window_size()}")
    print(f"   - Текущий индекс собственной цены: {tracker.get_current_index():.4f}")
    print(f"   - История индекса: {tracker.get_history_size()} записей")

    print("\n" + "=" * 70)
    print("Демонстрация завершена!")
    print("Для реальной работы запустите: python main.py")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_mode())
