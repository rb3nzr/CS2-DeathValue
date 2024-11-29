This script generates statistics of a player's death events from a `demo` file.

For each of the player's death events, the distance of each teammate from that point of death is gathered, and the `softmax` of that distance is calculated. A weighted score is generated based on the shortest distance (closest teammate) and whether or not the death was traded. 
```python
for tick, (softmax_value, was_traded, round_num, teammate) in death_values.items():
    trade_bonus = beta if was_traded else 0 
    weighted_score = alpha * (1 - softmax_value) + trade_bonus 
    w_death_values.append((tick, softmax_value, was_traded, weighted_score, round_num, teammate))
```

## Usage 
The script makes heavy usage of the [awpy project](https://github.com/pnxenopoulos/awpy)

```
pip install --pre awpy
pip install numpy, pandas, matplotlib, colorama
python death_value.py -d demofile.dem -p 'player name' --map
```

## Example Output
