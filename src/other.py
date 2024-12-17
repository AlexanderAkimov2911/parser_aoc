

class AbilityCountdown():
  def __init__(self, name, timer, timer_start=0, timer_suspend=5, colours=(10,5),
              # These arguments match the ones in parse()
              # If all non-null arguments match, we consider ability to have been used
              # (arguments can be prepended with '!')
              attacker=None, action=None, ability=None, target=None, amount=None, type=None, crit=None):
    self.name = name
    self.timer = timer
    self.timer_suspend_match = timer_suspend
    self.last_use = timer_start and elapsed() - timer + timer_start or 0
    self.colours = colours
    
    # 
    self.keywords = {}
    vars = locals() # We'll fetch some arguments from this
    for k in 'attacker', 'action', 'ability', 'target', 'amount', 'type', 'crit':
      if vars[k] != None:
        self.keywords[k] = vars[k]

  def parse(self, xxx_todo_changeme15):
    # If all keywords in self.keywords exist and match our arguments, we've got a match
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme15
    vars = locals()
    match = True
    for k in self.keywords:
      if not vars[k] or \
          (self.keywords[k][0] == '!' and self.keywords[k][1:] == vars[k]) or \
          (self.keywords[k][0] != '!' and self.keywords[k] != vars[k]):
        match = False
    
    if match and elapsed() - self.last_use > self.timer_suspend_match:
      self.last_use = elapsed()
  
  def getCountdownValue(self):
    return max(0,(self.timer - (elapsed() - self.last_use)))
  
  def prepareWindowText(self):
    if self.last_use == 0:
      next = 0
      colour = ""
    else:
      next = self.getCountdownValue()
      if   next > self.colours[0]:  colour = ""
      elif next > self.colours[1]:  colour = "yellow"
      else:                         colour = "red"
    return "%-16s#%s#%u#" % (self.name[:16], colour, next)

# This class is an AbilityCountdown that is used when the ability isn't found in
# combatlog when it is used.
# The timer (self.last_use) is set when the first match is found, and never
# touched after that.
class CyclicAbilityCountdown(AbilityCountdown):
  def parse(self, xxx_todo_changeme16):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme16
    if self.last_use == 0:
      AbilityCountdown.parse(self, (attacker, action, ability, target, amount, type, crit))
  
  def getCountdownValue(self):
      return self.timer - ((elapsed() - self.last_use) % self.timer)


class StandardBoss(LogParser):
  def __init__(self, window):
    self.window = window
    self.finished = False
    self.abilities = self.getAbilities()
  
  def getAbilities(self):
    raise NameError('Classes inheriting StandardBoss must implement getAbilities()')
    
    # raise "Classes inheriting StandardBoss must implement getAbilities()"
    # return [
    #   AbilityCountdown("Golem", timer=65, timer_suspend=10, attacker="Bone Golem", action="cast", ability='Self Destruct', colours=(15,5)),
    #   AbilityCountdown("Affliction", 33, attacker="Yah Chieng", action="buff", ability="Mortal Affliction"),
    #   AbilityCountdown("Devouring Pact", 41, attacker="Yah Chieng", action="cast", ability="Devouring Pact", colours=(15,10)),
    # ]
  
  def parse(self, xxx_todo_changeme17):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme17
    if action == 'damage':
      self.finished = elapsed()
    
    for a in self.abilities:
      a.parse((attacker, action, ability, target, amount, type, crit))
  
  def prepareWindowText(self):
    lines = (x.prepareWindowText() for x in self.abilities)
    return "\n".join(lines)
  
  def updateWindow(self):
    text = self.prepareWindowText()
    self.window.setText(text)
  
  def poll(self):
    self.updateWindow()
    return LogParser.poll(self)



class ParserWindow(LogParser):
  colours = {
    "red"   : (255,20,20),
    "green" : (0,200,10),
    "yellow": (240,240,20),
    "blue"  : (50,50,200),
    "grey"  : (130,130,130),
    "invisible" : (200,200,200),
  }
  lines = 1
  proportion = 0 # 0 also means not resizeable
    
  def __init__(self, parent):
    LogParser.__init__(self)
    
  def updateWindow(self):
    return
  
  def setTextCorrectly(self, text, scroll=True):
    try:
      self.Clear()
      
      n = 0
      for x in text.split("#"):
        if not x: continue
        if x in self.colours:
          self.BeginTextColour(self.colours[x])
          n = 1
        else:
          self.WriteText("%s" % x,)
          if n:
            n = 0
            self.EndTextColour()
      
      if scroll:  self.ShowPosition(self.GetLastPosition())
      else:       self.ShowPosition(0)
    except:
      pass
  
  def setText(self, text, scroll=True):
    wx.CallAfter(self.setTextCorrectly, text, scroll)

