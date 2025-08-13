# Overview

This is a professional cryptocurrency trading bot called "CryptoBot AI Pro" built with Streamlit. The application provides an intelligent, autonomous trading system that analyzes cryptocurrency markets using multiple AI-powered strategies including scalping, trend following, mean reversion, breakout trading, arbitrage, and news-based trading. The system features both demo and live trading modes with comprehensive risk management, technical analysis capabilities, and real-time market sentiment monitoring.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
**Streamlit Web Application**: The main interface is built using Streamlit with a modular page-based architecture including dashboard, demo trading, live trading, balance management, and trade history pages. The UI features Russian language support and provides real-time trading dashboards with interactive charts and controls.

**Security-First Design**: Authentication is handled through a custom SecurityManager class that implements session management, password hashing with salt, rate limiting, IP-based access control, and account lockout protection. The system includes encrypted API key storage and multi-layer security measures.

**Multi-Page Navigation**: The application uses a clean page structure with separate modules for dashboard, balance, demo trading, live trading, and trade history, allowing for clear separation of concerns and intuitive user experience.

## Backend Architecture
**Intelligent Trading Engine**: The core trading logic is implemented through IntelligentTrader and AdvancedTrader classes that combine multiple analysis methods. The system uses technical indicators (40%), price action analysis (25%), volume analysis (15%), and sentiment analysis (20%) to create weighted trading signals.

**Multi-Strategy Trading System**: Built with a strategy-based architecture supporting multiple concurrent trading strategies with different timeframes, risk levels, and signal strength requirements. Includes scalping, trend following, mean reversion, breakout, arbitrage, and news-based strategies.

**Exchange Integration**: MEXCClient provides comprehensive integration with MEXC exchange supporting both spot and futures trading. The client includes rate limiting, connection pooling, WebSocket support for real-time data, and demo mode simulation for safe testing.

**Risk Management System**: Comprehensive risk management through portfolio diversification (maximum 3 positions), position sizing (2% risk per trade), leverage control (up to 5x), stop-loss/take-profit automation, and correlation analysis to avoid overexposure.

## Data Processing Pipeline
**Technical Analysis Engine**: Implements a comprehensive suite of technical indicators including SMA, EMA, RSI, MACD, Bollinger Bands, Williams %R, CCI, ATR, and Stochastic oscillators. The analysis engine processes OHLCV data to generate technical signals with proper data validation and error handling.

**News Sentiment Analysis**: Multi-source RSS feed parser that monitors 10+ cryptocurrency news sources including CoinTelegraph, CoinDesk, Decrypt, and others. Uses advanced keyword-based sentiment analysis with positive, negative, and neutral keyword dictionaries to gauge market sentiment.

**Signal Generation**: Advanced signal generator that combines technical indicators, price action analysis, volume analysis, and sentiment data to create weighted trading signals. The system includes confidence scoring, signal strength thresholds, and cache management for optimal performance.

**Data Validation and Cleaning**: Robust data preprocessing pipeline that validates OHLCV data integrity, handles missing data points, converts timestamps, and ensures proper data types. Includes error handling and logging for all data operations.

# External Dependencies

**MEXC Exchange API**: Primary integration with MEXC cryptocurrency exchange for market data retrieval, account information, order execution, and WebSocket connections for real-time updates. Includes both mainnet and demo mode support with proper authentication and rate limiting.

**Multiple News Sources**: Integration with 10+ RSS feeds from major cryptocurrency news outlets including CoinTelegraph, CoinDesk, Decrypt, CoinBase Blog, Binance Blog, Bitcoin Magazine, NewsBC, CryptoNews, CryptoSlate, and BeInCrypto for comprehensive market sentiment analysis.

**Plotly Visualization**: Advanced charting and visualization using Plotly for interactive candlestick charts, technical indicator overlays, portfolio performance charts, and real-time trading dashboards with responsive design.

**Security and Authentication**: Uses standard Python security libraries including hashlib for password hashing, secrets for secure token generation, hmac for API signature generation, and cryptography for encrypted data storage. Includes session management and IP-based access control.

**Technical Analysis Libraries**: Integration with TA-Lib (Technical Analysis Library) for advanced technical indicator calculations, pandas for data manipulation, numpy for mathematical operations, and scipy for statistical analysis. Includes custom indicator implementations for specialized crypto trading signals.