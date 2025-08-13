import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

from exchanges.mexc_client import MEXCClient
from core.intelligent_trader import IntelligentTrader
from core.advanced_trader import AdvancedTrader
from auth.security import SecureDataManager
from utils.logger import get_logger

logger = get_logger(__name__)

def render_trade_history():
    """Рендеринг страницы истории сделок"""
    
    st.title("📊 История сделок")
    st.markdown("**Детальный анализ всех торговых операций**")
    
    # Проверяем API ключи
    api_key, secret_key = SecureDataManager.get_api_keys()
    
    if not api_key or not secret_key:
        st.warning("🔑 Необходимо настроить API ключи на главной странице")
        return
    
    # Инициализация компонентов
    if 'history_mexc_client' not in st.session_state:
        st.session_state.history_mexc_client = MEXCClient(api_key, secret_key, demo_mode=True)
    
    if 'history_intelligent_trader' not in st.session_state:
        st.session_state.history_intelligent_trader = IntelligentTrader(
            st.session_state.history_mexc_client, demo_mode=True
        )
    
    if 'history_advanced_trader' not in st.session_state:
        st.session_state.history_advanced_trader = AdvancedTrader(
            st.session_state.history_mexc_client, demo_mode=True
        )
    
    # Переключатель между демо и реальным режимом
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 📋 Фильтры и настройки")
    
    with col2:
        mode = st.selectbox("Режим данных:", ["Демо торговля", "Реальная торговля"], key="history_mode")
        demo_mode = mode == "Демо торговля"
    
    # Основной контент
    show_history_filters()
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        show_trade_list(demo_mode)
        st.divider()
        show_performance_analysis(demo_mode)
    
    with col2:
        show_trade_statistics(demo_mode)
        st.divider()
        show_export_options(demo_mode)

