#Bad Code
INVALID_INPUT = "INVALID_INPUT"
FAILURE = "FAILURE"
SUCCESS = "SUCCESS"

def average_highest_player_level_by_group(GroupID, m, avgLevel):
    if GroupID < 0 or GroupID > uni.get_universe_size() or avgLevel is None or m <= 0:
        return INVALID_INPUT

    if GroupID != 0 and m > uni.find_team_leader(GroupID).box.num_of_players_with_lvl_0 + uni.find_team_leader(GroupID).box.players_in_group.get_size():
        return FAILURE

    if GroupID == 0 and m > system_box.num_of_players_with_lvl_0 + system_box.players_in_group.get_size():
        return FAILURE

    avl = None
    final = None

    if GroupID == 0:
        avl = system_box.players_in_group
        final = system_box.total_level
    else:
        avl = uni.find_team_leader(GroupID).box.players_in_group
        final = uni.find_team_leader(GroupID).box.total_level

    if avl.get_size() == 0:
        avgLevel[0] = 0
        return SUCCESS

    if avl.get_size() - m < 1:
        avgLevel[0] = avl.get_sum(avl.get_size()) / m
        return SUCCESS

    low_sum = avl.get_sum(avl.get_size() - m)
    final -= low_sum
    avgLevel[0] = final / m

    return SUCCESS
  
#Good Code
INVALID_INPUT = "INVALID_INPUT"
FAILURE = "FAILURE"
SUCCESS = "SUCCESS"

def validate_inputs(GroupID, m, avgLevel):
    if GroupID < 0 or GroupID > uni.get_universe_size() or avgLevel is None or m <= 0:
        return INVALID_INPUT
    return SUCCESS

def check_failure_condition(GroupID, m):
    team_leader = uni.find_team_leader(GroupID) if GroupID != 0 else None
    num_of_players_with_lvl_0 = team_leader.box.num_of_players_with_lvl_0 if team_leader else system_box.num_of_players_with_lvl_0
    size_of_players_in_group = team_leader.box.players_in_group.get_size() if team_leader else system_box.players_in_group.get_size()

    if m > num_of_players_with_lvl_0 + size_of_players_in_group:
        return FAILURE
    return SUCCESS

def get_avl_and_final(GroupID):
    avl = None
    final = None

    if GroupID == 0:
        avl = system_box.players_in_group
        final = system_box.total_level
    else:
        avl = uni.find_team_leader(GroupID).box.players_in_group
        final = uni.find_team_leader(GroupID).box.total_level

    return avl, final

def compute_average_level(m, avgLevel, avl, final):
    if avl.get_size() == 0:
        avgLevel[0] = 0
        return SUCCESS

    if avl.get_size() - m < 1:
        avgLevel[0] = avl.get_sum(avl.get_size()) / m
        return SUCCESS

    low_sum = avl.get_sum(avl.get_size() - m)
    final -= low_sum
    avgLevel[0] = final / m
    return SUCCESS

def average_highest_player_level_by_group(GroupID, m, avgLevel):
    status = validate_inputs(GroupID, m, avgLevel)
    if status != SUCCESS:
        return status

    status = check_failure_condition(GroupID, m)
    if status != SUCCESS:
        return status

    avl, final = get_avl_and_final(GroupID)

    return compute_average_level(m, avgLevel, avl, final)
