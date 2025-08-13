import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time

from trading.advanced_trader import AdvancedTrader
from signals.signal_generator import SignalGenerator
from auth.security import SecureDataManager
from utils.logger import get_logger

logger = get_logger(__name__)

def show():
    """Display the trading panel"""
    try:
        st.title("📈 Торговая панель")
        
        # Initialize components
        if 'trader' not in st.session_state:
            api_key, secret_key = SecureDataManager.get_api_keys()
            demo_mode = st.session_state.get('demo_mode', True)
            st.session_state.trader = AdvancedTrader(api_key, secret_key, demo_mode)
        
        if 'signal_generator' not in st.session_state:
            st.session_state.signal_generator = SignalGenerator()
        
        trader = st.session_state.trader
        signal_generator = st.session_state.signal_generator
        
        # Main trading interface
        tab1, tab2, tab3, tab4 = st.tabs(["🎯 Сигналы", "⚡ Быстрая торговля", "🔍 Анализ символа", "⚙️ Управление позициями"])
        
        with tab1:
            show_trading_signals(trader, signal_generator)
        
        with tab2:
            show_quick_trading(trader)
        
        with tab3:
            show_symbol_analysis(trader, signal_generator)
        
        with tab4:
            show_position_management(trader)
        
    except Exception as e:
        logger.error(f"Error in trading panel: {str(e)}")
        st.error(f"Ошибка загрузки торговой панели: {str(e)}")

def show_trading_signals(trader, signal_generator):
    """Display trading signals"""
    try:
        st.markdown("### 🎯 Торговые сигналы")
        
        # Signal generation controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            confidence_threshold = st.slider("Минимальная уверенность сигнала", 50, 95, 70, step=5)
        
        with col2:
            if st.button("🔄 Обновить сигналы", use_container_width=True):
                signal_generator.clear_cache()
                st.rerun()
        
        with col3:
            auto_trade = st.checkbox("🤖 Автоторговля", help="Автоматически выполнять сигналы с высокой уверенностью")
        
        # Generate signals
        with st.spinner("Генерация торговых сигналов..."):
            opportunities = trader.scan_for_opportunities(limit=30)
        
        if opportunities:
            # Filter by confidence
            filtered_signals = [opp for opp in opportunities if opp['confidence'] >= confidence_threshold]
            
            if filtered_signals:
                st.success(f"🎯 Найдено {len(filtered_signals)} сигналов")
                
                # Signals table with actions
                for i, signal in enumerate(filtered_signals[:10]):
                    with st.container():
                        col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 2, 1])
                        
                        with col1:
                            st.write(f"**{signal['symbol']}**")
                            st.caption(f"${float(signal['current_price']):.6f}")
                        
                        with col2:
                            action_color = "🟢" if signal['action'] == 'BUY' else "🔴" if signal['action'] == 'SELL' else "🟡"
                            st.write(f"{action_color} {signal['action']}")
                        
                        with col3:
                            confidence = signal['confidence']
                            confidence_color = "🟢" if confidence >= 80 else "🟡" if confidence >= 65 else "🔴"
                            st.write(f"{confidence_color} {confidence:.1f}%")
                        
                        with col4:
                            change_24h = float(signal['change_24h'])
                            change_color = "🟢" if change_24h > 0 else "🔴"
                            st.write(f"{change_color} {change_24h:+.2f}%")
                        
                        with col5:
                            st.caption(signal['reasoning'])
                        
                        with col6:
                            button_key = f"trade_{signal['symbol']}_{i}"
                            if st.button("▶️", key=button_key, help="Выполнить сигнал"):
                                execute_trade_from_signal(trader, signal)
                        
                        st.divider()
                
                # Auto-trading for high confidence signals
                if auto_trade:
                    high_confidence_signals = [s for s in filtered_signals if s['confidence'] >= 85]
                    
                    if high_confidence_signals:
                        st.info(f"🤖 Автоторговля: Найдено {len(high_confidence_signals)} сигналов с высокой уверенностью")
                        
                        for signal in high_confidence_signals[:3]:  # Limit auto trades
                            try:
                                result = execute_trade_from_signal(trader, signal, auto_mode=True)
                                if result.get('success'):
                                    st.success(f"✅ Автоматически выполнен {signal['action']} {signal['symbol']}")
                                else:
                                    st.warning(f"⚠️ Не удалось выполнить автоторговлю для {signal['symbol']}: {result.get('message', 'Неизвестная ошибка')}")
                            except Exception as e:
                                logger.error(f"Auto-trade error for {signal['symbol']}: {str(e)}")
            else:
                st.warning(f"Нет сигналов с уверенностью ≥ {confidence_threshold}%")
        else:
            st.info("🔍 Торговые сигналы не найдены")
    
    except Exception as e:
        logger.error(f"Error in trading signals: {str(e)}")
        st.error("Ошибка генерации торговых сигналов")

