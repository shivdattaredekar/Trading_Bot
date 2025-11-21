src/
└── tradingsetup/
    ├── config/
    │   └── settings.py
    ├── utils/
    │   ├── __init__.py
    │   ├── logger.py
    │   ├── trade_logger.py
    │   └── trade_helpers.py         ✅ new — helper functions
    ├── trade_logic/
    │   ├── __init__.py
    │   ├── trade_executor.py        ✅ new — handles order placing logic
    │   ├── ema_strategy.py
    │   └── single_stock_strategy.py
    ├── strategies/
    │   ├── __init__.py
    │   ├── base_strategy.py         ✅ abstract base class
    │   ├── ema_strategy_impl.py     ✅ actual EMA logic
    │   └── single_stock_impl.py     ✅ Tata Motors strategy
    └── main.py                      ✅ runs everything together
