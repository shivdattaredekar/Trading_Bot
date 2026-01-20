Trading_Bot/
├── artifacts/           (build outputs or archived data)
├── backtesting/         (tools to backtest strategies historically)
├── backup/              (backup files)
├── env/                 (environment definition — likely for dependencies)
├── logs/                (runtime logs)
├── src/
│   └── tradingsetup/
│       ├── config/      (settings/configuration code)
│       ├── utils/       (helpers, logging, and utility functions)
│       ├── trade_logic/ (core logic for trading rules)
│       ├── strategies/  (strategy implementations)
│       └── main.py      (entrypoint tying everything together)
├── .gitignore
├── EMA_5min_BPCL.csv    (example or output dataset)
├── historical_5min.csv  (historical data for testing/backtesting)
├── main.py              (top-level runner)
├── test.ipynb           (notebook for exploration/testing)
├── test.py              (script for testing functionality)
├── trade_log.csv        (trade record examples)
├── pnl_tracker.xlsx     (profit/loss tracking spreadsheet)
├── requirements.txt     (Python dependencies)
├── setup.py             (install script)
└── template.py          (likely a template for extension)
