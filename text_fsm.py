import os, textfsm, tabulate, pprint


template_dps='fsm_dps.textfsm'
file='CombatLog-2025-08-11_1950.txt'
aoc_dir = '/home/alex/Games/Ageofconan/drive_c/Games/AgeofConan/'

combatlog= aoc_dir + '/' + file

def parser(template,combatlog):
    with open(template) as f, open(combatlog) as output:
        re_table = textfsm.TextFSM(f)
        header = re_table.header
        result = re_table.ParseText(output.read())
    return result


def sum_damage_by_attacker_target(data):
    damage_stats = {}
    player_name = 'Pvenab'

    for entry in data:
        if entry[1] == 'Your' or entry[1] == 'You':
            entry[1] = player_name
        if entry[3] == 'you':
            entry[3] = player_name
        # if entry[2] == 'slash' and entry[4] == '':
        #     entry[4] = 'White damage'


        time = entry[0]
        attacker = entry[1]
        hit = entry[2]
        target = entry[3]
        combo = entry[4]
        damage = int(entry[5])
        damage_type = entry[6]
        crit = entry[7]
        # print(f"{time} | {attacker} | {hit} | {target} | {combo} | {damage} | {damage_type} | {crit}")


        # key = (attacker, target, combo, crit)
        key = (attacker, target, combo)

        if key in damage_stats:
            damage_stats[key] += damage
        else:
            damage_stats[key] = damage

    return damage_stats


if __name__ == '__main__':
    pprint.pprint(sum_damage_by_attacker_target(parser(template_dps, combatlog)))
    # print(os.listdir(aoc_dir))

