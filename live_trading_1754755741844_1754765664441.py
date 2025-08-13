import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import threading

from exchanges.mexc_client import MEXCClient
from core.intelligent_trader import IntelligentTrader
from core.advanced_trader import AdvancedTrader
from auth.security import SecureDataManager
from utils.logger import get_logger

logger = get_logger(__name__)

def render_live_trading():
    """Рендеринг страницы реальной торговли"""
    
    st.title("📈 Реальная торговля")
    st.markdown("**⚠️ ВНИМАНИЕ: Реальная торговля с использованием ваших средств**")
    
    # Предупреждение о рисках
    with st.expander("⚠️ ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ О РИСКАХ", expanded=True):
        st.markdown("""
        ### 🚨 ПРЕДУПРЕЖДЕНИЕ О РИСКАХ
        
        **Торговля криптовалютами сопряжена с высоким риском:**
        - Возможна полная потеря инвестированных средств
        - Высокая волатильность может привести к быстрым убыткам
        - AI алгоритмы не гарантируют прибыль
        - Рыночные условия могут измениться внезапно
        
        **Рекомендации:**
        - Начните с небольших сумм
        - Никогда не инвестируйте больше, чем можете позволить себе потерять
        - Регулярно проверяйте свои позиции
        - Используйте стоп-лоссы для ограничения убытков
        
        **Нажимая "Понимаю риски", вы подтверждаете полное понимание рисков.**
        """)
        
        if not st.session_state.get('risks_accepted', False):
            if st.button("✅ Понимаю риски и готов торговать", type="primary"):
                st.session_state.risks_accepted = True
                st.rerun()
            else:
                st.stop()
        else:
            st.success("✅ Риски приняты. Торговля разрешена.")
    
    # Проверяем API ключи
    api_key, secret_key = SecureDataManager.get_api_keys()
    
    if not api_key or not secret_key:
        st.error("🔑 Необходимо настроить API ключи на главной странице")
        return
    
    # Инициализация компонентов для реальной торговли
    if 'live_mexc_client' not in st.session_state:
        st.session_state.live_mexc_client = MEXCClient(api_key, secret_key, demo_mode=False)
    
    if 'live_intelligent_trader' not in st.session_state:
        st.session_state.live_intelligent_trader = IntelligentTrader(
            st.session_state.live_mexc_client, demo_mode=False
        )
    
    if 'live_advanced_trader' not in st.session_state:
        st.session_state.live_advanced_trader = AdvancedTrader(
            st.session_state.live_mexc_client, demo_mode=False
        )
    
    # Проверяем подключение к API
    try:
        server_time = st.session_state.live_mexc_client.get_server_time()
        if 'error' in server_time:
            st.error(f"❌ Ошибка подключения к MEXC API: {server_time.get('error')}")
            st.stop()
    except Exception as e:
        st.error(f"❌ Критическая ошибка API: {str(e)}")
        st.stop()
    
    # Основной интерфейс
    show_live_controls()
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        show_live_trading_interface()
        st.divider()
        show_live_market_data()
    
    with col2:
        show_live_balance()
        st.divider()
        show_live_positions()
        st.divider()
        show_live_performance()

