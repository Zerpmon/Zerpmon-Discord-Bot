import inspect
import random
import re

import config


async def remove_effects(p, _p, eq_list, z1=None, z2=None):
    z = z1 if z1 else z2
    print(z['name'], eq_list)
    for eq1_lower in eq_list:
        if 'opponent miss chance' in eq1_lower:
            b = eq1_lower.replace('opponent', 'own').replace('increase', 'decrease')
            buffs = [[], []]
            buffs[0].append(b)
            p, _p, _, __ = await apply_status_effects(p, _p, buffs)
        # elif 'opponent blue chance' in eq1_lower:
        #     try:
        #         match = re.search(r'\b(\d+(\.\d+)?)\b', eq1_lower)
        #         percent_c = float(match.group()) if match is not None else 0
        #         z['moves'][6]['percent'] += percent_c
        #     except:
        #         print('remove_debuff failed')
    return p


def apply_reroll_to_msg(is_reroll, result, s1, s2, move1_cached, move2_cached):
    if is_reroll == 1:
        result['move2']['idx'] = move2_cached['idx']
        result['move2']['mul'] = move2_cached['mul']
        result['move2']['dmg'] = move2_cached['dmg']
        return s1
    elif is_reroll == 2:
        result['move1']['idx'] = move1_cached['idx']
        result['move1']['mul'] = move1_cached['mul']
        result['move1']['dmg'] = move1_cached['dmg']
        return s2
    else:
        return s1 + s2 + "Calculating Battle results..."


async def set_reroll(msg_hook, pre_text, result, is_reroll, move1_cached, move2_cached, is_pvp=False, hidden=True,
               pvp_fn=None):
    old_status = None
    if 'reset_roll1' in result or 'reset_roll2' in result:
        old_status = is_reroll
        if 'reset_roll1' in result:
            is_reroll = 1
            move2_cached.update(
                {'idx': result['move2']['idx'], 'mul': result['move2']['mul'], 'dmg': result['move2']['dmg']})
        else:
            is_reroll = 2
            move1_cached.update(
                {'idx': result['move1']['idx'], 'mul': result['move1']['mul'], 'dmg': result['move1']['dmg']})

        if is_reroll != old_status:
            if is_pvp:
                await pvp_fn(msg_hook, hidden, embeds=[], files=[], content=pre_text)
            else:
                await msg_hook.send(content=pre_text, ephemeral=hidden)
        return True, old_status, is_reroll
    return False, old_status, is_reroll


def get_crit_chance(eqs, extra=0):
    crit_chance = config.CRIT_CHANCES.copy()
    crit_chance[True] += extra
    for effect in eqs:
        if 'increase' in effect and 'crit' in effect:
            match = re.search(r'\b(\d+(\.\d+)?)\b', effect)
            val = int(float(match.group()))
            crit_chance[True] += val
    return random.choices(list(crit_chance.keys()),
                          list(crit_chance.values()))[0]


def update_dmg(dmg1, dmg2, status_affect_solo):
    changed_1, changed_2 = False, False
    for effect in status_affect_solo.copy():
        if 'next attack' in effect and 'damage' in effect:
            if not changed_2 and dmg2 != '' and dmg2 != 0 and (
                    'oppo' in effect or 'enemy' in effect):
                match = re.search(r'\b(\d+(\.\d+)?)\b', effect)
                val = int(float(match.group()))
                dmg2 = (1 - (val / 100)) * dmg2
                changed_2 = True
                status_affect_solo.remove(effect)
            elif not changed_1 and dmg1 != '' and dmg1 != 0 and not (
                    'oppo' in effect or 'enemy' in effect):
                match = re.search(r'\b(\d+(\.\d+)?)\b', effect)
                count = status_affect_solo.count(effect)
                val = int(float(match.group()))
                dmg1 = (1 + (val * count / 100)) * dmg1
                changed_1 = True
                status_affect_solo = [i for i in status_affect_solo if i != effect]
    return dmg1, dmg2, status_affect_solo


