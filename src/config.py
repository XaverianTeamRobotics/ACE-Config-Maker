import json

AVAILABLE_ACTIONS = ["PARK_LEFT", "PARK_CENTER", "PARK_RIGHT", "BACKDROP_SCORE", "SPIKE_MARK_SCORE", "DELAY_1S", "DELAY_5S"]
TEAM_COLORS = ["RED", "BLUE"]
STARTING_POSITIONS = ["LEFT", "RIGHT"]


def validate_action(action):
    if action not in AVAILABLE_ACTIONS:
        return False
    return True


def validate_team_color(color):
    if color not in TEAM_COLORS:
        return False
    return True


def validate_starting_position(position):
    if position not in STARTING_POSITIONS:
        return False
    return True


def validate_all(actions, team_color, starting_position):
    if not validate_team_color(team_color):
        return False
    if not validate_starting_position(starting_position):
        return False
    for action in actions:
        if not validate_action(action):
            return False
    return True


def save_config(actions, team_color, starting_position, file_path="ace-c-config.json"):
    if not validate_all(actions, team_color, starting_position):
        return False
    with open(file_path, "w") as f:
        as_dict = {
            "autoActions": actions,
            "teamColor": team_color,
            "startPosition": starting_position
        }
        f.write(json.dumps(as_dict))
    return True
