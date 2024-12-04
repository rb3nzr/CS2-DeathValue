This script generates statistics of a player's death events from a `demo` file.

For each of the player's death events, the distance of each teammate from that point of death is gathered, and the `softmax` of that distance is calculated. A weighted score is generated based on the shortest distance (closest teammate) and whether or not the death was traded.
```python
for tick, (softmax_value, was_traded, round_num, teammate) in death_values.items():
    trade_bonus = beta if was_traded else 0 
    weighted_score = alpha * (1 - softmax_value) + trade_bonus 
```
**The output:** tick number of the event, proximity to the closest teammate, was traded, score, round, and the closest teammate's name.

## Usage 
The script makes heavy usage of the [awpy project](https://github.com/pnxenopoulos/awpy)

```
pip install --pre awpy
pip install numpy pandas matplotlib colorama
python death_value.py -d demofile.dem -p 'player name' --map
```

## Example Output
**================= Deaths Data for XeNo_ftw =================**
|  Tick | Proximity | Was Traded | Weighted Score | Round | Closest Teammate |
|-------|-----------|------------|----------------|-------|------------------|
|  5698 |  0.333435 |     True   |    0.766596    |   1   |        T0rby     |
|  9342 |  0.421107 |    False   |    0.405225    |   2   |        53-68     |
| 13620 |  0.318313 |     True   |    0.777181    |   3   |        53-68     |
| 20246 |  0.288596 |    False   |    0.497983    |   4   |        53-68     |
| 32026 |  0.395551 |    False   |    0.423114    |   6   |        53-68     |
| 40054 |  0.464678 |    False   |    0.374726    |   7   |        53-68     |
| 46975 |  0.384300 |    False   |    0.430990    |   8   |     KingKaih     |
| 51675 |  0.542457 |    False   |    0.320280    |   9   |        53-68     |

