import curses
import json
import os.path
import sys
from os.path import exists

from adb import detect_adb, get_devices, push_file
import config


def end_curses(stdscr):
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()


def center_rect_begin_yx(stdscr, height, width):
    max_y, max_x = stdscr.getmaxyx()
    return (max_y - height) // 2, (max_x - width) // 2


def multiple_choice(stdscr, choices, prompt, choices_flags=None):
    win_height = len(choices) + 3
    win_width = max(len(choice) for choice in choices) + 3
    win_width = max(win_width, len(prompt) + 3)
    tl_y, tl_x = center_rect_begin_yx(stdscr, win_height, win_width)
    win = curses.newwin(win_height, win_width, tl_y, tl_x)
    if choices_flags is None:
        choices_flags = [0] * len(choices)
    if len(choices_flags) != len(choices):
        raise ValueError("choices_flags must be the same length as choices or None.")
    selected = 0
    while True:
        win.addstr("\n " + prompt + "\n", curses.A_BOLD)
        for i, choice in enumerate(choices):
            if i == selected:
                win.addstr(f" {choice}\n", curses.A_REVERSE + choices_flags[i])
            else:
                win.addstr(f" {choice}\n", choices_flags[i])
        win.box()
        win.refresh()
        key = stdscr.getch()
        win.clear()
        if key == curses.KEY_UP:
            selected = (selected - 1) % len(choices)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(choices)
        elif key == ord("\n"):
            win.clear()
            win.refresh()
            return choices[selected]


def display(stdscr, msg, first_line_title=False):
    conf_str = " Press any key to continue..."
    win_height = msg.count("\n") + 4
    win_width = max(len(line) for line in msg.split("\n")) + 3
    win_width = max(win_width, len(conf_str) + 3)
    tl_y, tl_x = center_rect_begin_yx(stdscr, win_height, win_width)
    win = curses.newwin(win_height, win_width, tl_y, tl_x)
    win.addstr("\n")
    for (i, line) in enumerate(msg.split("\n")):
        flag = curses.A_NORMAL
        if i == 0 and first_line_title:
            flag = curses.A_BOLD
        win.addstr(f" {line}\n", flag)
    win.addstr(conf_str, curses.A_BLINK)
    win.box()
    win.refresh()
    stdscr.getch()
    win.clear()
    win.refresh()


def make_config(stdscr):
    team_color = multiple_choice(stdscr, config.TEAM_COLORS, "Select team color: ",
                                 [curses.color_pair(2), curses.color_pair(3)])
    starting_position = multiple_choice(stdscr, config.STARTING_POSITIONS, "Select starting position: ",
                                        [curses.color_pair(1), curses.color_pair(4)])
    actions = []
    while True:
        action_list = config.AVAILABLE_ACTIONS.copy()
        action_list.append("DONE")
        action_list_flags = [0] * len(config.AVAILABLE_ACTIONS)
        action_list_flags.append(curses.color_pair(1) + curses.A_BOLD)
        warnings = []
        try:
            if actions[-1] == "BACKDROP_SCORE":
                warnings.append(action_list.index("PARK_CENTER"))
            if "SPIKE_MARK_SCORE" in actions:
                warnings.append(action_list.index("SPIKE_MARK_SCORE"))
            if len(actions) > 0 and not ("DELAY" in actions[-1]):
                warnings.append(action_list.index("DELAY_1S"))
                warnings.append(action_list.index("DELAY_5S"))
                warnings.append(action_list.index("SPIKE_MARK_SCORE"))
            for action in actions:
                if "PARK" in action:
                    warnings = range(len(action_list) - 1)
        except Exception as e:
            pass
        warning_symbol = "⚠️"
        warnings = list(set(warnings))
        for warning in warnings:
            action_list[warning] = f"{warning_symbol} {action_list[warning]}"
            action_list_flags[warning] = curses.color_pair(2) + curses.A_BOLD
        action = multiple_choice(stdscr, action_list, "Select action to add: ", action_list_flags)
        if action == "DONE":
            break
        actions.append(action)
        add_more = multiple_choice(stdscr, ["Yes", "No"], "Add more actions? ")
        if add_more == "No":
            break
    return actions, team_color, starting_position


