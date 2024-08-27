import os 
import sys 
import argparse
import numpy as np 
import pandas as pd 
import matplotlib.pyplot as plt

from colorama import Fore 
from typing import Union, Dict, List, Tuple

from awpy import Demo 
from awpy.stats import calculate_trades
from awpy.parsers.events import parse_kills 
from awpy.plot import plot, PLOT_SETTINGS

def calc_distance(x1, y1, x2, y2) -> float:
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

def softmax(distances: Union[List[float], np.ndarray]) -> np.ndarray:
    distances = np.array(distances)
    scaled_distances = distances / 1000
    exp_distances = np.exp(-scaled_distances)
    return exp_distances / np.sum(exp_distances)

def get_teammates_on_death(
        demo_data, player_name, player_deaths, kills
) -> List[Tuple[int, int, str, float]]:
    """
    Gets the softmax value for each teammate of the given player at the
    time of the player's death. The softmax is calculated from the euclidean
    distance of the teammate from the player. 

    Returns:
        - The tick number.
        - The round number.
        - Name of the teammate.
        - The softmax value of teammate at the player's death.
    """
    locations = list(
        demo_data.ticks[["tick", "X", "Y", "team_name", "name"]]
        .itertuples(index=False, name=None)
    )

    teammates_data = []
    for _, death in player_deaths.iterrows():
        for _, kill in kills.iterrows():
            if kill["tick"] == death["tick"]:
                death_tick   = death["tick"]
                round_num    = kill["round"]
                player_x     = death["victim_X"]
                player_y     = death["victim_Y"]
                player_team  = death["victim_team_name"]

                teammates = []
                for tick, x, y, team_name, name in locations:
                    if tick == death_tick and team_name == player_team:
                        if name == player_name:
                            continue 
                        teammates.append((name, x, y))
                
                distances = []
                for name, x, y in teammates:
                    distance = calc_distance(player_x, player_y, x, y)
                    distances.append(distance)
                
                softmax_values = softmax(distances)

                for i, (name, distance) in enumerate(zip([tm[0] for tm in teammates], distances)):
                    teammates_data.append((death_tick, round_num, name, softmax_values[i]))

    return teammates_data

def get_death_values(
        teammates_data, player_name, kills
) -> Dict[int, Tuple[float, bool, int, str]]:
    """
    Calculates the maximum softmax value for each tick and determines if the death was traded.
    
    Returns:
        A dictionary where the keys are tick numbers and the values are tuples containing:
            - The highest softmax value for that tick.
            - A boolean indicating if the death was traded.
            - The round number.
            - The teammate associated with the softmax (closest teammate).
    """
    death_values = {}
    trades = calculate_trades(kills)

    for death in teammates_data:
        tick          = death[0]
        round_num     = death[1]
        teammate      = death[2]
        softmax_value = death[3]

        if tick in death_values:
            if softmax_value > death_values[tick][0]:
                death_values[tick] = (softmax_value, False, round_num, teammate)
        else:
            death_values[tick] = (softmax_value, False, round_num, teammate)
        
    for _, trade in trades.iterrows():
        trade_tick  = trade["tick"]
        victim_name = trade["victim_name"]
        was_traded  = trade["was_traded"]

        if victim_name == player_name and was_traded:
            if trade_tick in death_values:
                current_softmax_value, _, existing_round, existing_teammate = death_values[trade_tick]
                death_values[trade_tick] = (current_softmax_value, True, existing_round, existing_teammate)

    return death_values 

def calc_weight(death_values, alpha=0.7, beta=0.3) -> pd.DataFrame:
    """
    Experimientation with getting a weight value based of the softmax
    (proximity of closest teammate teammate) and whether or not the death was traded.

    Alpha: A coefficient to represent the importance of proximity.
    Beta: A coefficient to represent the importance of a trade occuring.

    Bonus if the death was traded. 
    """
    w_death_values = []
    for tick, (softmax_value, was_traded, round_num, teammate) in death_values.items():
        trade_bonus = beta if was_traded else 0 
        weighted_score = alpha * (1 - softmax_value) + trade_bonus 
        w_death_values.append((tick, softmax_value, was_traded, weighted_score, round_num, teammate))
    
    w_death_values = pd.DataFrame(w_death_values, columns=[
        "Tick",
        "Proximity",
        "Was Traded",
        "Weighted Score",
        "Round",
        "Closest Teammate"
    ])

    return w_death_values