def show_quick_trading(trader):
    """Display quick trading interface"""
    try:
        st.markdown("### ⚡ Быстрая торговля")
        
        # Trading form
        with st.form("quick_trade_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                symbol = st.text_input("Символ", placeholder="BTCUSDT", help="Введите торговый символ")
                action = st.selectbox("Действие", ["BUY", "SELL"])
            
            with col2:
                trade_amount = st.number_input("Сумма ($)", min_value=10.0, max_value=10000.0, value=100.0, step=10.0)
                use_leverage = st.checkbox("Использовать плечо", help="Применить кредитное плечо для сделки")
            
            # Advanced options
            with st.expander("🔧 Дополнительные параметры"):
                col1, col2 = st.columns(2)
                
                with col1:
                    stop_loss_pct = st.number_input("Стоп-лосс (%)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
                    take_profit_pct = st.number_input("Тейк-профит (%)", min_value=1.0, max_value=50.0, value=10.0, step=0.5)
                
                with col2:
                    if use_leverage:
                        leverage = st.slider("Плечо", 1.0, 5.0, 2.0, step=0.5)
                    else:
                        leverage = 1.0
                    
                    order_type = st.selectbox("Тип ордера", ["MARKET", "LIMIT"])
            
            # Submit button
            submitted = st.form_submit_button("🚀 Выполнить сделку", use_container_width=True)
            
            if submitted and symbol:
                execute_manual_trade(trader, symbol, action, trade_amount, leverage, stop_loss_pct, take_profit_pct, order_type)
        
        st.markdown("---")
        
        # Quick market data
        if st.checkbox("📊 Показать рыночные данные"):
            show_quick_market_data(trader)
    
    except Exception as e:
        logger.error(f"Error in quick trading: {str(e)}")
        st.error("Ошибка быстрой торговли")

def show_symbol_analysis(trader, signal_generator):
    """Display detailed symbol analysis"""
    try:
        st.markdown("### 🔍 Анализ символа")
        
        # Symbol input
        col1, col2 = st.columns([3, 1])
        
        with col1:
            symbol = st.text_input("Символ для анализа", placeholder="BTCUSDT")
        
        with col2:
            if st.button("🔍 Анализировать", use_container_width=True):
                if symbol:
                    st.session_state.analysis_symbol = symbol
                    st.rerun()
        
        # Perform analysis if symbol is provided
        analysis_symbol = st.session_state.get('analysis_symbol', '')
        
        if analysis_symbol:
            st.markdown(f"#### 📊 Анализ {analysis_symbol}")
            
            try:
                # Get market data
                with st.spinner("Получение рыночных данных..."):
                    klines_data = trader.mexc_client.get_klines(analysis_symbol, '1h', 100)
                
                if 'error' in klines_data:
                    st.error(f"Ошибка получения данных: {klines_data['error']}")
                    return
                
                # Convert to DataFrame
                df = trader._convert_klines_to_df(klines_data)
                
                if len(df) < 20:
                    st.warning("Недостаточно данных для анализа")
                    return
                
                # Generate detailed analysis
                with st.spinner("Выполнение анализа..."):
                    analysis_result = trader.analyze_symbol(analysis_symbol)
                    signal = signal_generator.generate_trading_signal(analysis_symbol, df)
                
                # Display results
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### 📈 Торговый сигнал")
                    
                    if signal:
                        action = signal['action']
                        confidence = signal['confidence']
                        
                        action_color = "🟢" if action == 'BUY' else "🔴" if action == 'SELL' else "🟡"
                        confidence_color = "🟢" if confidence >= 80 else "🟡" if confidence >= 65 else "🔴"
                        
                        st.metric("Действие", f"{action_color} {action}")
                        st.metric("Уверенность", f"{confidence_color} {confidence:.1f}%")
                        st.metric("Сила сигнала", signal.get('strength', 'Unknown'))
                        st.metric("Уровень риска", signal.get('risk_level', 'Unknown'))
                        
                        st.markdown("**Обоснование:**")
                        st.write(signal.get('reasoning', 'Нет данных'))
                    else:
                        st.warning("Не удалось сгенерировать сигнал")
                
                with col2:
                    st.markdown("##### 🔢 Компоненты анализа")
                    
                    if signal and 'components' in signal:
                        components = signal['components']
                        
                        for component, score in components.items():
                            component_name = {
                                'technical_score': 'Технический анализ',
                                'price_action_score': 'Ценовое действие',
                                'volume_score': 'Анализ объемов',
                                'sentiment_score': 'Анализ настроений'
                            }.get(component, component)
                            
                            st.metric(component_name, f"{score:.1f}/100")
                
                # Price chart
                st.markdown("##### 📊 График цены")
                
                fig = go.Figure()
                
                # Candlestick chart
                fig.add_trace(go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name=analysis_symbol
                ))
                
                # Add moving averages
                sma_20 = df['close'].rolling(20).mean()
                sma_50 = df['close'].rolling(50).mean()
                
                fig.add_trace(go.Scatter(x=df.index, y=sma_20, name='SMA 20', line=dict(color='orange')))
                fig.add_trace(go.Scatter(x=df.index, y=sma_50, name='SMA 50', line=dict(color='red')))
                
                fig.update_layout(
                    title=f"{analysis_symbol} - Анализ цены",
                    xaxis_title="Время",
                    yaxis_title="Цена ($)",
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Execute trade button
                if signal and signal['confidence'] >= 65:
                    st.markdown("##### ⚡ Выполнить сделку")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        trade_amount = st.number_input("Сумма сделки ($)", min_value=10.0, value=100.0, step=10.0)
                    
                    with col2:
                        use_signal_leverage = st.checkbox("Использовать плечо", value=signal['confidence'] >= 85)
                    
                    with col3:
                        if st.button("🚀 Выполнить по сигналу", use_container_width=True):
                            execute_trade_from_analysis(trader, analysis_symbol, signal, trade_amount, use_signal_leverage)
            
            except Exception as e:
                logger.error(f"Error in symbol analysis: {str(e)}")
                st.error(f"Ошибка анализа символа: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in symbol analysis interface: {str(e)}")
        st.error("Ошибка интерфейса анализа символа")

def show_position_management(trader):
    """Display position management interface"""
    try:
        st.markdown("### ⚙️ Управление позициями")
        
        # Get current positions
        positions = trader.trading_history.get_current_positions()
        
        if positions:
            st.success(f"📊 Открыто позиций: {len(positions)}")
            
            # Position management for each position
            for i, position in enumerate(positions):
                with st.expander(f"📈 {position.symbol} - {position.side}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Количество", f"{position.quantity:.4f}")
                        st.metric("Цена входа", f"${position.entry_price:.6f}")
                    
                    with col2:
                        st.metric("Текущая цена", f"${position.current_price:.6f}")
                        st.metric("Время входа", position.entry_time.strftime('%Y-%m-%d %H:%M'))
                    
                    with col3:
                        pnl_color = "🟢" if position.unrealized_pnl_pct > 0 else "🔴"
                        st.metric("П/У %", f"{pnl_color} {position.unrealized_pnl_pct:+.2f}%")
                        st.metric("П/У $", f"${position.unrealized_pnl:+.2f}")
                    
                    # Position actions
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button(f"💰 Закрыть", key=f"close_{i}"):
                            close_position(trader, position)
                    
                    with col2:
                        if st.button(f"📊 Анализ", key=f"analyze_{i}"):
                            st.session_state.analysis_symbol = position.symbol
                            st.rerun()
                    
                    with col3:
                        if position.unrealized_pnl_pct > 10:
                            if st.button(f"🎯 Частичное закрытие", key=f"partial_{i}"):
                                partial_close_position(trader, position, 0.5)
                    
                    with col4:
                        if position.unrealized_pnl_pct < -5:
                            if st.button(f"⚠️ Стоп-лосс", key=f"stop_{i}"):
                                close_position(trader, position, reason="Стоп-лосс")
            
            # Bulk actions
            st.markdown("#### 🔧 Массовые действия")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💰 Закрыть все прибыльные", use_container_width=True):
                    close_profitable_positions(trader)
            
            with col2:
                if st.button("⚠️ Закрыть все убыточные", use_container_width=True):
                    close_losing_positions(trader)
            
            with col3:
                if st.button("🚨 Закрыть все позиции", use_container_width=True):
                    close_all_positions(trader)
        
        else:
            st.info("📭 Нет открытых позиций")
            
            if st.button("🎯 Найти торговые возможности"):
                st.session_state.navigation = "🏠 Главная панель"
                st.rerun()
        
        # Portfolio optimization
        st.markdown("---")
        st.markdown("#### 🎯 Оптимизация портфеля")
        
        if hasattr(trader, 'optimize_portfolio'):
            optimization = trader.optimize_portfolio()
            
            if optimization.get('status') == 'analyzed':
                score = optimization.get('optimization_score', 0)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Оценка оптимизации", f"{score:.1f}/100")
                
                with col2:
                    if score < 70:
                        st.warning("⚠️ Требуется оптимизация портфеля")
                    else:
                        st.success("✅ Портфель хорошо оптимизирован")
                
                # Show recommendations
                recommendations = optimization.get('recommendations', [])
                if recommendations:
                    st.markdown("**Рекомендации по оптимизации:**")
                    for rec in recommendations:
                        st.write(f"• {rec.get('reason', 'Рекомендация по оптимизации')}")
    
    except Exception as e:
        logger.error(f"Error in position management: {str(e)}")
        st.error("Ошибка управления позициями")

# Helper functions

def execute_trade_from_signal(trader, signal, auto_mode=False):
    """Execute trade based on signal"""
    try:
        symbol = signal['symbol']
        action = signal['action']
        confidence = signal['confidence']
        reasoning = signal['reasoning']
        
        result = trader.execute_trade(symbol, action, confidence, reasoning)
        
        if not auto_mode:
            if result.get('success'):
                st.success(f"✅ Сделка выполнена: {action} {symbol}")
                st.info(f"ID сделки: {result.get('trade_id')}")
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"❌ Ошибка выполнения сделки: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing trade from signal: {str(e)}")
        if not auto_mode:
            st.error(f"Ошибка выполнения сделки: {str(e)}")
        return {'success': False, 'message': str(e)}

def execute_manual_trade(trader, symbol, action, amount, leverage, stop_loss_pct, take_profit_pct, order_type):
    """Execute manual trade"""
    try:
        # Get current price
        ticker = trader.mexc_client.get_ticker_price(symbol)
        if 'error' in ticker:
            st.error(f"Ошибка получения цены: {ticker['error']}")
            return
        
        current_price = float(ticker.get('price', 0))
        if current_price <= 0:
            st.error("Некорректная цена символа")
            return
        
        # Calculate quantity
        effective_amount = amount * leverage
        quantity = effective_amount / current_price
        
        # Create synthetic signal for execution
        signal = {
            'symbol': symbol,
            'action': action,
            'confidence': 75.0,  # Manual trades get default confidence
            'reasoning': f"Ручная торговля: {action} {symbol} на сумму ${amount} с плечом {leverage}x"
        }
        
        result = execute_trade_from_signal(trader, signal)
        
        if result.get('success'):
            st.success(f"✅ Ручная сделка выполнена!")
            st.info(f"Символ: {symbol}, Действие: {action}, Сумма: ${amount}, Плечо: {leverage}x")
        
    except Exception as e:
        logger.error(f"Error in manual trade: {str(e)}")
        st.error(f"Ошибка ручной торговли: {str(e)}")

def execute_trade_from_analysis(trader, symbol, signal, amount, use_leverage):
    """Execute trade from detailed analysis"""
    try:
        leverage = 2.0 if use_leverage and signal['confidence'] >= 85 else 1.0
        
        # Update signal reasoning with amount and leverage info
        signal['reasoning'] += f" | Сумма: ${amount}, Плечо: {leverage}x"
        
        result = execute_trade_from_signal(trader, signal)
        
        if result.get('success'):
            st.balloons()
            st.success(f"🎉 Сделка по анализу выполнена успешно!")
        
    except Exception as e:
        logger.error(f"Error executing trade from analysis: {str(e)}")
        st.error(f"Ошибка выполнения сделки по анализу: {str(e)}")

def close_position(trader, position, reason="Ручное закрытие"):
    """Close a specific position"""
    try:
        # Find corresponding trade
        open_trades = trader.trading_history.get_open_trades()
        trade = next((t for t in open_trades if t.symbol == position.symbol), None)
        
        if trade:
            result = trader._close_position(trade, reason)
            
            if result.get('action') == 'closed':
                profit_pct = result.get('profit_pct', 0)
                profit_emoji = "📈" if profit_pct > 0 else "📉"
                st.success(f"{profit_emoji} Позиция {position.symbol} закрыта: {profit_pct:+.2f}%")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Ошибка закрытия позиции: {result.get('message', 'Неизвестная ошибка')}")
        else:
            st.error("Не найдена соответствующая сделка")
            
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}")
        st.error(f"Ошибка закрытия позиции: {str(e)}")

