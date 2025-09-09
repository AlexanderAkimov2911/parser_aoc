# text_fsm.py README

This script parses a combat log file using a TextFSM template and summarizes damage statistics by attacker-target pairs.

## Installation

Ensure you have Python 3.x installed. Install required dependencies:

```bash
pip install textfsm tabulate
```

## Usage

1. Place your TextFSM template file as `fsm_dps.textfsm`
2. Place your combat log file as `logs/CombatLog-2024-09-26_2041.txt`
3. Run the script:

```bash
python text_fsm.py
```

## Configuration

- Modify `template_dps` and `combatlog` variables at the top of the script to change file paths
- Update `player_name` to your in-game name if needed

## Output

The script outputs a dictionary showing total damage per (attacker, target) pair:

```python
{
    ('PlayerA', 'EnemyX'): 1500,
    ('PlayerB', 'EnemyY'): 2300,
    ...
}
```

## Notes

- The script automatically normalizes 'Your'/'You' to the specified player name
- Requires TextFSM template to be properly configured for your log format

## Plans

- [ ] Optimize TextFSM template to handle more complex log formats
- [ ] Add error handling for malformed logs
- [ ] Implement GUI interface using Tkinter or PyQt
  - File dialogs for template/log selection
  - Real-time damage visualization
  - Export to CSV functionality
- [ ] Add configuration file support for player names and log paths
- [ ] Implement damage type categorization
- [ ] Add combat duration statistics