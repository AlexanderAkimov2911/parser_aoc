import os
import re


def parseline(line):
    global verbose
    if not line: return None
    if line[0:4] == "Your": line = "You'" + line[4:]
    
    for x in ("affect", "afflict"):
      if x in line:
        v = re.match(r"(.+?) %ss? (.+?) with (.+)" % x, line).groups()
        if v: return (v[0], "buff", v[2], v[1], 0, None, False)
        
    for x in ("crush", "pierc", "slash"):
      if x in line:
        m = re.match(r"([^\']+?)(?:'s? (.+?))? (critically )?%se?s? (.+?) for (\d+)" % x, line)
    m = re.match(r"You suffer (\d+) fall damage", line)
    if m: return ("You", "damage", None, "You", int(m.group(1)), "fall", False)
    
    if "heal" in line:
      m = re.match(r"([^\']+?)(?:'s? (.+?))? (critically )?heal(?:s|ed) (.+?) for (\d+)\.", line)
      if m:
        v = m.groups()
        if v:
          if v[2]: crit = True
          else:    crit = False
          return (v[0], "heal", v[1], v[3], int(v[4]), None, crit)
    
    if "casts" in line:
      m = re.match(r"(.+?) casts (.+)", line)
      if m:
        v = m.groups()
        if v: return (v[0], "cast", v[1], None, 0, None, False)
    
    m = re.match(r"(.*?) lost (\d+) (mana|stamina|sprint energy)", line)
    if m:
      v = m.groups()
      return (None, "drain", None, v[0], int(v[1]), v[2], False)
    
    m = re.match(r"(.*?) gained (\d+) (mana|stamina|sprint energy)", line)
    if m:
      v = m.groups()
      return (None, "drain", None, v[0], -int(v[1]), v[2], False)
    
    m = re.match(r"(.*?) died\.", line)
    if m: return (None, "die", None, m.group(1), 0, None, False)
    
    m = re.match(r"You successfully cast spell (.*)", line)
    if m:
      v = m.groups()
      return ("You", "cast", v[0], None, 0, None, False)
    
    m = re.match(r"You gain Bel's Mirth", line)
    if m:
      return ("You", "buff", "Bel's Mirth", "You", 0, None, False)
    
    
    # This block is extra parsing that always returns None
    # Enable to test for unknown lines, at a small cost to performance
    if verbose:
      # Buff on self disappeared; don't really care
      m = re.match(r"Effect (.+) terminated\.", line)
      if m: return None
      
      # Don't care; the real damage we take already deducts this value
      m = re.match(r"(.+) absorbed (\d+) points of damage(?: from (.*) attack)?", line)
      if m: return None
      m = re.match(r"(.+) mitigated (\d+) points of damage(?: from (.*) attack)?", line)
      if m: return None
      
      for x in ("blocked", "parried", "dodged"):
        m = re.match(r"(.+?) %s (your|[^']+'s?) (?:combat|attack)" % x, line)
        if m: return None
      m = re.match(r"(.+) resisted the effects of a spell cast by (.+)", line)
      if m: return None
      m = re.match(r"(.+) misses\.", line)
      if m: return None
      
      # Static messages we ignore
      for x in ("Interrupted!", "This spell is currently recharging.", "Logging started", "Logging finished",
          "The target resisted the effect of your spell.", "There are no valid targets in range.", "You are silenced",
          "Can not cast the spell, a better one is already running on the target.",
          "You do not have enough mana to cast this spell.", "You have no line of sight to your target!",
          "The target is out of range", "Target must be in front of you.", "You' target is evading!",
          "The target is currently immune to the effect of this spell.", "You can not cast spells while falling."):
        if line == x: return None
      
      if line[0:19] == "You are healed for ": return None
      if line[0:8] == "You gain": return None # You gain buffs or mana/stamina
      if line[0:8] == "You lose": return None # You lose mana/stamina
      if line[0:17] == "You start casting": return None
      if line[0:16] == "You have earned ": return None # AA, valor
      if line[0:11] == "You earned ": return None # AA, prowess
      if "<font color=" in line: return None # faction or renown
      
      
      #MainWindow.PrintText("[00:00:00] %s" % line)
      print(f"{line}")
    return None


def parse(x):
    (attacker, action, ability, target, amount, type, crit) = x
    print(x)
    

    #return x

players = set()
verbose = 1 
file = open("./CombatLog-2024-09-05_2331.txt", "r")
while True:
    content = file.readline()
    if not content:
        break
    #vector = self.parseline(line[11:].rstrip())
    line = parseline(content[11:].rstrip())
    if line is None:
        #print(line)
        #print(f"Line is None {line}")
        pass
    else:
        #print(line)

        parsed_line = parse(line)
        # print(parsed_line)
        pass

        
    #parse(line)
    #print(content[:11].strip('[ ]'))
    #print(parseline(content[11:]))
print(players)

file.close()