def export_dv_xlsx(w_death_values, player_name) -> None:
    with pd.ExcelWriter(f"{player_name}_deaths.xlsx", engine="xlsxwriter") as writer:
        w_death_values.to_excel(writer, index=False, sheet_name="Death Analysis")
        workbook = writer.book 
        worksheet = writer.sheets["Death Analysis"]

        weighted_score_col = w_death_values.columns.get_loc("Weighted Score") + 1
        weighted_score_range = f"{chr(64 + weighted_score_col)}2:{chr(64 + weighted_score_col)}{len(w_death_values) + 1}"

        worksheet.conditional_format(
            weighted_score_range,
            {
                'type': '3_color_scale',
                'min_value': w_death_values['Weighted Score'].min(), 
                'mid_value': w_death_values['Weighted Score'].mean(),
                'max_value': w_death_values['Weighted Score'].max(),
                'min_type': 'min',
                'mid_type': 'percentile',
                'max_type': 'max',
                'min_color': "#FF0000",
                'mid_color': "#FFFF00",
                'max_color': "#008000"
            }
        )

        softmax_col = w_death_values.columns.get_loc("Proximity") + 1
        softmax_range = f'{chr(64 + softmax_col)}2:{chr(64 + softmax_col)}{len(w_death_values) + 1}'

        worksheet.conditional_format(
            softmax_range,
            {
                'type': '2_color_scale',
                'min_value': w_death_values['Proximity'].min(),
                'max_value': w_death_values['Proximity'].max(),
                'min_type': 'min',
                'max_type': 'max',
                'min_color': "#FFEB84",
                'max_color': "#F8696B"
            }
        )

def gen_death_map(player_deaths, w_death_values, map_name) -> None:
    """
    Generates a map with positions of player death, labeled with the tick number.
    TODO: Issue with large labels overlapping. Hard to see some tick numbers.
    TODO: Probably add teammates and seperate these out by round.
    """
    points = []
    point_settings = []
    for _, death in player_deaths.iterrows():
        row = w_death_values[w_death_values["Tick"] == death["tick"]]
        points.append((death["victim_X"], death["victim_Y"], death["victim_Z"]))

        score = row["Weighted Score"].values[0]
        if score >= 0.6:
            color = "green"
        elif score >= 0.38:
            color = "yellow"
        else:
            color = "red"

        settings = PLOT_SETTINGS.copy()
        settings.update(
            {
                "color": color,
                "size": 3, 
                "label": death["tick"],
            }
        )

        point_settings.append(settings)
    
    plot(map_name, points, point_settings)
    plt.savefig("deathmap.png", format='png')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="python death_analysis.py", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-d", "--demo-file", required=True, help="Path to demo file.")
    parser.add_argument("-p", "--player-name", required=True, help="Name of the player to analyze.")
    parser.add_argument("--map", required=False, action="store_true", help="Creates a map of the death events.")
    args = parser.parse_args()

    if not os.path.exists(args.demo_file):
        print(Fore.RED + f"[X] {args.demo_file} not found. Exiting..")
        sys.exit()

    demo_data = Demo(args.demo_file, verbose=True, ticks=True)

    if demo_data.kills is None:
        print(Fore.RED + "[X] Kills not found in demo. Exiting..")
        sys.exit()
        
    if demo_data.ticks is None:
        print(Fore.RED + "[X] Ticks not found in the demo file. Exiting..")
        sys.exit()
    
    parsed_kills = parse_kills(demo_data.events)
    player_deaths = parsed_kills[parsed_kills["victim_name"] == args.player_name]

    kills = demo_data.kills

    print(Fore.GREEN + "\n[>] Getting all teammates distances for each death event..\n")
    print(Fore.MAGENTA + f"[>] Found {len(player_deaths)} death events for: " + Fore.CYAN + f"{args.player_name}\n")
    teammates_data = get_teammates_on_death(demo_data, args.player_name, player_deaths, kills)

    print(Fore.GREEN + "[>] Getting the closest teammates & checking if the death was traded..\n")
    death_values = get_death_values(teammates_data, args.player_name, kills)

    print(Fore.GREEN + "[>] Weighing death values..\n")
    w_death_values = calc_weight(death_values)
    print(Fore.CYAN + f"================= Deaths Data for {args.player_name} =================")
    print(Fore.WHITE + f"{w_death_values}\n")

    print(Fore.GREEN + "[>] Exporting xlsx sheet..\n")
    export_dv_xlsx(w_death_values, args.player_name)
    
    if args.map == True:
        print(Fore.GREEN + "[>] Generating deaths map..\n")
        map_name = demo_data.header["map_name"]
        gen_death_map(player_deaths, w_death_values, map_name)