def show_history_filters():
    """Фильтры для истории сделок"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        date_range = st.selectbox(
            "Период:",
            ["Сегодня", "7 дней", "30 дней", "90 дней", "Все время"],
            index=2
        )
    
    with col2:
        trade_type = st.selectbox(
            "Тип сделки:",
            ["Все", "BUY", "SELL"]
        )
    
    with col3:
        symbol_filter = st.text_input("Фильтр по символу:", placeholder="Например: BTC")
    
    with col4:
        min_pnl = st.number_input("Минимальный P&L:", value=None, placeholder="Не ограничено")
    
    # Сохраняем фильтры в session state
    st.session_state.history_filters = {
        'date_range': date_range,
        'trade_type': trade_type,
        'symbol_filter': symbol_filter.upper() if symbol_filter else '',
        'min_pnl': min_pnl
    }

def show_trade_list(demo_mode: bool):
    """Список сделок"""
    
    st.markdown("### 📜 Список сделок")
    
    try:
        # Получаем историю сделок в зависимости от режима
        if demo_mode:
            if 'demo_intelligent_trader' in st.session_state:
                trade_history = st.session_state.demo_intelligent_trader.trade_history
            else:
                trade_history = st.session_state.history_intelligent_trader.trade_history
        else:
            if 'live_intelligent_trader' in st.session_state:
                trade_history = st.session_state.live_intelligent_trader.trade_history
            else:
                # Получаем реальную историю с биржи
                trade_history = get_real_trade_history()
        
        if not trade_history:
            st.info("📭 История сделок пуста")
            return
        
        # Применяем фильтры
        filtered_trades = apply_trade_filters(trade_history)
        
        if not filtered_trades:
            st.info("🔍 Нет сделок, соответствующих фильтрам")
            return
        
        # Конвертируем в DataFrame
        df = pd.DataFrame(filtered_trades)
        
        # Форматируем данные для отображения
        display_df = df.copy()
        display_df['entry_time'] = pd.to_datetime(display_df['entry_time']).dt.strftime('%Y-%m-%d %H:%M')
        display_df['exit_time'] = pd.to_datetime(display_df['exit_time']).dt.strftime('%Y-%m-%d %H:%M')
        display_df['entry_price'] = display_df['entry_price'].round(6)
        display_df['exit_price'] = display_df['exit_price'].round(6)
        display_df['quantity'] = display_df['quantity'].round(6)
        display_df['pnl'] = display_df['pnl'].round(2)
        display_df['pnl_pct'] = display_df['pnl_pct'].round(2)
        
        # Выбираем колонки для отображения
        display_columns = ['symbol', 'side', 'entry_time', 'exit_time', 
                          'entry_price', 'exit_price', 'quantity', 'pnl', 'pnl_pct', 'reason']
        
        display_df = display_df[display_columns].copy()
        display_df.columns = ['Символ', 'Сторона', 'Время входа', 'Время выхода',
                             'Цена входа', 'Цена выхода', 'Количество', 'P&L ($)', 'P&L (%)', 'Причина']
        
        # Применяем цветовую схему
        def highlight_pnl(row):
            if row['P&L ($)'] > 0:
                return ['background-color: rgba(0, 255, 0, 0.1)'] * len(row)
            elif row['P&L ($)'] < 0:
                return ['background-color: rgba(255, 0, 0, 0.1)'] * len(row)
            else:
                return [''] * len(row)
        
        styled_df = display_df.style.apply(highlight_pnl, axis=1)
        
        # Отображаем таблицу
        st.dataframe(styled_df, use_container_width=True)
        
        # Пагинация для большого количества сделок
        if len(filtered_trades) > 50:
            st.info(f"📄 Показано последние 50 из {len(filtered_trades)} сделок")
    
    except Exception as e:
        logger.error(f"Error showing trade list: {str(e)}")
        st.error("Ошибка отображения списка сделок")

def apply_trade_filters(trade_history: list) -> list:
    """Применение фильтров к истории сделок"""
    
    try:
        filtered_trades = trade_history.copy()
        filters = st.session_state.get('history_filters', {})
        
        # Фильтр по дате
        date_range = filters.get('date_range', 'Все время')
        if date_range != 'Все время':
            days_map = {
                'Сегодня': 1,
                '7 дней': 7,
                '30 дней': 30,
                '90 дней': 90
            }
            
            days = days_map.get(date_range, 30)
            cutoff_date = datetime.now() - timedelta(days=days)
            
            filtered_trades = [
                trade for trade in filtered_trades
                if trade['exit_time'] >= cutoff_date
            ]
        
        # Фильтр по типу сделки
        trade_type = filters.get('trade_type', 'Все')
        if trade_type != 'Все':
            filtered_trades = [
                trade for trade in filtered_trades
                if trade['side'] == trade_type
            ]
        
        # Фильтр по символу
        symbol_filter = filters.get('symbol_filter', '')
        if symbol_filter:
            filtered_trades = [
                trade for trade in filtered_trades
                if symbol_filter in trade['symbol']
            ]
        
        # Фильтр по минимальному P&L
        min_pnl = filters.get('min_pnl')
        if min_pnl is not None:
            filtered_trades = [
                trade for trade in filtered_trades
                if trade['pnl'] >= min_pnl
            ]
        
        # Сортировка по времени выхода (новые сначала)
        filtered_trades.sort(key=lambda x: x['exit_time'], reverse=True)
        
        return filtered_trades[:50]  # Ограничиваем количество
    
    except Exception as e:
        logger.error(f"Error applying trade filters: {str(e)}")
        return trade_history

def get_real_trade_history():
    """Получение реальной истории сделок с биржи"""
    
    try:
        # Здесь можно получить реальную историю с MEXC API
        # Для демонстрации возвращаем пустой список
        return []
    except Exception as e:
        logger.error(f"Error getting real trade history: {str(e)}")
        return []

def show_performance_analysis(demo_mode: bool):
    """Анализ производительности"""
    
    st.markdown("### 📈 Анализ производительности")
    
    try:
        # Получаем данные торговли
        if demo_mode:
            if 'demo_intelligent_trader' in st.session_state:
                trade_history = st.session_state.demo_intelligent_trader.trade_history
            else:
                trade_history = st.session_state.history_intelligent_trader.trade_history
        else:
            if 'live_intelligent_trader' in st.session_state:
                trade_history = st.session_state.live_intelligent_trader.trade_history
            else:
                trade_history = []
        
        if not trade_history:
            st.info("Недостаточно данных для анализа производительности")
            return
        
        # Применяем фильтры
        filtered_trades = apply_trade_filters(trade_history)
        
        if not filtered_trades:
            st.info("Нет сделок для анализа после применения фильтров")
            return
        
        df = pd.DataFrame(filtered_trades)
        
        # График кривой P&L
        df_sorted = df.sort_values('exit_time')
        df_sorted['cumulative_pnl'] = df_sorted['pnl'].cumsum()
        df_sorted['trade_number'] = range(1, len(df_sorted) + 1)
        
        tab1, tab2, tab3 = st.tabs(["📊 Кривая P&L", "📈 Распределение", "⏱️ Временной анализ"])
        
        with tab1:
            fig = go.Figure()
            
            # Кривая накопительного P&L
            fig.add_trace(go.Scatter(
                x=df_sorted['trade_number'],
                y=df_sorted['cumulative_pnl'],
                mode='lines+markers',
                name='Накопительный P&L',
                line=dict(color='#00D4AA', width=2),
                marker=dict(size=4)
            ))
            
            # Добавляем нулевую линию
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            
            fig.update_layout(
                title="Кривая накопительного P&L",
                xaxis_title="Номер сделки",
                yaxis_title="P&L (USDT)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Гистограмма P&L
            fig_hist = px.histogram(
                df,
                x='pnl',
                nbins=20,
                title="Распределение P&L по сделкам",
                color_discrete_sequence=['#00D4AA']
            )
            
            fig_hist.update_layout(
                xaxis_title="P&L (USDT)",
                yaxis_title="Количество сделок",
                height=400
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Круговая диаграмма прибыльных/убыточных сделок
            winning_trades = len(df[df['pnl'] > 0])
            losing_trades = len(df[df['pnl'] < 0])
            breakeven_trades = len(df[df['pnl'] == 0])
            
            fig_pie = px.pie(
                values=[winning_trades, losing_trades, breakeven_trades],
                names=['Прибыльные', 'Убыточные', 'В ноль'],
                title="Распределение сделок по результату",
                color_discrete_sequence=['#00D4AA', '#FF6B6B', '#FFD93D']
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with tab3:
            # Анализ по времени
            df['hour'] = pd.to_datetime(df['exit_time']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['exit_time']).dt.day_name()
            
            # P&L по часам
            hourly_pnl = df.groupby('hour')['pnl'].sum().reset_index()
            
            fig_hourly = px.bar(
                hourly_pnl,
                x='hour',
                y='pnl',
                title="P&L по часам дня",
                color='pnl',
                color_continuous_scale='RdYlGn'
            )
            
            fig_hourly.update_layout(
                xaxis_title="Час дня",
                yaxis_title="P&L (USDT)",
                height=300
            )
            
            st.plotly_chart(fig_hourly, use_container_width=True)
            
            # P&L по дням недели
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            daily_pnl = df.groupby('day_of_week')['pnl'].sum().reindex(day_order, fill_value=0).reset_index()
            
            fig_daily = px.bar(
                daily_pnl,
                x='day_of_week',
                y='pnl',
                title="P&L по дням недели",
                color='pnl',
                color_continuous_scale='RdYlGn'
            )
            
            fig_daily.update_layout(
                xaxis_title="День недели",
                yaxis_title="P&L (USDT)",
                height=300
            )
            
            st.plotly_chart(fig_daily, use_container_width=True)
    
    except Exception as e:
        logger.error(f"Error showing performance analysis: {str(e)}")
        st.error("Ошибка анализа производительности")

def show_trade_statistics(demo_mode: bool):
    """Торговая статистика"""
    
    st.markdown("### 📊 Статистика")
    
    try:
        # Получаем данные
        if demo_mode:
            if 'demo_intelligent_trader' in st.session_state:
                stats = st.session_state.demo_intelligent_trader.get_performance_stats()
                trade_history = st.session_state.demo_intelligent_trader.trade_history
            else:
                stats = st.session_state.history_intelligent_trader.get_performance_stats()
                trade_history = st.session_state.history_intelligent_trader.trade_history
        else:
            if 'live_intelligent_trader' in st.session_state:
                stats = st.session_state.live_intelligent_trader.get_performance_stats()
                trade_history = st.session_state.live_intelligent_trader.trade_history
            else:
                stats = {}
                trade_history = []
        
        # Применяем фильтры к истории для детального анализа
        filtered_trades = apply_trade_filters(trade_history) if trade_history else []
        
        # Основные метрики
        st.metric("🎯 Всего сделок", stats.get('total_trades', 0))
        st.metric("✅ Прибыльные", stats.get('winning_trades', 0))
        st.metric("❌ Убыточные", stats.get('losing_trades', 0))
        
        win_rate = stats.get('win_rate', 0)
        st.metric("📊 Винрейт", f"{win_rate:.1f}%")
        
        total_pnl = stats.get('total_pnl', 0)
        pnl_color = "🟢" if total_pnl >= 0 else "🔴"
        st.metric(f"{pnl_color} Общий P&L", f"${total_pnl:+.2f}")
        
        avg_pnl = stats.get('average_pnl', 0)
        st.metric("📊 Средний P&L", f"${avg_pnl:+.2f}")
        
        best_trade = stats.get('best_trade', 0)
        st.metric("🏆 Лучшая сделка", f"${best_trade:+.2f}")
        
        worst_trade = stats.get('worst_trade', 0)
        st.metric("📉 Худшая сделка", f"${worst_trade:+.2f}")
        
        # Дополнительная статистика по отфильтрованным данным
        if filtered_trades:
            st.divider()
            st.markdown("**По текущим фильтрам:**")
            
            df = pd.DataFrame(filtered_trades)
            
            filtered_total = len(df)
            filtered_winning = len(df[df['pnl'] > 0])
            filtered_losing = len(df[df['pnl'] < 0])
            filtered_win_rate = (filtered_winning / filtered_total) * 100 if filtered_total > 0 else 0
            
            st.metric("🔍 Сделок в фильтре", filtered_total)
            st.metric("🎯 Винрейт (фильтр)", f"{filtered_win_rate:.1f}%")
            
            filtered_total_pnl = df['pnl'].sum()
            filtered_avg_pnl = df['pnl'].mean()
            
            st.metric("💰 P&L (фильтр)", f"${filtered_total_pnl:+.2f}")
            st.metric("📊 Средний P&L (фильтр)", f"${filtered_avg_pnl:+.2f}")
    
    except Exception as e:
        logger.error(f"Error showing trade statistics: {str(e)}")
        st.error("Ошибка отображения статистики")

def show_export_options(demo_mode: bool):
    """Опции экспорта данных"""
    
    st.markdown("### 📤 Экспорт данных")
    
    try:
        # Получаем данные для экспорта
        if demo_mode:
            if 'demo_intelligent_trader' in st.session_state:
                trade_history = st.session_state.demo_intelligent_trader.trade_history
            else:
                trade_history = st.session_state.history_intelligent_trader.trade_history
        else:
            if 'live_intelligent_trader' in st.session_state:
                trade_history = st.session_state.live_intelligent_trader.trade_history
            else:
                trade_history = []
        
        if not trade_history:
            st.info("Нет данных для экспорта")
            return
        
        # Применяем фильтры
        filtered_trades = apply_trade_filters(trade_history)
        
        if not filtered_trades:
            st.info("Нет сделок для экспорта после применения фильтров")
            return
        
        # Подготавливаем данные для экспорта
        df = pd.DataFrame(filtered_trades)
        
        # Форматируем колонки
        export_df = df.copy()
        export_df['entry_time'] = pd.to_datetime(export_df['entry_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        export_df['exit_time'] = pd.to_datetime(export_df['exit_time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Переименовываем колонки для экспорта
        export_df.columns = [
            'Символ', 'Сторона', 'Цена_входа', 'Цена_выхода', 'Количество',
            'PnL_USDT', 'PnL_процент', 'Время_входа', 'Время_выхода', 'Причина_закрытия',
            'Сила_сигнала'
        ]
        
        # Кнопки экспорта
        col1, col2 = st.columns(2)
        
        with col1:
            # Экспорт в CSV
            csv_buffer = io.StringIO()
            export_df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_data = csv_buffer.getvalue()
            
            st.download_button(
                label="📄 Скачать CSV",
                data=csv_data,
                file_name=f"trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Экспорт в Excel
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                export_df.to_excel(writer, index=False, sheet_name='Trade_History')
                
                # Добавляем статистику на отдельный лист
                stats_data = {
                    'Метрика': ['Всего сделок', 'Прибыльные сделки', 'Убыточные сделки', 
                               'Винрейт (%)', 'Общий P&L (USDT)', 'Средний P&L (USDT)',
                               'Лучшая сделка (USDT)', 'Худшая сделка (USDT)'],
                    'Значение': [
                        len(export_df),
                        len(export_df[export_df['PnL_USDT'] > 0]),
                        len(export_df[export_df['PnL_USDT'] < 0]),
                        (len(export_df[export_df['PnL_USDT'] > 0]) / len(export_df)) * 100 if len(export_df) > 0 else 0,
                        export_df['PnL_USDT'].sum(),
                        export_df['PnL_USDT'].mean(),
                        export_df['PnL_USDT'].max(),
                        export_df['PnL_USDT'].min()
                    ]
                }
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, index=False, sheet_name='Statistics')
            
            excel_data = excel_buffer.getvalue()
            
            st.download_button(
                label="📊 Скачать Excel",
                data=excel_data,
                file_name=f"trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # Информация о данных
        st.info(f"📊 Готово к экспорту: {len(filtered_trades)} сделок")
        
        # Предварительный просмотр
        with st.expander("👀 Предварительный просмотр данных для экспорта"):
            st.dataframe(export_df.head(10), use_container_width=True)
    
    except Exception as e:
        logger.error(f"Error showing export options: {str(e)}")
        st.error("Ошибка подготовки данных для экспорта")

# Автообновление каждые 60 секунд
if 'history_last_update' not in st.session_state:
    st.session_state.history_last_update = datetime.now()

if (datetime.now() - st.session_state.history_last_update).total_seconds() > 60:
    st.session_state.history_last_update = datetime.now()
    # Автоматическое обновление данных
    pass