def partial_close_position(trader, position, close_ratio=0.5):
    """Partially close a position"""
    try:
        st.info(f"Частичное закрытие {close_ratio:.0%} позиции {position.symbol}")
        # This would require more complex implementation
        # For now, just show info
        st.warning("Функция частичного закрытия в разработке")
        
    except Exception as e:
        logger.error(f"Error in partial close: {str(e)}")
        st.error(f"Ошибка частичного закрытия: {str(e)}")

def close_profitable_positions(trader):
    """Close all profitable positions"""
    try:
        positions = trader.trading_history.get_current_positions()
        profitable_positions = [p for p in positions if p.unrealized_pnl_pct > 0]
        
        if profitable_positions:
            for position in profitable_positions:
                close_position(trader, position, "Массовое закрытие прибыльных")
            
            st.success(f"✅ Закрыто {len(profitable_positions)} прибыльных позиций")
        else:
            st.info("Нет прибыльных позиций для закрытия")
    
    except Exception as e:
        logger.error(f"Error closing profitable positions: {str(e)}")
        st.error(f"Ошибка закрытия прибыльных позиций: {str(e)}")

def close_losing_positions(trader):
    """Close all losing positions"""
    try:
        positions = trader.trading_history.get_current_positions()
        losing_positions = [p for p in positions if p.unrealized_pnl_pct < 0]
        
        if losing_positions:
            for position in losing_positions:
                close_position(trader, position, "Массовое закрытие убыточных")
            
            st.warning(f"⚠️ Закрыто {len(losing_positions)} убыточных позиций")
        else:
            st.info("Нет убыточных позиций для закрытия")
    
    except Exception as e:
        logger.error(f"Error closing losing positions: {str(e)}")
        st.error(f"Ошибка закрытия убыточных позиций: {str(e)}")

