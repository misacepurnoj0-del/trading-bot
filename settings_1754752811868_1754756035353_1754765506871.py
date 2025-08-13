import streamlit as st
import time
from typing import Dict

from auth.security import SecureDataManager
from trading.advanced_trader import AdvancedTrader
from utils.logger import get_logger

logger = get_logger(__name__)

def show():
    """Display settings page"""
    try:
        st.title("⚙️ Настройки")
        
        # Settings tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🔑 API ключи", 
            "🎛️ Торговые параметры", 
            "🔔 Уведомления", 
            "🛡️ Безопасность", 
            "📊 Система"
        ])
        
        with tab1:
            show_api_settings()
        
        with tab2:
            show_trading_settings()
        
        with tab3:
            show_notification_settings()
        
        with tab4:
            show_security_settings()
        
        with tab5:
            show_system_settings()
    
    except Exception as e:
        logger.error(f"Error in settings page: {str(e)}")
        st.error(f"Ошибка загрузки настроек: {str(e)}")

def show_api_settings():
    """Display API settings"""
    try:
        st.markdown("### 🔑 Настройки API ключей")
        
        # Current API key status
        api_key, secret_key = SecureDataManager.get_api_keys()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if api_key and secret_key:
                st.success("✅ API ключи настроены")
                st.info(f"API Key: {api_key[:8]}{'*' * (len(api_key) - 8) if len(api_key) > 8 else ''}")
                st.info(f"Secret Key: {'*' * 16}")
            else:
                st.warning("⚠️ API ключи не настроены")
                st.error("Для реальной торговли необходимо настроить API ключи MEXC")
        
        with col2:
            st.markdown("#### 📋 Инструкция")
            st.write("""
            **Как получить API ключи MEXC:**
            1. Войдите в аккаунт на MEXC
            2. Перейдите в API Management
            3. Создайте новый API ключ
            4. Включите права на торговлю
            5. Сохраните ключи в безопасном месте
            """)
        
        st.markdown("---")
        
        # API key configuration form
        st.markdown("#### 🔧 Настройка API ключей")
        
        with st.form("api_keys_form"):
            new_api_key = st.text_input(
                "MEXC API Key",
                value="",
                type="password",
                help="Введите ваш API ключ от MEXC"
            )
            
            new_secret_key = st.text_input(
                "MEXC Secret Key", 
                value="",
                type="password",
                help="Введите ваш Secret ключ от MEXC"
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                save_keys = st.form_submit_button("💾 Сохранить ключи", use_container_width=True)
            
            with col2:
                test_keys = st.form_submit_button("🧪 Тестировать ключи", use_container_width=True)
            
            with col3:
                clear_keys = st.form_submit_button("🗑️ Очистить ключи", use_container_width=True)
            
            if save_keys and new_api_key and new_secret_key:
                save_api_keys(new_api_key, new_secret_key)
            
            if test_keys and new_api_key and new_secret_key:
                test_api_keys(new_api_key, new_secret_key)
            
            if clear_keys:
                clear_api_keys()
        
        # Security warnings
        st.markdown("---")
        st.markdown("#### ⚠️ Важные предупреждения о безопасности")
        
        st.warning("""
        🔒 **Безопасность API ключей:**
        - Никогда не передавайте свои API ключи третьим лицам
        - Используйте только HTTPS соединения
        - Регулярно меняйте API ключи
        - Ограничьте права API ключей только необходимыми функциями
        - Следите за активностью на своем аккаунте
        """)
        
        st.error("""
        🚨 **Внимание:**
        - API ключи дают доступ к вашему торговому аккаунту
        - Неправильное использование может привести к потерям
        - Всегда тестируйте сначала в демо режиме
        """)
    
    except Exception as e:
        logger.error(f"Error in API settings: {str(e)}")
        st.error("Ошибка настроек API")

def show_trading_settings():
    """Display trading parameters settings"""
    try:
        st.markdown("### 🎛️ Торговые параметры")
        
        # Initialize trader if needed
        if 'trader' not in st.session_state:
            api_key, secret_key = SecureDataManager.get_api_keys()
            demo_mode = st.session_state.get('demo_mode', True)
            st.session_state.trader = AdvancedTrader(api_key, secret_key, demo_mode)
        
        trader = st.session_state.trader
        
        # Risk management settings
        st.markdown("#### 🛡️ Управление рисками")
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_positions = st.number_input(
                "Максимальное количество позиций",
                min_value=1,
                max_value=10,
                value=getattr(trader, 'max_positions', 3),
                step=1,
                help="Максимальное количество одновременно открытых позиций"
            )
            
            position_size_pct = st.slider(
                "Размер позиции (% от капитала)",
                min_value=10.0,
                max_value=50.0,
                value=getattr(trader, 'position_size_pct', 33.33),
                step=1.0,
                help="Процент капитала на одну позицию"
            )
            
            max_leverage = st.slider(
                "Максимальное плечо",
                min_value=1.0,
                max_value=10.0,
                value=getattr(trader, 'max_leverage', 5.0),
                step=0.5,
                help="Максимальное кредитное плечо"
            )
        
        with col2:
            min_confidence_threshold = st.slider(
                "Минимальная уверенность сигнала (%)",
                min_value=50.0,
                max_value=95.0,
                value=getattr(trader, 'min_confidence_threshold', 70.0),
                step=5.0,
                help="Минимальная уверенность для выполнения сделки"
            )
            
            max_hold_time_hours = st.number_input(
                "Максимальное время удержания (часы)",
                min_value=1,
                max_value=720,  # 30 days
                value=getattr(trader, 'max_hold_time_hours', 168),  # 1 week
                step=1,
                help="Максимальное время удержания позиции"
            )
            
            # Advanced risk settings (if available)
            if hasattr(trader, 'risk_per_trade'):
                risk_per_trade = st.slider(
                    "Риск на сделку (%)",
                    min_value=0.5,
                    max_value=5.0,
                    value=trader.risk_per_trade,
                    step=0.1,
                    help="Максимальный риск на одну сделку"
                )
                
                portfolio_heat = st.slider(
                    "Общий риск портфеля (%)",
                    min_value=1.0,
                    max_value=15.0,
                    value=getattr(trader, 'portfolio_heat', 6.0),
                    step=0.5,
                    help="Максимальный общий риск портфеля"
                )
        
        # Indicator weights settings
        st.markdown("#### ⚖️ Веса индикаторов")
        
        indicator_weights = getattr(trader, 'indicator_weights', {
            'technical': 0.35,
            'fundamental': 0.25,
            'sentiment': 0.20,
            'momentum': 0.20
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            technical_weight = st.slider(
                "Технический анализ",
                min_value=0.1,
                max_value=0.6,
                value=indicator_weights.get('technical', 0.35),
                step=0.05,
                help="Вес технического анализа в общем сигнале"
            )
            
            fundamental_weight = st.slider(
                "Фундаментальный анализ",
                min_value=0.1,
                max_value=0.6,
                value=indicator_weights.get('fundamental', 0.25),
                step=0.05,
                help="Вес фундаментального анализа"
            )
        
        with col2:
            sentiment_weight = st.slider(
                "Анализ настроений",
                min_value=0.1,
                max_value=0.6,
                value=indicator_weights.get('sentiment', 0.20),
                step=0.05,
                help="Вес анализа новостей и настроений"
            )
            
            momentum_weight = st.slider(
                "Анализ моментума",
                min_value=0.1,
                max_value=0.6,
                value=indicator_weights.get('momentum', 0.20),
                step=0.05,
                help="Вес анализа моментума и объемов"
            )
        
        # Validate weights sum to 1.0
        total_weight = technical_weight + fundamental_weight + sentiment_weight + momentum_weight
        
        if abs(total_weight - 1.0) > 0.01:
            st.warning(f"⚠️ Сумма весов должна равняться 100%. Текущая сумма: {total_weight:.1%}")
        else:
            st.success(f"✅ Сумма весов: {total_weight:.1%}")
        
        # Save settings button
        if st.button("💾 Сохранить торговые параметры", use_container_width=True):
            save_trading_parameters(
                trader, max_positions, position_size_pct, max_leverage,
                min_confidence_threshold, max_hold_time_hours,
                {
                    'technical': technical_weight,
                    'fundamental': fundamental_weight,
                    'sentiment': sentiment_weight,
                    'momentum': momentum_weight
                }
            )
        
        # Reset to defaults
        if st.button("🔄 Восстановить по умолчанию"):
            reset_trading_parameters(trader)
    
    except Exception as e:
        logger.error(f"Error in trading settings: {str(e)}")
        st.error("Ошибка торговых настроек")

def show_notification_settings():
    """Display notification settings"""
    try:
        st.markdown("### 🔔 Настройки уведомлений")
        
        # Initialize notification manager
        if 'trader' not in st.session_state:
            api_key, secret_key = SecureDataManager.get_api_keys()
            demo_mode = st.session_state.get('demo_mode', True)
            st.session_state.trader = AdvancedTrader(api_key, secret_key, demo_mode)
        
        trader = st.session_state.trader
        notifications = trader.notifications
        
        # Current notification statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_notifications = len(notifications.get_notifications())
            st.metric("Всего уведомлений", total_notifications)
        
        with col2:
            unread_count = notifications.get_unread_count()
            st.metric("Непрочитанных", unread_count)
        
        with col3:
            st.metric("Максимум уведомлений", notifications.max_notifications)
        
        # Notification type settings
        st.markdown("#### 📱 Типы уведомлений")
        
        notification_settings = st.session_state.get('notification_settings', {
            'trade_opened': True,
            'trade_closed': True,
            'signal_generated': True,
            'risk_warning': True,
            'system_status': True,
            'performance_update': True
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            trade_opened = st.checkbox(
                "📈 Открытие сделок",
                value=notification_settings.get('trade_opened', True),
                help="Уведомления при открытии новых позиций"
            )
            
            trade_closed = st.checkbox(
                "📊 Закрытие сделок",
                value=notification_settings.get('trade_closed', True),
                help="Уведомления при закрытии позиций"
            )
            
            signal_generated = st.checkbox(
                "🎯 Генерация сигналов",
                value=notification_settings.get('signal_generated', True),
                help="Уведомления о новых торговых сигналах"
            )
        
        with col2:
            risk_warning = st.checkbox(
                "⚠️ Предупреждения о рисках",
                value=notification_settings.get('risk_warning', True),
                help="Уведомления о рисковых ситуациях"
            )
            
            system_status = st.checkbox(
                "🔧 Статус системы",
                value=notification_settings.get('system_status', True),
                help="Уведомления о статусе торговой системы"
            )
            
            performance_update = st.checkbox(
                "📊 Обновления производительности",
                value=notification_settings.get('performance_update', True),
                help="Периодические отчеты о производительности"
            )
        
        # Notification management
        st.markdown("#### 🧹 Управление уведомлениями")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Отметить все как прочитанные", use_container_width=True):
                marked_count = notifications.mark_all_as_read()
                st.success(f"Отмечено {marked_count} уведомлений как прочитанные")
                time.sleep(1)
                st.rerun()
        
        with col2:
            if st.button("🗑️ Очистить старые (7+ дней)", use_container_width=True):
                cleared_count = notifications.clear_old_notifications(days=7)
                st.success(f"Удалено {cleared_count} старых уведомлений")
                time.sleep(1)
                st.rerun()
        
        with col3:
            max_notifications = st.number_input(
                "Макс. уведомлений",
                min_value=50,
                max_value=500,
                value=notifications.max_notifications,
                step=10
            )
        
        # Save notification settings
        if st.button("💾 Сохранить настройки уведомлений", use_container_width=True):
            st.session_state.notification_settings = {
                'trade_opened': trade_opened,
                'trade_closed': trade_closed,
                'signal_generated': signal_generated,
                'risk_warning': risk_warning,
                'system_status': system_status,
                'performance_update': performance_update
            }
            
            notifications.max_notifications = max_notifications
            
            st.success("✅ Настройки уведомлений сохранены")
            time.sleep(1)
            st.rerun()
        
        # Recent notifications preview
        st.markdown("#### 📋 Последние уведомления")
        
        recent_notifications = notifications.get_notifications(limit=10)
        
        if recent_notifications:
            for notif in recent_notifications:
                # Icon based on type
                icon = {
                    'trade_opened': '📈',
                    'trade_closed': '📊',
                    'signal_generated': '🎯',
                    'risk_warning': '⚠️',
                    'system_status': '🔧',
                    'performance_update': '📊'
                }.get(notif.type.value, '📝')
                
                # Status indicator
                status = "🔴" if not notif.read else "✅"
                
                # Priority color
                if notif.priority == 'critical':
                    st.error(f"{status} {icon} **{notif.title}** - {notif.timestamp.strftime('%H:%M:%S')}")
                elif notif.priority == 'high':
                    st.warning(f"{status} {icon} **{notif.title}** - {notif.timestamp.strftime('%H:%M:%S')}")
                else:
                    st.info(f"{status} {icon} **{notif.title}** - {notif.timestamp.strftime('%H:%M:%S')}")
                
                st.caption(f"   {notif.message}")
        else:
            st.info("📭 Нет уведомлений")
    
    except Exception as e:
        logger.error(f"Error in notification settings: {str(e)}")
        st.error("Ошибка настроек уведомлений")

def show_security_settings():
    """Display security settings"""
    try:
        st.markdown("### 🛡️ Настройки безопасности")
        
        # Security manager
        security_manager = st.session_state.security_manager
        
        # Current session info
        session_info = security_manager.get_session_info()
        
        if session_info['authenticated']:
            st.success("✅ Авторизован")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Пользователь", session_info['username'])
                st.metric("Время сессии", f"{session_info['session_age_hours']:.1f} часов")
            
            with col2:
                st.metric("Остается времени", f"{session_info['remaining_hours']:.1f} часов")
                st.metric("Токен сессии", session_info['session_token'])
        
        # Security settings
        st.markdown("#### 🔐 Параметры безопасности")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**Таймаут сессии:** {security_manager.session_timeout / 3600:.0f} часов")
            st.info(f"**Максимум попыток входа:** {security_manager.max_login_attempts}")
            st.info(f"**Время блокировки:** {security_manager.lockout_duration / 60:.0f} минут")
        
        with col2:
            st.info(f"**Алгоритм хеширования:** SHA-256 с солью")
            st.info(f"**Шифрование API ключей:** XOR с токеном сессии")
            st.info(f"**Длина токена сессии:** 32 байта")
        
        # Security actions
        st.markdown("#### 🔧 Действия безопасности")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Продлить сессию", use_container_width=True):
                security_manager.extend_session()
                st.success("✅ Сессия продлена")
                time.sleep(1)
                st.rerun()
        
        with col2:
            if st.button("🗑️ Очистить API ключи", use_container_width=True):
                SecureDataManager.clear_api_keys()
                st.success("✅ API ключи удалены")
                time.sleep(1)
                st.rerun()
        
        with col3:
            if st.button("🚪 Выйти из системы", use_container_width=True):
                security_manager.logout()
                st.success("✅ Выход выполнен")
                time.sleep(1)
                st.rerun()
        
        # Security audit
        st.markdown("#### 📊 Аудит безопасности")
        
        # Check for security issues
        security_issues = []
        
        # Check API keys
        api_key, secret_key = SecureDataManager.get_api_keys()
        if not api_key or not secret_key:
            security_issues.append("⚠️ API ключи не настроены")
        
        # Check session age
        if session_info['authenticated'] and session_info['session_age_hours'] > 6:
            security_issues.append("⚠️ Сессия активна более 6 часов")
        
        # Check demo mode
        if st.session_state.get('demo_mode', True):
            security_issues.append("ℹ️ Работа в демо режиме (не критично)")
        
        if security_issues:
            st.markdown("**🔍 Обнаруженные проблемы безопасности:**")
            for issue in security_issues:
                if issue.startswith("⚠️"):
                    st.warning(issue)
                else:
                    st.info(issue)
        else:
            st.success("✅ Проблем безопасности не обнаружено")
        
        # Security recommendations
        st.markdown("#### 💡 Рекомендации по безопасности")
        
        st.info("""
        🔒 **Рекомендации:**
        - Регулярно меняйте пароли и API ключи
        - Не используйте общие компьютеры для торговли
        - Всегда выходите из системы после работы
        - Проверяйте историю торговли на предмет подозрительной активности
        - Используйте сильные пароли
        - Ограничьте права API ключей только необходимыми функциями
        """)
    
    except Exception as e:
        logger.error(f"Error in security settings: {str(e)}")
        st.error("Ошибка настроек безопасности")

def show_system_settings():
    """Display system settings"""
    try:
        st.markdown("### 📊 Системные настройки")
        
        # System information
        st.markdown("#### ℹ️ Информация о системе")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**Версия приложения:** 1.0.0")
            st.info("**Торговая платформа:** MEXC")
            st.info("**Режим работы:** " + ("Демо" if st.session_state.get('demo_mode', True) else "Реальный"))
            st.info("**AI модель:** Интеллектуальный анализ v1.0")
        
        with col2:
            st.info("**Поддерживаемые индикаторы:** 15+")
            st.info("**Источники новостей:** 6")
            st.info("**Максимальные позиции:** 3-5")
            st.info("**Поддержка плеча:** До 5x")
        
        # System components status
        st.markdown("#### 🔧 Статус компонентов")
        
        # Check components
        components_status = []
        
        try:
            # Check trader
            if 'trader' in st.session_state:
                components_status.append(("🤖 Торговый движок", "✅ Активен", "success"))
            else:
                components_status.append(("🤖 Торговый движок", "❌ Не инициализирован", "error"))
            
            # Check security
            if st.session_state.security_manager.is_authenticated():
                components_status.append(("🛡️ Система безопасности", "✅ Активна", "success"))
            else:
                components_status.append(("🛡️ Система безопасности", "❌ Не авторизован", "error"))
            
            # Check API keys
            api_key, secret_key = SecureDataManager.get_api_keys()
            if api_key and secret_key:
                components_status.append(("🔑 API интеграция", "✅ Настроена", "success"))
            else:
                components_status.append(("🔑 API интеграция", "⚠️ Не настроена", "warning"))
            
            # Check news parser
            if 'trader' in st.session_state:
                components_status.append(("📰 Анализ новостей", "✅ Доступен", "success"))
            else:
                components_status.append(("📰 Анализ новостей", "❌ Недоступен", "error"))
            
            # Check signal generator
            if 'signal_generator' in st.session_state:
                components_status.append(("🎯 Генератор сигналов", "✅ Активен", "success"))
            else:
                components_status.append(("🎯 Генератор сигналов", "❌ Не инициализирован", "error"))
        
        except Exception as e:
            components_status.append(("❌ Ошибка проверки", str(e), "error"))
        
        # Display component status
        for component, status, status_type in components_status:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**{component}**")
            
            with col2:
                if status_type == "success":
                    st.success(status)
                elif status_type == "warning":
                    st.warning(status)
                else:
                    st.error(status)
        
        # System controls
        st.markdown("#### 🎛️ Управление системой")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Перезапустить компоненты", use_container_width=True):
                restart_system_components()
        
        with col2:
            if st.button("🧹 Очистить кеши", use_container_width=True):
                clear_system_caches()
        
        with col3:
            if st.button("📊 Обновить статус", use_container_width=True):
                st.rerun()
        
        # Advanced settings
        st.markdown("#### ⚙️ Расширенные настройки")
        
        with st.expander("🔧 Технические параметры"):
            col1, col2 = st.columns(2)
            
            with col1:
                log_level = st.selectbox(
                    "Уровень логирования",
                    ["DEBUG", "INFO", "WARNING", "ERROR"],
                    index=1,
                    help="Уровень детализации логов"
                )
                
                cache_duration = st.number_input(
                    "Время кеширования (сек)",
                    min_value=60,
                    max_value=3600,
                    value=300,
                    step=60,
                    help="Время хранения кешированных данных"
                )
            
            with col2:
                max_threads = st.number_input(
                    "Максимум потоков",
                    min_value=1,
                    max_value=10,
                    value=4,
                    step=1,
                    help="Максимальное количество потоков для анализа"
                )
                
                request_timeout = st.number_input(
                    "Таймаут запросов (сек)",
                    min_value=5,
                    max_value=60,
                    value=10,
                    step=5,
                    help="Таймаут для API запросов"
                )
            
            if st.button("💾 Применить технические настройки"):
                st.session_state.technical_settings = {
                    'log_level': log_level,
                    'cache_duration': cache_duration,
                    'max_threads': max_threads,
                    'request_timeout': request_timeout
                }
                st.success("✅ Технические настройки сохранены")
        
        # Data management
        st.markdown("#### 📂 Управление данными")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📤 Экспортировать данные", use_container_width=True):
                export_trading_data()
        
        with col2:
            if st.button("🗑️ Очистить историю", use_container_width=True):
                if st.session_state.get('confirm_clear_history', False):
                    clear_trading_history()
                    st.session_state.confirm_clear_history = False
                else:
                    st.session_state.confirm_clear_history = True
                    st.warning("⚠️ Нажмите еще раз для подтверждения")
        
        with col3:
            if st.button("🔄 Сброс настроек", use_container_width=True):
                if st.session_state.get('confirm_reset_settings', False):
                    reset_all_settings()
                    st.session_state.confirm_reset_settings = False
                else:
                    st.session_state.confirm_reset_settings = True
                    st.warning("⚠️ Нажмите еще раз для подтверждения")
    
    except Exception as e:
        logger.error(f"Error in system settings: {str(e)}")
        st.error("Ошибка системных настроек")

# Helper functions

def save_api_keys(api_key: str, secret_key: str):
    """Save API keys securely"""
    try:
        success = SecureDataManager.store_api_keys(api_key, secret_key)
        
        if success:
            st.success("✅ API ключи сохранены безопасно")
            
            # Reinitialize trader with new keys
            if 'trader' in st.session_state:
                demo_mode = st.session_state.get('demo_mode', True)
                st.session_state.trader = AdvancedTrader(api_key, secret_key, demo_mode)
            
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Ошибка сохранения API ключей")
    
    except Exception as e:
        logger.error(f"Error saving API keys: {str(e)}")
        st.error(f"Ошибка сохранения: {str(e)}")

def test_api_keys(api_key: str, secret_key: str):
    """Test API keys connectivity"""
    try:
        # Create temporary client to test
        from exchanges.mexc_client import MEXCClient
        
        test_client = MEXCClient(api_key, secret_key, demo_mode=True)
        
        with st.spinner("Тестирование API ключей..."):
            # Test basic connectivity
            server_time = test_client.get_server_time()
            
            if 'error' in server_time:
                st.error(f"❌ Ошибка подключения: {server_time['error']}")
                return
            
            # Test authenticated request
            account_info = test_client.get_account_info()
            
            if 'error' in account_info:
                st.error(f"❌ Ошибка аутентификации: {account_info['error']}")
                return
            
            st.success("✅ API ключи работают корректно!")
            st.info("🔍 Соединение с MEXC установлено успешно")
    
    except Exception as e:
        logger.error(f"Error testing API keys: {str(e)}")
        st.error(f"Ошибка тестирования: {str(e)}")

def clear_api_keys():
    """Clear saved API keys"""
    try:
        SecureDataManager.clear_api_keys()
        
        # Reset trader to demo mode
        if 'trader' in st.session_state:
            st.session_state.trader = AdvancedTrader("", "", demo_mode=True)
            st.session_state.demo_mode = True
        
        st.success("✅ API ключи удалены")
        time.sleep(1)
        st.rerun()
    
    except Exception as e:
        logger.error(f"Error clearing API keys: {str(e)}")
        st.error(f"Ошибка удаления: {str(e)}")

def save_trading_parameters(trader, max_positions, position_size_pct, max_leverage, 
                          min_confidence_threshold, max_hold_time_hours, indicator_weights):
    """Save trading parameters"""
    try:
        # Update trader parameters
        trader.max_positions = max_positions
        trader.position_size_pct = position_size_pct
        trader.max_leverage = max_leverage
        trader.min_confidence_threshold = min_confidence_threshold
        trader.max_hold_time_hours = max_hold_time_hours
        trader.indicator_weights = indicator_weights
        
        # Save to session state for persistence
        st.session_state.trading_parameters = {
            'max_positions': max_positions,
            'position_size_pct': position_size_pct,
            'max_leverage': max_leverage,
            'min_confidence_threshold': min_confidence_threshold,
            'max_hold_time_hours': max_hold_time_hours,
            'indicator_weights': indicator_weights
        }
        
        st.success("✅ Торговые параметры сохранены")
        logger.info("Trading parameters updated")
        time.sleep(1)
        st.rerun()
    
    except Exception as e:
        logger.error(f"Error saving trading parameters: {str(e)}")
        st.error(f"Ошибка сохранения: {str(e)}")

def reset_trading_parameters(trader):
    """Reset trading parameters to defaults"""
    try:
        # Default values
        trader.max_positions = 3
        trader.position_size_pct = 33.33
        trader.max_leverage = 5.0
        trader.min_confidence_threshold = 70.0
        trader.max_hold_time_hours = 168
        trader.indicator_weights = {
            'technical': 0.35,
            'fundamental': 0.25,
            'sentiment': 0.20,
            'momentum': 0.20
        }
        
        # Clear saved parameters
        if 'trading_parameters' in st.session_state:
            del st.session_state.trading_parameters
        
        st.success("✅ Параметры сброшены к значениям по умолчанию")
        time.sleep(1)
        st.rerun()
    
    except Exception as e:
        logger.error(f"Error resetting trading parameters: {str(e)}")
        st.error(f"Ошибка сброса: {str(e)}")

def restart_system_components():
    """Restart system components"""
    try:
        # Clear and reinitialize components
        if 'trader' in st.session_state:
            api_key, secret_key = SecureDataManager.get_api_keys()
            demo_mode = st.session_state.get('demo_mode', True)
            st.session_state.trader = AdvancedTrader(api_key, secret_key, demo_mode)
        
        if 'signal_generator' in st.session_state:
            from signals.signal_generator import SignalGenerator
            st.session_state.signal_generator = SignalGenerator()
        
        st.success("✅ Компоненты системы перезапущены")
        logger.info("System components restarted")
        time.sleep(1)
        st.rerun()
    
    except Exception as e:
        logger.error(f"Error restarting components: {str(e)}")
        st.error(f"Ошибка перезапуска: {str(e)}")

def clear_system_caches():
    """Clear system caches"""
    try:
        # Clear signal generator cache
        if 'signal_generator' in st.session_state:
            st.session_state.signal_generator.clear_cache()
        
        # Clear news parser cache
        if 'trader' in st.session_state:
            st.session_state.trader.news_parser.clear_cache()
        
        st.success("✅ Кеши системы очищены")
        logger.info("System caches cleared")
        time.sleep(1)
        st.rerun()
    
    except Exception as e:
        logger.error(f"Error clearing caches: {str(e)}")
        st.error(f"Ошибка очистки: {str(e)}")

def export_trading_data():
    """Export trading data"""
    try:
        if 'trader' not in st.session_state:
            st.warning("⚠️ Торговая система не инициализирована")
            return
        
        trader = st.session_state.trader
        
        # Export to DataFrame
        trades_df = trader.trading_history.export_to_dataframe()
        
        if not trades_df.empty:
            # Convert to CSV
            csv_data = trades_df.to_csv(index=False)
            
            st.download_button(
                label="📥 Скачать данные торговли (CSV)",
                data=csv_data,
                file_name=f"trading_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.success(f"✅ Подготовлен экспорт {len(trades_df)} сделок")
        else:
            st.info("ℹ️ Нет данных для экспорта")
    
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        st.error(f"Ошибка экспорта: {str(e)}")

def clear_trading_history():
    """Clear trading history"""
    try:
        if 'trader' in st.session_state:
            trader = st.session_state.trader
            
            # Clear all trading data
            trader.trading_history.trades.clear()
            trader.trading_history.positions.clear()
            trader.notifications.notifications.clear()
            
            st.success("✅ История торговли очищена")
            logger.info("Trading history cleared")
        else:
            st.warning("⚠️ Торговая система не инициализирована")
        
        time.sleep(1)
        st.rerun()
    
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}")
        st.error(f"Ошибка очистки: {str(e)}")

def reset_all_settings():
    """Reset all settings to defaults"""
    try:
        # Clear all saved settings
        settings_keys = [
            'trading_parameters', 'notification_settings', 'technical_settings',
            'demo_mode', 'system_status'
        ]
        
        for key in settings_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        # Reset system status
        st.session_state.system_status = 'В ожидании'
        st.session_state.demo_mode = True
        
        # Reinitialize trader
        if 'trader' in st.session_state:
            api_key, secret_key = SecureDataManager.get_api_keys()
            st.session_state.trader = AdvancedTrader(api_key, secret_key, demo_mode=True)
        
        st.success("✅ Все настройки сброшены к значениям по умолчанию")
        logger.info("All settings reset to defaults")
        time.sleep(1)
        st.rerun()
    
    except Exception as e:
        logger.error(f"Error resetting settings: {str(e)}")
        st.error(f"Ошибка сброса настроек: {str(e)}")