async def update_next_atk(p1, p2, index1, index2, status_affect_solo):
    p1 = p1[:]
    p2 = p2[:]
    for effect in status_affect_solo.copy():
        if 'damage' in effect:
            continue
        if 'next attack' in effect and index2 < 4 and ('oppo' in effect or 'enemy' in effect):
            match = re.search(r'\b(\d+(\.\d+)?)\b', effect)
            val = int(float(match.group()))
            val = val if 'increase' in effect else -val
            p2 = await update_array(p2, index2, val)
            status_affect_solo.remove(effect)

        elif 'next attack' in effect and index1 < 4 and not ('oppo' in effect or 'enemy' in effect):
            match = re.search(r'\b(\d+(\.\d+)?)\b', effect)
            val = int(float(match.group()))
            val = val if 'increase' in effect else -val
            p1 = await update_array(p1, index1, val)
            status_affect_solo.remove(effect)

    print(p1, p2, status_affect_solo)
    return p1, p2, status_affect_solo


def update_next_dmg(status_affect_solo):
    for effect in status_affect_solo.copy():
        if '0 damage' in effect:
            return 0, status_affect_solo
    return 1, status_affect_solo


def update_purple_stars(total, status_affect_solo):
    for effect in status_affect_solo.copy():
        if total == 0:
            break
        if 'reduce' in effect and 'star' in effect:
            if 'to 0' in effect:
                total = 0
            else:
                match = re.search(r'\b(\d+(\.\d+)?)\b', effect)
                val = int(float(match.group()))
                total -= val
    return total, status_affect_solo


async def update_array(arr, index, value, own=False, is_boss=False, index2=None):
    caller_name = inspect.currentframe().f_back.f_code.co_name
    print("Caller function:", caller_name)
    print('ARR RECV: ', arr, value)

    if arr[index] is None:
        return arr
    if arr[-1] >= 0:
        buffer_miss = 0
    else:
        buffer_miss = -arr[-1]
        arr[-1] = 0
    # Distribute the value change among the other elements
    remaining_value = -value

    if value < 0 and abs(value) > arr[index]:
        if own and index == 7:
            buffer_miss += remaining_value - arr[index]
        remaining_value = arr[index]
    print(f'here: {remaining_value, value, buffer_miss, arr}')
    if index == 7 and is_boss and value + arr[7] > 70:
        value = 70 - arr[-1]
        remaining_value = -value
    elif value < 0 and arr[-1] is not None and not own:
        if is_boss and remaining_value + arr[-1] > 70:
            remaining_value = 70 - arr[-1]
        arr[index] -= remaining_value
        arr[-1] += remaining_value
        if buffer_miss > 0:
            arr[-1] -= buffer_miss
        print('ARR RET: ', arr)
        return arr

    # if value > 0 and value
    _i = len([i for i in arr if i is not None]) - 1
    check_arr = [index]
    if index2:
        remaining_value *= 2
        _i -= 1
        check_arr.append(index2)
    for i in range(len(arr)):
        if arr[i] is None:
            continue
        if i not in check_arr:
            delta = remaining_value / _i
            _i -= 1
            arr[i] = round(arr[i] + delta, 2)

            if arr[i] < 0:
                remaining_value += arr[i]
                arr[i] = 0
            remaining_value -= delta

    # Set the index value to the desired value
    for i in check_arr:
        arr[i] += value
    if arr[index] >= 100:
        arr = [0 if (i != index and i is not None) else (100 if i == index else arr[i]) for i in range(len(arr))]
    else:
        # Check if any values are out of bounds (i.e. negative or greater than 100)
        for i in range(len(arr)):
            if arr[i] is None:
                continue
            if arr[i] < 0:
                arr[i] = 0
            elif arr[i] > 100:
                arr[i] = 100
    if buffer_miss > 0:
        arr[-1] -= buffer_miss
    print('ARR RET: ', arr)
    return arr


