import os, textfsm, tabulate, pprint


template_dps='fsm_dps'
template_heal='fsm_heal'
combatlog='CombatLog-2024-09-26_2041.txt'
combatlog_local = 'combatlog_local.txt'


def parser(template,combatlog):
    with open(template) as f, open(combatlog) as output:
        re_table = textfsm.TextFSM(f)
        header = re_table.header
        result = re_table.ParseText(output.read())
    return result


def sum_damage_by_attacker_target(data):
    damage_stats = {}

    for entry in data:
        time = entry[0]
        attacker = entry[1]
        hit = entry[2]
        target = entry[3]
        combo = entry[4]
        damage = int(entry[5])
        damage_type = entry[6]
        crit = entry[7]
        #print(f"{time} {attacker} {hit} {target} {combo} {damage} {damage_type} {crit}")

        key = (attacker, target, combo, crit)

        if key in damage_stats:
            damage_stats[key] += damage
        else:
            damage_stats[key] = damage

    return damage_stats


if __name__ == '__main__':
    pprint.pprint(parser(template_dps, combatlog_local))

    #pprint.pprint(sum_damage_by_attacker_target(parser(template_dps, combatlog_local)))
    #sum_damage_by_attacker_target(parser(template_dps, combatlog))