def main():
    cached_config = None
    stdscr = curses.initscr()
    try:
        curses.curs_set(0)
        stdscr.keypad(True)
        curses.noecho()
        curses.cbreak()
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        # Check adb status
        stdscr.addstr("ADB Status: ", curses.color_pair(1))
        stdscr.refresh()
        if detect_adb():
            stdscr.addstr("Installed\n", curses.color_pair(1))
        else:
            stdscr.addstr("Not Installed\n", curses.color_pair(2))

        while True:
            stdscr.move(1, 0)
            stdscr.clrtobot()
            stdscr.move(1, 0)
            stdscr.refresh()
            if cached_config is not None:
                stdscr.addstr("Cached Configuration: ", curses.color_pair(1))
                stdscr.addstr(cached_config[1], curses.color_pair(4))
                stdscr.addstr(" | ", curses.color_pair(1))
                stdscr.addstr(cached_config[2], curses.color_pair(4))
            else:
                stdscr.addstr("Cached Configuration: ", curses.color_pair(1))
                stdscr.addstr("None", curses.color_pair(4))
            NEW_CONFIG_CHOICE = "Create New Configuration"
            SAVE_CONFIG_CHOICE = "Save Configuration"
            PUSH_CONFIG_CHOICE = "Push Configuration"
            VIEW_SAVE_CONFIG_CHOICE = "View Saved Configurations"
            QUIT_CHOICE = "Quit"
            choices_list = [NEW_CONFIG_CHOICE, VIEW_SAVE_CONFIG_CHOICE]
            if cached_config is not None:
                choices_list.append(SAVE_CONFIG_CHOICE)
                if detect_adb():
                    choices_list.append(PUSH_CONFIG_CHOICE)
            choices_list.append(QUIT_CHOICE)
            choice = multiple_choice(stdscr, choices_list,
                                     "Autonomous Creation Engine Config:")
            if choice == NEW_CONFIG_CHOICE:
                cached_config = make_config(stdscr)
            elif choice == SAVE_CONFIG_CHOICE:
                save_slots = [f"{i}" for i in range(10)]
                save_slots_flags = [0] * 10
                for slot in save_slots:
                    if exists(f"ace-c-config-{slot}.json"):
                        save_slots[int(slot)] = f"{slot} (Occupied)"
                        save_slots_flags[int(slot)] = curses.color_pair(2)
                    else:
                        save_slots[int(slot)] = f"{slot} (Empty)"
                        save_slots_flags[int(slot)] = curses.color_pair(1)
                save_slot = multiple_choice(stdscr, save_slots, "Select save slot: ")
                config.save_config(cached_config[0], cached_config[1], cached_config[2],
                                   f"ace-c-config-{save_slot.split(' ')[0]}.json")
            elif choice == VIEW_SAVE_CONFIG_CHOICE:
                save_slots = [f"{i}" for i in range(10)]
                save_slots_flags = [0] * 10
                for slot in save_slots:
                    if exists(f"ace-c-config-{slot}.json"):
                        save_slots[int(slot)] = f"{slot} (Occupied)"
                        save_slots_flags[int(slot)] = curses.color_pair(1)
                    else:
                        save_slots[int(slot)] = f"{slot} (Empty)"
                        save_slots_flags[int(slot)] = curses.color_pair(2)
                save_slots += ["Back"]
                save_slots_flags.append(curses.color_pair(1) + curses.A_BOLD)
                save_slot = multiple_choice(stdscr, save_slots, "Select save slot: ", save_slots_flags)
                if save_slot == "Back":
                    continue
                elif "Empty" not in save_slot:
                    slot_id = save_slot.split(" ")[0]
                    slot_action = multiple_choice(stdscr, ["Load", "Inspect", "Delete", "Back"], f"Selected slot {slot_id}: ")
                    if slot_action == "Delete":
                        os.remove(f"ace-c-config-{slot_id}.json")
                    elif slot_action == "Back":
                        continue
                    else:
                        with open(f"ace-c-config-{slot_id}.json", "r") as f:
                            pre_processed = json.loads(f.read())
                        pre_processed = (pre_processed["autoActions"], pre_processed["teamColor"],
                                         pre_processed["startPosition"])
                        if slot_action == "Load":
                            cached_config = pre_processed
                        elif slot_action == "Inspect":
                            display_msg = f"Slot {slot_id} Configuration:\n"
                            display_msg += f"Team Color: {pre_processed[1]}\n"
                            display_msg += f"Starting Position: {pre_processed[2]}\n"
                            display_msg += "Actions:\n"
                            for action in pre_processed[0]:
                                display_msg += f"  - {action}\n"
                            display(stdscr, display_msg, True)
            elif choice == PUSH_CONFIG_CHOICE:
                devices = get_devices() + ["Back"]
                device = multiple_choice(stdscr, devices, "Select device to push to: ")
                if device == "Back":
                    continue
                config.save_config(cached_config[0], cached_config[1], cached_config[2], "ace-c-config.json")
                push_status = push_file(f"ace-c-config.json", "/storage/emulated/0/FIRST/ace-c-config.json")
                if push_status:
                    display(stdscr, "Push successful.", True)
                else:
                    display(stdscr, "Push failed.", True)
                os.remove("ace-c-config.json")
            elif choice == QUIT_CHOICE:
                break
    except Exception as e:
        end_curses(stdscr)
        print(e)
        sys.exit(1)
    end_curses(stdscr)


if __name__ == "__main__":
    main()