def close_all_positions(trader):
    """Close all positions"""
    try:
        positions = trader.trading_history.get_current_positions()
        
        if positions:
            # Confirm action
            if st.button("🚨 ПОДТВЕРДИТЬ ЗАКРЫТИЕ ВСЕХ ПОЗИЦИЙ", type="primary"):
                for position in positions:
                    close_position(trader, position, "Массовое закрытие всех позиций")
                
                st.success(f"✅ Закрыто {len(positions)} позиций")
        else:
            st.info("Нет позиций для закрытия")
    
    except Exception as e:
        logger.error(f"Error closing all positions: {str(e)}")
        st.error(f"Ошибка закрытия всех позиций: {str(e)}")

def show_quick_market_data(trader):
    """Show quick market data overview"""
    try:
        st.markdown("#### 📊 Быстрые рыночные данные")
        
        # Get top gainers and losers
        with st.spinner("Загрузка рыночных данных..."):
            gainers = trader.mexc_client.get_top_gainers_losers(10)
        
        if gainers:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**🟢 Топ растущие**")
                for ticker in gainers[:5]:
                    change = float(ticker.get('priceChangePercent', 0))
                    if change > 0:
                        st.write(f"{ticker['symbol']}: +{change:.2f}%")
            
            with col2:
                st.markdown("**🔴 Топ падающие**")
                sorted_tickers = sorted(gainers, key=lambda x: float(x.get('priceChangePercent', 0)))
                for ticker in sorted_tickers[:5]:
                    change = float(ticker.get('priceChangePercent', 0))
                    if change < 0:
                        st.write(f"{ticker['symbol']}: {change:.2f}%")
        
    except Exception as e:
        logger.error(f"Error in quick market data: {str(e)}")
        st.error("Ошибка загрузки рыночных данных")
