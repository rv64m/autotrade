# autotrade

Autonomous trading strategy research using LLM-driven backtesting.

## Setup

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your settings (exchange, symbol, dates, etc.)

# Run a backtest
uv run python -m src.train
```

## Autonomous Strategy Iteration

Use an LLM CLI to autonomously iterate on trading strategies. The LLM reads `src/program.md` and follows the experiment loop.

### Claude Code

```bash
# Autonomous mode (skip all permission prompts)
claude -p "Read src/program.md and follow the experiment loop autonomously." \
  --dangerously-skip-permissions

# Safer: only allow specific tools
claude -p "Read src/program.md and follow the experiment loop." \
  --allowedTools "Read,Write,Edit,Bash,Glob,Grep"

# Limit iterations for testing
claude -p "Read src/program.md and run 5 strategy experiments." \
  --dangerously-skip-permissions \
  --max-turns 50

# Background execution
nohup claude -p "Read src/program.md and follow the experiment loop." \
  --dangerously-skip-permissions \
  > claude_session.log 2>&1 &
```

### Codex (OpenAI)

```bash
# Autonomous mode (non-interactive)
codex exec "Read src/program.md and follow the experiment loop autonomously." \
  --full-auto

# Interactive with auto-approval
codex "Read src/program.md and follow the experiment loop." \
  --full-auto

# Fully autonomous (dangerous - no sandbox)
codex exec "Read src/program.md and follow the experiment loop." \
  --dangerously-bypass-approvals-and-sandbox

# Background execution
nohup codex exec "Read src/program.md and follow the experiment loop." \
  --full-auto \
  > codex_session.log 2>&1 &
```

### Gemini CLI

```bash
# Autonomous mode
gemini -p "Read src/program.md and follow the experiment loop autonomously." \
  --sandbox none

# With tool restrictions
gemini -p "Read src/program.md and follow the experiment loop." \
  --tools "read_file,write_file,run_command"

# Background execution
nohup gemini -p "Read src/program.md and follow the experiment loop." \
  --sandbox none \
  > gemini_session.log 2>&1 &
```

## Key Files

| File | Description |
|------|-------------|
| `src/program.md` | LLM instructions for strategy iteration |
| `src/train.py` | Backtest runner (set `STRATEGY_FILE`, `TIMEFRAME`, `MAX_LEVERAGE`) |
| `src/prepare.py` | Data loading and settings (read from `.env`) |
| `src/strategies/generated/` | Generated strategy files |
| `src/strategies/base.py` | `BaseStrategy` base class |
| `src/results.jsonl` | Experiment log (JSON Lines) |
| `.trash/strategies/` | Discarded strategies |

## Configuration

See `.env.example` for all options:

```bash
TOTAL_CASH=100000          # Initial capital
MARKET_TYPE=spot           # spot or swap
EXCHANGE_ID=binance        # Exchange for data
SYMBOL=BTC/USDT            # Trading pair
START_DATE=2023-01-01      # Backtest start
END_DATE=                  # Backtest end (blank = today)
MAX_DRAWDOWN_LIMIT=-30     # Target max drawdown
MIN_PROFIT_FACTOR=1.0      # Target profit factor
```