async def apply_status_effects(p1, p2, status_e, is_boss=False):
    print(f'old: {p1, p2}, {status_e}')
    old_miss1, old_miss2 = p1[-1], p2[-1]

    p1_atk = [i for i in p1[:4] if i is not None]
    low_index1 = p1.index(min(p1_atk))
    l_color1 = 'white' if low_index1 in [0, 1] else ('gold' if low_index1 in [2, 3] else 'purple')
    max_index1 = p1.index(max(p1_atk))
    m_color1 = 'white' if max_index1 in [0, 1] else ('gold' if max_index1 in [2, 3] else 'purple')
    try:
        l_val = min([i for i in p1[2:4] if i is not None])
        lg_index1 = [index for index, value in enumerate(p1) if value == l_val and index >= 2 and index < 4][0]
        g_val = max([i for i in p1[2:4] if i is not None])
        mg_index1 = [index for index, value in enumerate(p1) if value == g_val and index >= 2 and index < 4][0]
    except:
        lg_index1 = 2
        mg_index1 = 2

    p2_atk = [i for i in p2[:4] if i is not None]
    low_index2 = p2.index(min(p2_atk))
    l_color2 = 'white' if low_index2 in [0, 1] else ('gold' if low_index2 in [2, 3] else 'purple')
    temp = p2_atk.copy()
    temp.remove(p2[low_index2])
    low2_index2 = p2.index(min(temp))
    l2_color2 = 'white' if low2_index2 in [0, 1] else ('gold' if low2_index2 in [2, 3] else 'purple')
    max_index2 = p2.index(max(p2_atk))
    m_color2 = 'white' if max_index2 in [0, 1] else ('gold' if max_index2 in [2, 3] else 'purple')
    try:
        l_val = min([i for i in p2[2:4] if i is not None])
        lg_index2 = [index for index, value in enumerate(p2) if value == l_val and index >= 2 and index < 4][0]
        g_val = max([i for i in p2[2:4] if i is not None])
        mg_index2 = [index for index, value in enumerate(p2) if value == g_val and index >= 2 and index < 4][0]
    except:
        lg_index2 = 2
        mg_index2 = 2
    m1 = ""
    index = None

    for effect in status_e[0]:
        effect = str(effect).lower()
        if 'next' in effect or 'knock' in effect or 'stars' in effect or '0 damage' in effect:
            continue
        match = re.search(r'\b(\d+(\.\d+)?)\b', effect)
        val = float(match.group())

        if "increase" in effect:
            val = + val
            if "oppo" in effect:
                (index, m1) = (7, f'@op⬆️{config.COLOR_MAPPING["miss"]}') if "red" in effect or "miss" in effect else (
                    None, '0')
                if index is None:
                    continue
                p2 = await update_array(p2, index, val, is_boss=is_boss)

            else:
                (index, m1) = (7, f'@me⬆️{config.COLOR_MAPPING["miss"]}') if "red" in effect or "miss" in effect else (
                    (6, f'@me⬆️{config.COLOR_MAPPING["blue"]}') if "blue" in effect else
                    ((low_index1,
                      f'@me⬆️{config.COLOR_MAPPING[l_color1]}') if "lowest" in effect and "percentage attack" in effect else
                     ((max_index1,
                       f'@me⬆️{config.COLOR_MAPPING[m_color1]}') if "highest" in effect and "percentage attack" in effect else
                      ((mg_index1,
                        f'@me⬆️{config.COLOR_MAPPING["gold"]}') if "highest" in effect and "gold" in effect else
                       (lg_index1, f'@me⬆️{config.COLOR_MAPPING["gold"]}')))))
                # print(index, mg_index1, lg_index1)
                p1 = await update_array(p1, index, val)

        elif "decrease" in effect:
            val = -val
            if "oppo" in effect:
                (index, m1) = (7, f'@op⬇️{config.COLOR_MAPPING["miss"]}') if "red" in effect or "miss" in effect else (
                    (6, f'@op⬇️{config.COLOR_MAPPING["blue"]}') if "blue" in effect else
                    ((mg_index2,
                      f'@op⬇️{config.COLOR_MAPPING["gold"]}') if ("highest" in effect and "gold" in effect) or (
                            "second lowest" in effect and "gold" in effect) else
                     ((low2_index2,
                       f'@op⬇️{config.COLOR_MAPPING[l2_color2]}') if "second lowest" in effect and "attack" in effect else
                      ((low_index2,
                        f'@op⬇️{config.COLOR_MAPPING[l_color2]}') if "lowest" in effect and "percentage attack" in effect else
                       ((max_index2,
                         f'@op⬇️{config.COLOR_MAPPING[m_color2]}') if "highest" in effect and "percentage attack" in effect else
                        ((4 if (p2[4] is not None and p2[4] != 0) else (5 if p2[5] is not None else p2[4]),
                          f'@op⬇️{config.COLOR_MAPPING["purple"]}') if "purple" in effect else
                         (lg_index2, f'@op⬇️{config.COLOR_MAPPING["gold"]}')))))))
                p2 = await update_array(p2, index, val, is_boss=is_boss)
            else:
                (index, m1) = (7, f'@me⬇️{config.COLOR_MAPPING["miss"]}') if "red" in effect or "miss" in effect else (
                    (6, f'@me⬇️{config.COLOR_MAPPING["blue"]}') if "blue" in effect else
                    ((low_index1,
                      f'@me⬇️{config.COLOR_MAPPING[l_color1]}') if "lowest" in effect and "percentage attack" in effect else
                     ((max_index1,
                       f'@me⬇️{config.COLOR_MAPPING[m_color1]}') if "highest" in effect and "percentage attack" in effect else
                      ((mg_index1,
                        f'@me⬇️{config.COLOR_MAPPING["gold"]}') if "highest" in effect and "gold" in effect else
                       (lg_index1, f'@me⬇️{config.COLOR_MAPPING["gold"]}')))))
                p1 = await update_array(p1, index, val, own=True)
        print(m1)
        m1 += f" **{abs(val)}**%{index if index is not None else ''}"

    p1_atk = [i for i in p1[:4] if i is not None]
    low_index1 = p1.index(min(p1_atk))
    l_color1 = 'white' if low_index1 in [0, 1] else ('gold' if low_index1 in [2, 3] else 'purple')
    temp = p1_atk.copy()
    temp.remove(p1[low_index1])
    low2_index1 = p1.index(min(temp))
    l2_color1 = 'white' if low2_index1 in [0, 1] else ('gold' if low2_index1 in [2, 3] else 'purple')
    max_index1 = p1.index(max(p1_atk))
    m_color1 = 'white' if max_index1 in [0, 1] else ('gold' if max_index1 in [2, 3] else 'purple')
    try:
        l_val = min([i for i in p1[2:4] if i is not None])
        lg_index1 = [index for index, value in enumerate(p1) if value == l_val and index >= 2 and index < 4][0]
        g_val = max([i for i in p1[2:4] if i is not None])
        mg_index1 = [index for index, value in enumerate(p1) if value == g_val and index >= 2 and index < 4][0]
    except:
        lg_index1 = 2
        mg_index1 = 2

    p2_atk = [i for i in p2[:4] if i is not None]
    low_index2 = p2.index(min(p2_atk))
    l_color2 = 'white' if low_index2 in [0, 1] else ('gold' if low_index2 in [2, 3] else 'purple')
    max_index2 = p2.index(max(p2_atk))
    m_color2 = 'white' if max_index2 in [0, 1] else ('gold' if max_index2 in [2, 3] else 'purple')
    try:
        l_val = min([i for i in p2[2:4] if i is not None])
        lg_index2 = [index for index, value in enumerate(p2) if value == l_val and index >= 2 and index < 4][0]
        g_val = max([i for i in p2[2:4] if i is not None])
        mg_index2 = [index for index, value in enumerate(p2) if value == g_val and index >= 2 and index < 4][0]
    except:
        lg_index2 = 2
        mg_index2 = 2
    m2 = ""
    index = None

    for effect in status_e[1]:
        effect = str(effect).lower()
        if 'next' in effect or 'knock' in effect or 'stars' in effect or '0 damage' in effect:
            continue
        match = re.search(r'\b(\d+(\.\d+)?)\b', effect)
        val = float(match.group())

        if "increase" in effect:
            val = + val
            if "oppo" in effect:
                (index, m2) = (7, f'@op⬆️{config.COLOR_MAPPING["miss"]}') if "red" in effect or "miss" in effect else (
                    None, '0')
                if index is None:
                    continue
                p1 = await update_array(p1, index, val)
            else:
                (index, m2) = (7, f'@me⬆️{config.COLOR_MAPPING["miss"]}') if "red" in effect or "miss" in effect else (
                    (6, f'@me⬆️{config.COLOR_MAPPING["blue"]}') if "blue" in effect else
                    ((low_index2,
                      f'@me⬆️{config.COLOR_MAPPING[l_color2]}') if "lowest" in effect and "percentage attack" in effect else
                     ((max_index2,
                       f'@me⬆️{config.COLOR_MAPPING[m_color2]}') if "highest" in effect and "percentage attack" in effect else
                      ((mg_index2,
                        f'@me⬆️{config.COLOR_MAPPING["gold"]}') if "highest" in effect and "gold" in effect else
                       (lg_index2, f'@me⬆️{config.COLOR_MAPPING["gold"]}')))))
                p2 = await update_array(p2, index, val, is_boss=is_boss)

        elif "decrease" in effect:
            val = -val
            if "oppo" in effect:
                (index, m2) = (7, f'@op⬇️{config.COLOR_MAPPING["miss"]}') if "red" in effect or "miss" in effect else (
                    (6, f'@op⬇️{config.COLOR_MAPPING["blue"]}') if "blue" in effect else
                    ((mg_index1,
                      f'@op⬇️{config.COLOR_MAPPING["gold"]}') if ("highest" in effect and "gold" in effect) or (
                            "second lowest" in effect and "gold" in effect) else
                     ((low2_index1,
                       f'@op⬇️{config.COLOR_MAPPING[l2_color1]}') if "second lowest" in effect and "attack" in effect else
                      ((low_index1,
                        f'@op⬇️{config.COLOR_MAPPING[l_color1]}') if "lowest" in effect and "percentage attack" in effect else
                       ((max_index1,
                         f'@op⬇️{config.COLOR_MAPPING[m_color1]}') if "highest" in effect and "percentage attack" in effect else
                        ((4 if (p1[4] is not None and p1[4] != 0) else (5 if p1[5] is not None else p1[4]),
                          f'@op⬇️{config.COLOR_MAPPING["purple"]}') if "purple" in effect else
                         (lg_index1, f'@op⬇️{config.COLOR_MAPPING["gold"]}')))))))
                p1 = await update_array(p1, index, val)
            else:
                (index, m2) = (7, f'@me⬇️{config.COLOR_MAPPING["miss"]}') if "red" in effect or "miss" in effect else (
                    (6, f'@me⬇️{config.COLOR_MAPPING["blue"]}') if "blue" in effect else
                    ((low_index2,
                      f'@me⬇️{config.COLOR_MAPPING[l_color2]}') if "lowest" in effect and "percentage attack" in effect else
                     ((max_index2,
                       f'@me⬇️{config.COLOR_MAPPING[m_color2]}') if "highest" in effect and "percentage attack" in effect else
                      ((mg_index2,
                        f'@me⬇️{config.COLOR_MAPPING["gold"]}') if "highest" in effect and "gold" in effect else
                       (lg_index2, f'@me⬇️{config.COLOR_MAPPING["gold"]}')))))
                p2 = await update_array(p2, index, val, own=True, is_boss=is_boss)
        print(m2)
        m2 += f" **{abs(val)}**%{index if index is not None else ''}"

    print(f'new: {p1, p2} after {status_e}')
    print(m1, m2)
    # Miss chance equipment buffer miss addition
    # if p1[-1] > old_miss1 and buffer_miss[0] > 0:
    #     if p1[-1] > buffer_miss[0]:
    #         p1[-1] -= buffer_miss[0]
    #     else:
    #         p1[-1] = 0
    #         buffer_miss[0] -= p1[-1]
    # if p2[-1] > old_miss2 and buffer_miss[1] > 0:
    #     if p2[-1] > buffer_miss[1]:
    #         p2[-1] -= buffer_miss[1]
    #     else:
    #         p2[-1] = 0
    #         buffer_miss[1] -= p2[-1]
    return p1, p2, m1, m2

# print(apply_status_effects([21.0, 18.0, 21.0, 19.0, 11.0, None, None, 10.0], [10.0, None, 24.0, 15.0, 16.0, 16.0, 9.0, 10.0], [['Increases own highest percentage Gold by 10%'], []]))