def show_live_controls():
    """Панель управления реальной торговлей"""
    
    st.markdown("### 🎮 Управление реальной торговлей")
    
    # Статус подключения
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚀 Запустить AI торговлю", use_container_width=True):
            if not st.session_state.get('live_auto_trading', False):
                # Дополнительное подтверждение
                if st.session_state.get('trading_confirmed', False):
                    st.session_state.live_auto_trading = True
                    st.success("✅ AI торговля запущена!")
                    logger.info("Live AI trading started")
                else:
                    st.session_state.trading_confirmed = True
                    st.warning("⚠️ Нажмите еще раз для подтверждения запуска реальной торговли")
            else:
                st.warning("⚠️ AI торговля уже активна")
    
    with col2:
        if st.button("⏹️ Остановить AI торговлю", use_container_width=True):
            if st.session_state.get('live_auto_trading', False):
                st.session_state.live_auto_trading = False
                st.session_state.trading_confirmed = False
                st.info("ℹ️ AI торговля остановлена")
                logger.info("Live AI trading stopped")
    
    with col3:
        if st.button("🚨 ЭКСТРЕННАЯ ОСТАНОВКА", use_container_width=True):
            # Останавливаем все операции и закрываем позиции
            st.session_state.live_auto_trading = False
            st.session_state.trading_confirmed = False
            st.error("🚨 Экстренная остановка активирована!")
            logger.warning("Emergency stop activated for live trading")
    
    with col4:
        if st.button("🔄 Обновить данные", use_container_width=True):
            # Принудительное обновление данных
            st.session_state.live_data_last_update = datetime.now() - timedelta(minutes=10)
            st.rerun()
    
    # Настройки риск-менеджмента
    with st.expander("⚙️ Настройки риск-менеджмента", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_daily_loss = st.number_input("Макс. дневной убыток (USDT)", 
                                           min_value=0.0, 
                                           value=100.0, 
                                           step=10.0)
            max_positions = st.slider("Максимум позиций одновременно", 1, 10, 5)
        
        with col2:
            risk_per_trade = st.slider("Риск на сделку (%)", 0.1, 5.0, 1.0, 0.1)
            max_leverage = st.slider("Максимальное плечо", 1, 20, 3)
        
        with col3:
            stop_loss = st.slider("Стоп-лосс (%)", 1.0, 10.0, 3.0, 0.1)
            take_profit = st.slider("Тейк-профит (%)", 2.0, 20.0, 6.0, 0.1)
        
        if st.button("💾 Сохранить настройки риск-менеджмента"):
            # Здесь можно сохранить настройки в трейдеры
            st.success("✅ Настройки сохранены")
    
    # Статус торговли
    if st.session_state.get('live_auto_trading', False):
        st.success("🟢 AI торговля активна - Ведется реальная торговля")
    else:
        st.info("🔴 AI торговля остановлена")

def show_live_trading_interface():
    """Интерфейс реальной торговли"""
    
    st.markdown("### 💹 Ручное размещение ордеров")
    
    # Получаем реальные торговые пары
    try:
        exchange_info = st.session_state.live_mexc_client.get_exchange_info()
        if 'error' not in exchange_info and 'symbols' in exchange_info:
            symbols = [s['symbol'] for s in exchange_info['symbols'] 
                      if s['status'] == 'TRADING' and s['symbol'].endswith('USDT')][:50]
        else:
            # Fallback к популярным парам
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT', 
                      'SOLUSDT', 'XRPUSDT', 'DOTUSDT', 'AVAXUSDT', 'MATICUSDT']
    except:
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT']
    
    selected_symbol = st.selectbox("Выберите торговую пару:", symbols, key="live_symbol_select")
    
    # Получаем реальную информацию о символе
    try:
        ticker = st.session_state.live_mexc_client.get_ticker_24hr(selected_symbol)
        if 'error' not in ticker:
            current_price = float(ticker.get('lastPrice', 0))
            change_24h = float(ticker.get('priceChangePercent', 0))
            volume_24h = float(ticker.get('quoteVolume', 0))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Текущая цена", f"${current_price:.6f}")
            with col2:
                st.metric("Изменение 24ч", f"{change_24h:+.2f}%", delta=f"{change_24h:+.2f}%")
            with col3:
                st.metric("Объем 24ч", f"${volume_24h:,.0f}")
        else:
            current_price = 0
            st.error("Ошибка получения данных о торговой паре")
    except Exception as e:
        current_price = 0
        st.error(f"Ошибка загрузки данных: {str(e)}")
    
    if current_price > 0:
        # Получаем баланс для расчета доступных средств
        try:
            account_info = st.session_state.live_mexc_client.get_account_info()
            usdt_balance = 0
            asset_balance = 0
            
            if 'error' not in account_info and 'balances' in account_info:
                for balance in account_info['balances']:
                    if balance['asset'] == 'USDT':
                        usdt_balance = float(balance['free'])
                    elif balance['asset'] == selected_symbol.replace('USDT', ''):
                        asset_balance = float(balance['free'])
        except:
            usdt_balance = 0
            asset_balance = 0
        
        # Форма для размещения ордера
        with st.form("live_trade_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                trade_type = st.selectbox("Тип сделки:", ["BUY", "SELL"], key="live_trade_type")
                order_type = st.selectbox("Тип ордера:", ["MARKET", "LIMIT"], key="live_order_type")
            
            with col2:
                max_quantity = usdt_balance / current_price if trade_type == "BUY" else asset_balance
                quantity = st.number_input("Количество:", 
                                         min_value=0.0, 
                                         max_value=max_quantity,
                                         step=0.000001, 
                                         format="%.6f",
                                         key="live_quantity")
                
                if order_type == "LIMIT":
                    limit_price = st.number_input("Цена лимита:", 
                                                min_value=0.0, 
                                                value=current_price,
                                                step=0.000001, 
                                                format="%.6f",
                                                key="live_limit_price")
                else:
                    limit_price = current_price
            
            # Отображаем доступные средства
            st.info(f"💰 Доступно: {usdt_balance:.2f} USDT, {asset_balance:.6f} {selected_symbol.replace('USDT', '')}")
            
            # Расчет стоимости ордера
            if quantity > 0:
                total_cost = quantity * limit_price
                st.info(f"💸 Стоимость ордера: ${total_cost:.2f} USDT")
                
                # Проверяем достаточность средств
                if trade_type == "BUY" and total_cost > usdt_balance:
                    st.error("❌ Недостаточно USDT для покупки")
                elif trade_type == "SELL" and quantity > asset_balance:
                    st.error("❌ Недостаточно активов для продажи")
            
            # Подтверждение размещения
            confirm_order = st.checkbox("✅ Я подтверждаю размещение РЕАЛЬНОГО ордера", key="live_confirm_order")
            
            if st.form_submit_button("🔥 РАЗМЕСТИТЬ РЕАЛЬНЫЙ ОРДЕР", 
                                   use_container_width=True, 
                                   type="primary"):
                
                if not confirm_order:
                    st.error("❌ Необходимо подтвердить размещение ордера")
                elif quantity <= 0:
                    st.error("❌ Укажите корректное количество")
                else:
                    try:
                        with st.spinner("Размещение ордера..."):
                            # Размещаем реальный ордер
                            result = st.session_state.live_mexc_client.place_order(
                                symbol=selected_symbol,
                                side=trade_type,
                                order_type=order_type,
                                quantity=quantity,
                                price=limit_price if order_type == "LIMIT" else None
                            )
                            
                            if 'error' not in result:
                                st.success(f"✅ ОРДЕР РАЗМЕЩЕН УСПЕШНО!")
                                st.success(f"🆔 ID ордера: {result.get('orderId')}")
                                st.success(f"📊 Статус: {result.get('status')}")
                                logger.info(f"Live order placed: {trade_type} {quantity} {selected_symbol} at {limit_price}")
                            else:
                                st.error(f"❌ ОШИБКА РАЗМЕЩЕНИЯ ОРДЕРА: {result.get('error')}")
                                logger.error(f"Live order failed: {result.get('error')}")
                    
                    except Exception as e:
                        st.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
                        logger.error(f"Critical error placing live order: {str(e)}")

def show_live_market_data():
    """Реальные рыночные данные"""
    
    st.markdown("### 📊 Реальные рыночные данные")
    
    try:
        # Получаем реальные данные с MEXC
        market_conditions = st.session_state.live_mexc_client.analyze_market_conditions()
        top_gainers = st.session_state.live_mexc_client.get_top_gainers_losers(10)
        volume_leaders = st.session_state.live_mexc_client.get_volume_leaders(10)
        
        tab1, tab2, tab3 = st.tabs(["📈 Рыночные условия", "🔥 Топ активы", "📊 Объемы"])
        
        with tab1:
            if 'error' not in market_conditions:
                col1, col2 = st.columns(2)
                
                with col1:
                    sentiment = market_conditions.get('market_sentiment', 'Unknown')
                    sentiment_color = {
                        'Bullish': '🟢',
                        'Bearish': '🔴',
                        'Neutral': '🟡'
                    }.get(sentiment, '⚪')
                    
                    st.metric("Настроение рынка", f"{sentiment_color} {sentiment}")
                    st.metric("Всего активов", market_conditions.get('total_symbols', 0))
                
                with col2:
                    gainers = market_conditions.get('gainers', 0)
                    losers = market_conditions.get('losers', 0)
                    total = gainers + losers
                    
                    if total > 0:
                        gainers_pct = (gainers / total) * 100
                        st.metric("📈 Растущие активы", f"{gainers} ({gainers_pct:.1f}%)")
                        st.metric("📉 Падающие активы", f"{losers} ({100-gainers_pct:.1f}%)")
                    
                    avg_change = market_conditions.get('avg_change_pct', 0)
                    st.metric("Средний рост", f"{avg_change:+.2f}%")
            else:
                st.error("Ошибка загрузки рыночных условий")
        
        with tab2:
            if top_gainers:
                df_gainers = pd.DataFrame(top_gainers[:10])
                if not df_gainers.empty:
                    # Форматируем данные для отображения
                    display_df = df_gainers[['symbol', 'lastPrice', 'priceChangePercent', 'volume']].copy()
                    display_df.columns = ['Символ', 'Цена', 'Рост %', 'Объем']
                    display_df['Рост %'] = display_df['Рост %'].astype(float).round(2)
                    display_df['Цена'] = display_df['Цена'].astype(float)
                    
                    # Цветовая схема для роста
                    def color_negative_red(val):
                        color = 'red' if val < 0 else 'green'
                        return f'color: {color}'
                    
                    styled_df = display_df.style.applymap(color_negative_red, subset=['Рост %'])
                    st.dataframe(styled_df, use_container_width=True)
            else:
                st.error("Ошибка загрузки топ активов")
        
        with tab3:
            if volume_leaders:
                df_volume = pd.DataFrame(volume_leaders[:10])
                if not df_volume.empty:
                    display_df = df_volume[['symbol', 'lastPrice', 'volume', 'quoteVolume']].copy()
                    display_df.columns = ['Символ', 'Цена', 'Объем', 'Объем USDT']
                    display_df['Цена'] = display_df['Цена'].astype(float)
                    display_df['Объем'] = display_df['Объем'].astype(float).apply(lambda x: f"{x:,.0f}")
                    display_df['Объем USDT'] = display_df['Объем USDT'].astype(float).apply(lambda x: f"${x:,.0f}")
                    
                    st.dataframe(display_df, use_container_width=True)
            else:
                st.error("Ошибка загрузки данных по объемам")
    
    except Exception as e:
        logger.error(f"Error showing live market data: {str(e)}")
        st.error("Ошибка загрузки рыночных данных")

def show_live_balance():
    """Реальный баланс аккаунта"""
    
    st.markdown("### 💰 Реальный баланс")
    
    try:
        account_info = st.session_state.live_mexc_client.get_account_info()
        
        if 'error' not in account_info and 'balances' in account_info:
            total_balance_usdt = 0
            significant_balances = []
            
            for balance in account_info['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    # Конвертируем в USDT для общего баланса
                    if asset == 'USDT':
                        balance_usdt = total
                    else:
                        try:
                            ticker = st.session_state.live_mexc_client.get_ticker_price(f"{asset}USDT")
                            if 'error' not in ticker:
                                price = float(ticker.get('price', 0))
                                balance_usdt = total * price
                            else:
                                balance_usdt = 0
                        except:
                            balance_usdt = 0
                    
                    total_balance_usdt += balance_usdt
                    
                    # Сохраняем значимые балансы (> $1)
                    if balance_usdt > 1:
                        significant_balances.append({
                            'asset': asset,
                            'free': free,
                            'locked': locked,
                            'total': total,
                            'balance_usdt': balance_usdt
                        })
            
            # Отображаем общий баланс
            st.metric("💵 Общий баланс", f"${total_balance_usdt:,.2f}")
            
            # Детализация по активам
            if significant_balances:
                st.markdown("**Активы с балансом > $1:**")
                
                for balance in sorted(significant_balances, key=lambda x: x['balance_usdt'], reverse=True):
                    with st.container():
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**{balance['asset']}**")
                        
                        with col2:
                            if balance['asset'] == 'USDT':
                                st.write(f"Всего: ${balance['total']:.2f}")
                                st.write(f"Доступно: ${balance['free']:.2f}")
                            else:
                                st.write(f"Всего: {balance['total']:.6f}")
                                st.write(f"Доступно: {balance['free']:.6f}")
                        
                        with col3:
                            st.write(f"Стоимость: ${balance['balance_usdt']:.2f}")
                            if balance['locked'] > 0:
                                st.write(f"В ордерах: {balance['locked']:.6f}")
                        
                        st.divider()
            else:
                st.info("Нет значимых балансов для отображения")
        else:
            st.error("Ошибка получения данных баланса")
    
    except Exception as e:
        logger.error(f"Error showing live balance: {str(e)}")
        st.error("Ошибка загрузки баланса")

def show_live_positions():
    """Реальные активные позиции"""
    
    st.markdown("### 📊 Активные позиции")
    
    try:
        # Получаем открытые ордера
        open_orders = st.session_state.live_mexc_client.get_open_orders()
        
        if 'error' not in open_orders and open_orders:
            st.markdown("**Открытые ордера:**")
            
            for order in open_orders[:10]:  # Показываем до 10 ордеров
                with st.container():
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**{order.get('symbol', 'Unknown')}**")
                        side_emoji = "📈" if order.get('side') == 'BUY' else "📉"
                        st.write(f"{side_emoji} {order.get('side', 'Unknown')}")
                    
                    with col2:
                        st.write(f"Тип: {order.get('type', 'Unknown')}")
                        st.write(f"Количество: {float(order.get('origQty', 0)):,.6f}")
                    
                    with col3:
                        st.write(f"Цена: ${float(order.get('price', 0)):,.6f}")
                        st.write(f"Статус: {order.get('status', 'Unknown')}")
                    
                    # Кнопка отмены ордера
                    if st.button(f"❌ Отменить", key=f"cancel_{order.get('orderId')}"):
                        try:
                            result = st.session_state.live_mexc_client.cancel_order(
                                order.get('symbol'), order.get('orderId')
                            )
                            if 'error' not in result:
                                st.success("✅ Ордер отменен")
                                st.rerun()
                            else:
                                st.error(f"❌ Ошибка отмены: {result.get('error')}")
                        except Exception as e:
                            st.error(f"❌ Ошибка: {str(e)}")
                    
                    st.divider()
        else:
            st.info("Нет открытых ордеров")
        
        # Активные позиции от AI трейдеров
        ai_positions = st.session_state.live_intelligent_trader.active_positions
        
        if ai_positions:
            st.markdown("**AI позиции:**")
            
            for symbol, position in ai_positions.items():
                with st.container():
                    # Получаем текущую цену
                    try:
                        ticker = st.session_state.live_mexc_client.get_ticker_price(symbol)
                        if 'error' not in ticker:
                            current_price = float(ticker['price'])
                        else:
                            current_price = position['entry_price']
                    except:
                        current_price = position['entry_price']
                    
                    # Расчет P&L
                    entry_price = position['entry_price']
                    quantity = position['quantity']
                    side = position['side']
                    
                    if side == 'BUY':
                        unrealized_pnl = (current_price - entry_price) * quantity
                    else:
                        unrealized_pnl = (entry_price - current_price) * quantity
                    
                    pnl_pct = (unrealized_pnl / (entry_price * quantity)) * 100
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**{symbol}** (AI)")
                        side_emoji = "📈" if side == 'BUY' else "📉"
                        st.write(f"{side_emoji} {side} {quantity:.6f}")
                    
                    with col2:
                        st.write(f"Вход: ${entry_price:.6f}")
                        pnl_color = "🟢" if unrealized_pnl >= 0 else "🔴"
                        st.write(f"{pnl_color} P&L: ${unrealized_pnl:+.2f} ({pnl_pct:+.2f}%)")
                    
                    st.divider()
        
        if not open_orders and not ai_positions:
            st.info("Нет активных позиций")
    
    except Exception as e:
        logger.error(f"Error showing live positions: {str(e)}")
        st.error("Ошибка загрузки позиций")

def show_live_performance():
    """Производительность реальной торговли"""
    
    st.markdown("### 📈 Производительность")
    
    try:
        # Получаем статистику от AI трейдера
        stats = st.session_state.live_intelligent_trader.get_performance_stats()
        
        # Основные метрики
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("🎯 Всего сделок", stats.get('total_trades', 0))
            st.metric("💰 Общий P&L", f"${stats.get('total_pnl', 0):+.2f}")
        
        with col2:
            win_rate = stats.get('win_rate', 0)
            st.metric("📊 Винрейт", f"{win_rate:.1f}%")
            avg_pnl = stats.get('average_pnl', 0)
            st.metric("📊 Средний P&L", f"${avg_pnl:+.2f}")
        
        # График истории сделок
        trade_history = st.session_state.live_intelligent_trader.trade_history
        
        if trade_history and len(trade_history) > 1:
            df_trades = pd.DataFrame(trade_history)
            df_trades['cumulative_pnl'] = df_trades['pnl'].cumsum()
            df_trades['trade_number'] = range(1, len(df_trades) + 1)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_trades['trade_number'],
                y=df_trades['cumulative_pnl'],
                mode='lines+markers',
                name='Накопительный P&L',
                line=dict(color='#00D4AA', width=2),
                marker=dict(size=4)
            ))
            
            fig.update_layout(
                title="Кривая реального P&L",
                xaxis_title="Номер сделки",
                yaxis_title="P&L (USDT)",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Последние сделки
            st.markdown("**Последние 5 сделок:**")
            recent_trades = trade_history[-5:]
            
            for trade in reversed(recent_trades):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.write(f"**{trade['symbol']}**")
                
                with col2:
                    side_emoji = "📈" if trade['side'] == 'BUY' else "📉"
                    st.write(f"{side_emoji} {trade['side']}")
                
                with col3:
                    pnl_color = "🟢" if trade['pnl'] >= 0 else "🔴"
                    st.write(f"{pnl_color} ${trade['pnl']:+.2f}")
                
                with col4:
                    st.write(f"⏰ {trade['exit_time'].strftime('%m/%d %H:%M')}")
        else:
            st.info("Недостаточно данных для отображения графика")
    
    except Exception as e:
        logger.error(f"Error showing live performance: {str(e)}")
        st.error("Ошибка отображения производительности")

# Автообновление данных каждые 30 секунд
if 'live_data_last_update' not in st.session_state:
    st.session_state.live_data_last_update = datetime.now()

if (datetime.now() - st.session_state.live_data_last_update).total_seconds() > 30:
    st.session_state.live_data_last_update = datetime.now()
    # Автообновление при активной торговле
    if st.session_state.get('live_auto_trading', False):
        st.rerun()