# This parser attempts to group debuffs by caster, and display for further analysis
# Command line use only!
class DebuffFinder(LogParser):
  boss_names = ("Thaw", "Swelter", "Harvest", "Arctic")
  pets = ("Arcanist", "Archmagus", "Blighted One", "Blood Arcanist", "Blood Pit", "Cacodemon", "Circle of Magic", "Companion Spirit", "Demon Slave", "Demon Warlord", "Dread Shadow", "Frozen Hatred", "Heroic Banner", "Idol of Dark Rejuvenation", "Idol of Set", "Life-stealer", "Living Firestorm", "Magus", "Parasitic Soul", "Protective Spirit", "Reaper", "Spirit of Yggdrasil", "Zone of Gluttony")
  player_buffs = ("Armageddon Falls", "Claws of Corruption (Rank 1)", "Claws of Corruption (Rank 2)", "Claws of Life", "Claws of Stone (Rank 4)", "Claws of the Reaper", "Cursed by Hell (Rank 3)", "Cursed by the Heavens (Rank 3)", "Cursed", "Mark of the Devourer (1)", "Mark of the Devourer (2)", "Marked Target (1)", "Marked Target (2)", "Marked Target (3)", "Marked Target (4)", "Marked Target (5)", "Mocking Sneer", "Static Charge")
  ignore_list = ("Foul Presence", "Shock Protection")
  
  def __init__(self):
    self.first_action = 0
    self.last_action = 0
    self.debuff = {}
    self.timestamps = {}
  
  def parse(self, xxx_todo_changeme18):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme18
    if action == "damage":
      if self.last_action == 0:
        self.first_action = elapsed()
      self.last_action = elapsed()
    
    if action in ("buff", "damage", "cast"):
      if attacker in self.pets or (" " not in attacker and attacker not in self.boss_names):
        return
      if ability and ability in self.player_buffs or ability in self.ignore_list:
        return
      
      if self.last_action == 0:
        self.first_action = elapsed()
      self.last_action = elapsed()
      
      if ability:
        ability += " (%s)" % action
      
      e = int(elapsed() - self.first_action)
      if attacker not in self.debuff:
        self.debuff[attacker] = {}
        self.timestamps[attacker] = timestamp()
      if ability not in self.debuff[attacker]:
        self.debuff[attacker][ability] = {}
      if e not in self.debuff[attacker][ability]:
        self.debuff[attacker][ability][e] = []
      self.debuff[attacker][ability][e].append(target)
      
  def poll(self):
    if self.last_action and elapsed() - self.last_action > 15:
      for a in self.debuff:
        print("\n%s =================== %s (%us) ===================" % (self.timestamps[a], a, self.last_action - self.first_action))
        debuffs = [x for x in self.debuff[a]]
        debuffs.sort()
        for b in debuffs:
          print("\n[%s]" % b)
          e = [x for x in self.debuff[a][b]]
          e.sort()
          for x in range(len(e)):
            if x == 0:  prev = 0
            else:       prev = e[x] - e[x-1]
            # if prev > 100: prev = 0
            print("- %3u (%3u): %s" % (e[x], prev, self.debuff[a][b][e[x]]))
      
      if self.debuff > 1:
        print("\n")
      
      self.last_action = 0
      self.debuff = {}
      self.timestamps = {}
    return False


# This parser prints out a simplified version of the full combat log
# Command line use only!
class BossDisplay(LogParser):
  ignore_list = (("buff","Foul Presence"), ("buff","Shock Protection"), ("buff","Host"), ("damage","Nergal's Parasite (1)"))
  
  def __init__(self):
    self.first_action = 0
    self.last_action = 0
    self.action = {}
    self.timestamps = {}
  
  def parse(self, xxx_todo_changeme19):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme19
    if action == "damage":
      if self.last_action == 0:
        self.first_action = elapsed()
      self.last_action = elapsed()
    
    if action in ("buff", "damage", "cast"):
      if attacker in DebuffFinder.pets or (" " not in attacker and attacker not in DebuffFinder.boss_names):
        return
      if ability and ability in DebuffFinder.player_buffs or (action,ability) in self.ignore_list:
        return
      
      if self.last_action == 0:
        self.first_action = elapsed()
      self.last_action = elapsed()
      
      
      e = int(elapsed() - self.first_action)
      if attacker not in self.action:
        self.action[attacker] = []
        self.timestamps[attacker] = timestamp()
      
      for x in range(1,5):
        if len(self.action[attacker]) > x and self.action[attacker][-x][:3] == [e, action, ability]:
          self.action[attacker][-x][3].append(target)
          return
      self.action[attacker].append([e, action, ability, [target,]])
  
  def poll(self):
    if self.last_action and elapsed() - self.last_action > 15:
      for a in self.action:
        print("\n%s =================== %s (%us) ===================" % (self.timestamps[a], a, self.last_action - self.first_action))
        abilities = {}
        for b in self.action[a]:
          prev = b[0] - abilities.get((b[1],b[2]), b[0])
          print("%3u (%3u) %6s: %-25s %s" % (b[0], prev, b[1], b[2], b[3]))
          abilities[(b[1],b[2])] = b[0]
      
      self.last_action = 0
      self.action = {}
      self.timestamps = {}
    return False

