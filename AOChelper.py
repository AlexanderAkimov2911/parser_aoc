import wx, wx.richtext
import sys, os, threading, getopt, re, pickle
import time as real_time

speedup = 1
elapsed_rewind = 0

class enum:
  RAID    = 1
  TOE     = 2
  JC      = 3
  DPS     = 4
  DS      = 5
  DEBUFF  = 6
  DOTS    = 7
  AOT  = 99
  MIN  = 98
  SS   = 97
  FINC = 96
  FDEC = 95
  EXIT = 100

def sleep(delay):
  global speedup
  real_time.sleep(1.0*delay/speedup)

def time():
  global start_time, speedup
  return start_time + (real_time.time() - start_time)*speedup

def timestamp():
  global current_timestamp
  return current_timestamp

def elapsed():
  global start_time, speedup, elapsed_rewind
  return (real_time.time() - start_time)*speedup - elapsed_rewind

def average(values):
  try:
    return 1.0 * sum(values) / len(values)
  except:
    # Not really true, but in our use-case this is all right
    return 0.0

class ParserThread(threading.Thread):
  def __init__(self, log, name="parser"):
    self.log = log
    self.window = None
    self.parsers = []
    self.logdir = "."
    threading.Thread.__init__(self, name=name)
    
    if log:
      self.playback = True
    else:
      global speedup
      self.playback = False
      speedup = 1
      for x in [
            os.getcwd(),
            os.path.join(os.getcwd(), ".."),
            os.path.join(os.getcwd(), "..", "Age of Conan"),
            os.path.join(os.getcwd(), "..", "..", "Age of Conan"),
            os.path.join(os.getcwd(), "..", "Funcom", "Age of Conan"),
            os.path.join(os.getcwd(), "..", "..", "Funcom", "Age of Conan"),
            os.path.join(os.getenv("ProgramFiles(x86)","."),"Funcom","Age of Conan"),
            os.path.join(os.getenv("ProgramFiles","."),"Funcom","Age of Conan"),
            os.path.join(os.getenv("ProgramFiles(x86)","."),"Age of Conan"),
            os.path.join(os.getenv("ProgramFiles","."),"Age of Conan"),
            ]:
        try:
          os.stat(os.path.join(x,"AgeOfConan.exe"))
          self.logdir = x
          break
        except:
          continue
  
  def getNewestLog(self):
    # Get all logfiles ordered by modified time
    logs = [(os.path.getmtime(x), x) for x in ["%s/%s" % (self.logdir, y) for y in os.listdir(self.logdir) if y[0:10] == "CombatLog-"]]
    logs.sort()
    
    if not logs:
      if self.logdir == ".":  return False
      else:                   return None
    
    # Check if most recent logfile is active (written to in last five minutes)
    now = real_time.time()
    if now - logs[-1][0] > 5*60:
      return None
    
    # We're already parsing this file...
    if self.log and logs[-1][1] == self.log.name:
      return None
    
    log = open(logs[-1][1], "r")
    log.seek(0,2) # Seek to end
    
    return log
    
  
  def run(self):
    global current_timestamp
    current_timestamp = "[00:00:00]"
    # Loop over all logfiles
    while True:
      
      # Get logfile if we are not reading an existing one
      if not self.playback:
        try:
          self.log = self.getNewestLog()
          if self.log == False:
            print("No combatlogs found!\nPlease run this program either from your AOC-folder or a folder parallell to that")
            self.window.Close(True)
            exit()
          elif self.log == None:
            if self.window.settings["minimal_ui"]:
              self.window.setText("Start logging:\n  /logcombat on\n#grey#_________________")
            else:
              self.window.setText("Start logging:\n  /logcombat on\n#grey#Rclick = Settings")
            sleep(5)
            continue
          else:
            self.window.setText("Logfile found:\n%s" % self.log.name.split("/")[-1])
        except:
          if verbose:
            raise
          try:
            self.window.Close(True)
          except:
            pass
          exit()

      
      last_poll = 0
      idle = 0.0
    
      # Loop over all lines in log
      while True:
        # self.log is set to None when gui exits... ugly way of terminating this thread
        if not self.log:
          exit()
        line = self.log.readline()

        # Poll the parsers, and remove parsers that are done
        if last_poll != int(elapsed()):
          last_poll = int(elapsed())
          for p in self.parsers:
            try:
              ret = p.poll()
              if ret: self.parsers.remove(p)
            except:
              if verbose: raise
              else:       pass
        # End of file
        if not line:
          if self.playback:
            print("Done!")
            sleep(60)
            for p in self.parsers:
              try:
                ret = p.poll()
                if ret: self.parsers.remove(p)
              except:
                if verbose: raise
                else:       pass
            sleep(60)
            for p in self.parsers:
              try:
                ret = p.poll()
                if ret: self.parsers.remove(p)
              except:
                if verbose: raise
                else:       pass
            self.window.Close(True)
            exit()
          else:
            # Check for new logfile after 30 seconds, and every five seconds after that
            if idle > 30 and int(idle*10 % 50) == 0:
              new_log = self.getNewestLog()
              if new_log:
                self.log.close()
                self.log = new_log
                idle = 0
                self.window.setText("New log:\n%s" % self.log.name.split("/")[-1])
            
            idle += 0.1
            sleep(0.1)
            continue
        else:
          idle = 0
        
        # We are reading an old log, and should play it back at correct speed
        # If we can't process lines quick enough, we cheat by rewinding the clock slightly
        # Some parsers might assume that elapsed() always increases,
        # but hopefully the consequences won't be too bad.
        if self.playback:
          global elapsed_rewind
          log_time = 3600*int(line[1:3]) + 60*int(line[4:6]) + int(line[7:9])
          try:
            sleep_time = (log_time - first_log_timestamp) - elapsed()
            if sleep_time > 0:
              sleep(min(sleep_time, 20))
            elif sleep_time < -1:
              elapsed_rewind -= sleep_time/2
              
          except:
            first_log_timestamp = log_time
        
        
        try:
          current_timestamp = line[:10]
          vector = self.parseline(line[11:].rstrip()) # Strip timestamp and linebreak
        except:
          vector = None
        
        if vector:
          for parser in self.parsers:
            try:
              parser.parse(vector)
            except:
              if verbose: raise
              else:       pass
  
  
  def parseline(self, line):
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
        if m:
          v = m.groups()
          if v:
            if v[2]: crit = True
            else:    crit = False
            return (v[0], "damage", v[1], v[3], int(v[4]), x + "ing", crit)
    
    for x in ("hit", "crit"):
      if x in line:
        m = re.match(r"([^\']+?)(?:'s? (.+?))? (critically )?%ss? (.+?) for (\d+)(?: (\w+) damage\.)?" % x, line)
        if m:
          v = m.groups()
          if v:
            if v[2] or x == "crit": crit = True
            else:                   crit = False
            return (v[0], "damage", v[1], v[3], int(v[4]), v[5], crit)
    
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
          "The target is currently immune to the effect of this spell."):
        if line == x: return None
      
      if line[0:19] == "You are healed for ": return None
      if line[0:8] == "You gain": return None # You gain buffs or mana/stamina
      if line[0:8] == "You lose": return None # You lose mana/stamina
      if line[0:17] == "You start casting": return None
      if line[0:16] == "You have earned ": return None # AA, valor
      if line[0:11] == "You earned ": return None # AA, prowess
      if "<font color=" in line: return None # faction or renown
      
      
      print("[00:00:00] %s" % line)
    return None
  
  
  # This doesn't really exit the thread, but it will exit on next attempt to read the logfile
  def exit(self):
    if self.log:
      self.log.close()
      self.log = None
  
  
class LogParser():
  def __init__(self):
    self.finished = 0 # set to elapsed() when done; poll() will return True a few seconds later
  def parse(self, xxx_todo_changeme14):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme14
    raise
  def poll(self):
    # True means that parser is done, and can be removed
    return (self.finished and elapsed() - self.finished > 10)

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


class ParserWindow(LogParser, wx.richtext.RichTextCtrl):
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
    size = (0,self.lines*parent.GetFont().GetPixelSize()[1]+wx.SYS_FRAMESIZE_Y)
    wx.richtext.RichTextCtrl.__init__(self,parent,style=wx.TE_MULTILINE | wx.TE_READONLY | wx.SIMPLE_BORDER, size=size)
    self.SetBackgroundColour((200,200,200))
    #self.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
    
    # Set events
    # - Right-click for settings
    self.Bind(wx.EVT_RIGHT_DOWN, parent.ShowMenu)
    # - Move when click+drag
    self.Bind(wx.EVT_MOTION, parent.OnMotion)
    self.Bind(wx.EVT_LEFT_DOWN, parent.OnLeftDown)        
    self.Bind(wx.EVT_ENTER_WINDOW, parent.OnLeftDown)        
    
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

# Log all own sources of damage with crit chance
# Command line use only!
class CritDetector(LogParser):
  def __init__(self):
    self.abilities = {} # "Ability Name" : [ [100,100,...] (non-crit), [200,200,...] (crit)]
  
  def __del__(self):
    for x,v in self.abilities.items():
      s = average(v[0])
      c = average(v[1])
      cc = 100.0*len(v[1])/len(v[0]+v[1])
      if s > 0 and cc > 0:    cd = (100*c/s - 100)
      else:                   cd = 0.0
      
      print("%-40s cc=%-5.1f cd=%-5.0f #nc=%-4u #c=%-5u avg nc=%-4u avg c=%-4u" % (x, cc, cd, len(v[0]), len(v[1]), s, c))
  
  def parse(self, xxx_todo_changeme20):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme20
    if attacker == "You" and amount:
      try:
        if crit: self.abilities[ability][1].append(amount)
        else:    self.abilities[ability][0].append(amount)
      except KeyError:
        if crit:    self.abilities[ability] = [[],[amount,]]
        else:       self.abilities[ability] = [[amount,],[]]
  
  def poll(self):
    return False

# This class is a container for all raid bosses
class RAID(ParserWindow):
  lines = 3
  proportion = 1
  short_text = "Raiding"
  
  def __init__(self, parent):
    self.parsers = []
    self.last_action = 0
    self.cur_text = ""
    ParserWindow.__init__(self,parent)
  
  def poll(self):
    for p in self.parsers:
      try:
        ret = p.poll()
        if ret:
          self.parsers.remove(p)
          if not self.parsers:
            self.setText("")
      except:
        if verbose: raise
        else:       pass
    
    if not self.parsers and elapsed() - self.last_action > 60:
      self.setText("\n     Raiding\n#grey#_________________") # The line is for easier sizing of the window
    
    if self.parsers and self.last_action and elapsed() - self.last_action > 90:
      self.parsers = []
      self.setText("")
    
    return False
    
  def setText(self, text, scroll=True):
    text = text.rstrip()
    if text == self.cur_text:
      return
    
    self.cur_text = text
    ParserWindow.setText(self, text, scroll)
    self.last_action = elapsed()
  
  def parse(self, xxx_todo_changeme21):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme21
    if self.parsers:
      for p in self.parsers:
        try:
          p.parse((attacker, action, ability, target, amount, type, crit))
        except:
          if verbose: raise
          else:       pass
    else:
      for b,p in (
        # T3
        ("Kharon", self.TAS_Brothers),
        ("Daimone", self.TAS_Brothers),
        ("Ixion", self.TAS_Brothers),
        ("Hathor-Ka",self.TAS_HathorKa),
        ("Arbanus",self.TAS_Arbanus),
        # ("Master Gyas",self.TAS_Gyas), # Not implemented
        ("Favored of Louhi",self.TAS_Louhi),
        ("Hollow Knight",self.TAS_HollowKnight),
        ("Thoth-Amon",self.TAS_ThothAmon),
        
        # T3,5
        ("Archfiend of Gore", self.TOE_Archfiend),
        ("Arch Lector Zaal", self.TOE_Archlector),
        ("Bat of Nergal", self.TOE_Bat),
        
        # House of Crom
        ("Aspect of the Ruin", self.HOC_Lurker),
        ("The Lurker at the Threshold", self.HOC_Lurker),
        
        # T4
        ("Dai Gang", self.JC_Sheng),
        ("Zhu Meng", self.JC_Sheng),
        ("Yi Qin", self.JC_Sheng),
        # Missing: Basilisk
        ("Thaw", self.JC_Zodiac),
        ("Swelter", self.JC_Zodiac),
        ("Harvest", self.JC_Zodiac),
        ("Arctic", self.JC_Zodiac),
        ("Symbol of Spring", self.JC_Zodiac),
        ("Symbol of Summer", self.JC_Zodiac),
        ("Symbol of Autumn", self.JC_Zodiac),
        ("Symbol of Winter", self.JC_Zodiac),
        # Missing: Garden Imp
        ("Yah Chieng", self.JC_Cheng),
        # Missing: Memory Cloud
        ("The Entity", self.JC_Entity)
      ):
        if b in (attacker, target):
          self.last_action = elapsed()
          self.setText("")
          self.parsers.append(p(self)) # Should be window, but we want to override setText
          try:
            self.parsers[0].parse((attacker, action, ability, target, amount, type, crit))
          except:
            if verbose: raise
            else:       pass
  
  class TAS_Brothers(LogParser):
    # When death displayed in log       Including damage after death
    # Ixion		Kharon	Daimone						Ixion		Kharon	Daimone
    # 1545023	1460497	1631226						1545023	1461682	1631796
    # 1545060	1460939	1631282     	    1545949	1462124	1632073
    # 1545098	1461382	1631339						1546876	1462566	1632350
                  
    # 1545098	1461382	1631339						1546876	1461682	1632350
    # 1545023	1460497	1631226						1545023	1462566	1631796
    # 1548877 1463409 1620697         	1549410 1463649 1621422
    hp_max = {}
    hp_max["Ixion"] = 1545000
    hp_max["Kharon"] = 1460497
    hp_max["Daimone"] = 1631226
    spacer = {
      -5 : "!<   ",
      -4 : "!<   ",
      -3 : " <   ",
      -2 : " <   ",
      -1 : " <   ",
       0 : "  |  ",
       1 : "   > ",
       2 : "   > ",
       3 : "   > ",
       4 : "   >!",
       5 : "   >!"
    }
    def __init__(self, window):
      self.window = window
      self.finished = 0 # set to elapsed() when done; poll() will return True a few seconds later
      self.last_action = 0
      self.hp = {}
      for k,v in list(self.hp_max.items()):
        self.hp[k] = v
    
    def toPercent(self, boss):
      try:    return 100.0 * self.hp[boss]/self.hp_max[boss]
      except: return 50
        
    def parse(self, xxx_todo_changeme):
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme
      if action == "damage" and target in self.hp:
        self.hp[target] -= amount
        self.last_action = elapsed()
      elif action == "heal" and target in self.hp:
        self.hp[target] += amount
        self.last_action = elapsed()
      elif action == "die" and target in self.hp:
        self.hp[target] = 0
    
    def updateWindow(self):
      (d,k,i) = (self.toPercent("Daimone"), self.toPercent("Kharon"), self.toPercent("Ixion"))
      
      # Daimone and Kharon enrage when more than 5% difference in life
      # Ixion enter battle when one is at 50%
      diff = round(k-d)
      if abs(diff) < 1.5: colour = "green"
      elif abs(diff) < 4: colour = "yellow"
      else:               colour = "red"
      
      # Ensure all numbers are rounded properly, and diff is int and [-5,5]
      diff = int(round(diff))
      if diff < -5:   diff = -5
      elif diff > 5:  diff = 5
      (d,k,i) = (int(round(x)) for x in (d,k,i))
      
      # Only apply colour at the side with most life; other should be green
      # (We can only reduce their hp; the coloured one should be focused with dps)
      if d>k: text = " #%s#%3u%%%s#green#%u%%#\n" % (colour, d, self.spacer[diff], k)
      else:   text = " #green#%3u%%#%s#%s%u%%#\n" % (d, colour, self.spacer[diff], k)
      
      # Remember ixion, and display in window
      text += "      %2u%%" % i
      self.window.setText(text)
    
    def poll(self):
      if self.last_action > 0:
        if elapsed() - self.last_action < 30:
          # Fight ongoing; show information
          self.updateWindow()
        else:
          # Wipe/reset
          for k,v in list(self.hp_max.items()):
            self.hp[k] = v
          self.last_action = 0
          self.window.setText("")
          self.finished = elapsed()
      return LogParser.poll(self)
      
  class TAS_HathorKa(LogParser):
    def __init__(self, window):
      self.window = window
      self.finished = 0 # set to elapsed() when done; poll() will return True a few seconds later
      self.miasma = {} # keys are name of affected player, and value is timestamp of infection
    
    def parse(self, xxx_todo_changeme1):
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme1
      if action == "buff" and ability == "Miasma":
        self.miasma[target] = elapsed()
        self.updateWindow()
      
      elif action == "die" and target == "Hathor-Ka":
        self.finished = elapsed()
    
    def updateWindow(self):
      if not self.miasma:
        return
      
      cur_time = elapsed()
      text = "Infected:"
      
      for k,v in list(self.miasma.items()):
        if cur_time - v > 10: self.miasma.pop(k)
        elif k == "you":    text += "\n- #yellow#You#"
        else:               text += "\n- #blue#%s#" % k
      
      self.window.setText(text)
      
    def poll(self):
      self.updateWindow()
      return LogParser.poll(self)
      
  class TAS_Arbanus(LogParser):
    # XXX: This parser assumes that updateWindow is called every second
    DRAW_TO_RITUAL = 20
    
    def __init__(self, window):
      self.window = window
      self.finished = 0 # set to elapsed() when done; poll() will return True a few seconds later
      self.last_draw = 0
      self.bane = {} # Key is name, value is a counter that is incremented by poll(). Pair removed when counter >2
    
    def parse(self, xxx_todo_changeme2):
      # Bane is often reported as self-inflicted injury
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme2
      if action == "damage" and ability and "Grim Bane" in ability:
        self.bane[target] = 0
      # This means first stack; put something in self.bane since this is indicator of second phase
      elif action == "buff" and ability == "Grim Bane":
        self.bane[target] = 10
      
      # Time from blood draw to to ritual seems fairly constant; 22-25 seconds
      # Time from ritual to draw is 10 or 20 seconds, depending on arbanus' hp
      elif action == "buff" and attacker == "Arbanus" and ability == "Blood Draw":
        self.last_draw = elapsed()
      elif action == "cast" and attacker == "Arbanus" and ability == "Blood Ritual":
        self.last_draw = (elapsed() - self.DRAW_TO_RITUAL - 2) # 2 sec casting time
      
    def updateWindow(self):
      if not self.last_draw:
        return
      text = ""
      now = elapsed()
      time = int(round(now - self.last_draw))
      
      if time <= self.DRAW_TO_RITUAL:
        text = "Ritual: ~%us" % (self.DRAW_TO_RITUAL - time)
      else:
        if self.bane:   time_to_draw = 20 + self.DRAW_TO_RITUAL - time
        else:           time_to_draw = 10 + self.DRAW_TO_RITUAL - time
        if time_to_draw < 0: time_to_draw = 0
        
        if time_to_draw > 10:
          text = "Blood Draw: #green#~%us#" % (time_to_draw)
        elif time_to_draw > 5:
          text = "Blood Draw: #yellow#~%us#" % (time_to_draw)
        else:
          text = "Blood Draw: #red#~%us#" % (time_to_draw)
        
      for k in self.bane:
        self.bane[k] += 1
        if self.bane[k] > 2:    # value is continually set to 0 in parse()
          continue            # Only show those that were recently damaged by bane
        
        if k == "you":  text += "\n- #yellow#You#"
        else:           text += "\n- #blue#%s#" % k
      
      if self.bane:
        text += "\n  #grey#Grim Bane"
      
      self.window.setText(text, scroll=False)
      
    def poll(self):
      self.updateWindow()
      return (self.last_draw and elapsed() - self.last_draw > 60)
      
  class TAS_Gyas(LogParser):
    def __init__(self, window):
      self.window = window
      self.finished = 0 # set to elapsed() when done; poll() will return True a few seconds later
      impel = {}
    
    def parse(self, xxx_todo_changeme3):
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme3
      pass
      
    def updateWindow(self):
      pass
      
    def poll(self):
      return True
      # self.finished = elapsed()
      # return LogParser.poll(self)
      
  class TAS_Louhi(LogParser):
    # XXX: This parser assumes that updateWindow is called every second
    def __init__(self, window):
      self.window = window
      self.finished = 0 # set to elapsed() when done; poll() will return True a few seconds later
      self.ecstasy = {} # keys are name of affected player, and value is timestamp of infection and stack
      self.counter = 0
      self.phylactery = 0
    
    def parse(self, xxx_todo_changeme4):
      # First thing he casts
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme4
      if action == "cast" and attacker == "Favored of Louhi" and ability == "Spiritual Attunement":
        self.phylactery = 1
        self.counter = 59
      
      # Phylactery spawned
      elif action == "cast" and attacker == "Favored of Louhi" and ability == "Inspiring Light" and self.phylactery < 4:
        self.phylactery += 1
        self.counter = 60
      
      # Last phylactery spawned; divine ecstasy buff enabled
      elif action == "cast" and attacker == "Favored of Louhi" and ability == "Divine Ecstasy":
        self.counter = 0
        self.phylactery = 0
        self.ecstasy = {"you":(elapsed(),0)} # Populate with something, so that we start showing things in poll()
      
      # Someone affected with divine ecstasy; poll() remove them when they time out
      elif action == "buff" and attacker == "Favored of Louhi" and ability == "Divine Ecstacy" and " " not in target and "-" not in target:
        if target in self.ecstasy and elapsed() - self.ecstasy[target][0] < 12:
          self.ecstasy[target] = (elapsed(), self.ecstasy[target][1]+1)
        else:
          self.ecstasy[target] = (elapsed(), 1)
        
      # Louhi dead; our job is done
      elif action == "die" and target == "Favored of Louhi":
        self.finished = elapsed()
      
    def updateWindow(self):
      if self.phylactery == 0 and not self.ecstasy:
        return
      
      # Countdown to next phylactery; self.ecstasy is only populated after fourth spawn
      if self.phylactery > 0:
        self.window.setText("Phylactery %u\n- ~%u" % (self.phylactery, self.counter))
        if self.counter > 0:
          self.counter -= 1
        return
      
      # Countdown has stopped, now we got ecstasy
      now = elapsed()
      stack_3 = []
      stack_4 = []
      
      for k,v in list(self.ecstasy.items()):
        if now - v[0] > 12: self.ecstasy.pop(k)
        elif v[1] == 3: stack_3.append(k)
        elif v[1] == 4: stack_4.append(k)
      
      stack_3.sort()
      stack_4.sort()
      text = "Ecstasy:"
      for x in stack_3: text += "\n3 #yellow#%s#" % x
      for x in stack_4: text += "\n4 #red#%s#" % x
      
      self.window.setText(text)
      
    def poll(self):
      self.updateWindow()
      return LogParser.poll(self)
      
  class TAS_HollowKnight(LogParser):
    TIMER_SWORD_INTERVAL = 32
    TIMER_SWORD_BEGIN_OFFSET = 3
    TIMER_SWORD_FLAT_OFFSET = 3
    def __init__(self, window):
      self.window = window
      self.finished = 0 # set to elapsed() when done; poll() will return True a few seconds later
      self.target = ""
      self.start = elapsed()
      self.last_seen = elapsed()
      self.last_lacerate = elapsed()
      
    def parse(self, xxx_todo_changeme5):
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme5
      if "Hollow Knight" in (attacker, target):
        self.last_seen = elapsed()
    
      if action == "buff" and ability == "Human Prey":
        self.target = target
        self.updateWindow()
      elif action == "die" and target == self.target:
        self.target = ""
        self.updateWindow()
      elif action == "die" and target == "Hollow Knight":
        self.target = ""
        self.updateWindow()
        self.finished = elapsed()
      
    def updateWindow(self):
      duration = max(0,int(round(elapsed() - self.start)) - self.TIMER_SWORD_BEGIN_OFFSET)
      next_sword = max(0, self.TIMER_SWORD_INTERVAL - ((duration) % self.TIMER_SWORD_INTERVAL) - self.TIMER_SWORD_FLAT_OFFSET)
      text = "#Swords: %s\n" % next_sword
      
      if self.target == "you":
        text += "- #yellow#You!#"
      elif self.target:
        text += "- #blue#%s#" % self.target
      else:
        text += "- "
        
      self.window.setText(text)
      
    def poll(self):
      self.updateWindow()
      if self.finished == 0 and (elapsed() - self.last_seen) > 60:
        self.finished = elapsed()
      return LogParser.poll(self)
  
  class TAS_ThothAmon(LogParser):
    def __init__(self, window):
      self.window = window
      self.finished = 0 # set to elapsed() when done; poll() will return True a few seconds later
      self.acheron = ""
      self.next_doom = 0
      self.next_acheron = 0
      self.doom_count = 0
    
    def parse(self, xxx_todo_changeme6):
      # Event ongoing... (may be first time we see it)
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme6
      if action == "damage" and attacker == "Acheronian Soul" and self.acheron != target and target[0:13] != "Thoth-Amon's " and target != "Acheronian Soul":
        self.acheron = target
        self.next_acheron = 0
        self.window.setText("Mark of Acheron:\n- #blue#%s" % self.acheron)
      
      # End, completed
      elif action == "die" and self.acheron and target == "Acheronian Soul":
        self.acheron = ""
        self.next_acheron = 46
        self.window.setText("Mark of Acheron:\n-")
        
      # End, died
      elif action == "die" and target == self.acheron:
        self.acheron = ""
        self.next_acheron = 46
        self.window.setText("=== Killed\n- #blue#%s" % target)
        
      # End, charmed
      elif action == "buff" and ability == "Mark of Acheron":
        self.acheron = ""
        self.next_acheron = 46
        self.window.setText("!!! #red#Charmed#  !!!\n! #blue#%-13s#!" % target)
        
      # poll() counts down and displays a timer
      elif action == "damage" and ability == "Precognition of Doom":
        if self.next_doom < 20:
          self.next_acheron = 0
          self.next_doom = 47 # Shortest I've seen is 46s, average roughly 49s
          self.doom_count += 1
      
      # Last boss down :D
      elif action == "die" and target == "Thoth-Amon":
        self.next_doom = 0
        self.next_acheron = 0
        self.finished = elapsed()
        self.window.setText("\n Thoth-Amon dead.\n")
      
    def poll(self):
      if self.next_doom > 0:
        if self.next_doom > 10:     colour = ""
        elif self.next_doom > 5:    colour = "yellow"
        else:                       colour = "red"
        
        self.next_doom -= 1
        self.window.setText("Precognition %u:\n  #%s#~%us#" % (self.doom_count, colour, self.next_doom))
        
      elif self.next_acheron > 0:
        if self.next_acheron > 10:  colour = ""
        elif self.next_acheron > 5: colour = "yellow"
        else:                       colour = "red"
        
        self.next_acheron -= 1
        if self.next_acheron < 26: self.window.setText("Mark of Acheron:\n-  #%s#~%us#" % (colour,self.next_acheron))
        
      return LogParser.poll(self)
  
  class TOE_Archfiend(LogParser):
    TIMER_BLOOD = 30
    TIMER_VISCERA = 27
    TIMER_FORCE = 30
    TIMER_BATH = 80
    

    def __init__(self, window):
      self.window = window
      self.finished = False
      
      self.last_blood = 0
      self.blood_count = 0
      self.last_viscera = 0
      self.last_force = 0
      self.last_bath = elapsed()
      self.bath_count = 1
      self.bath_clicks = 0
    
    def parse(self, xxx_todo_changeme7):
      # Trigger when four players are coated. Counter is reset by poll()
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme7
      if ability == 'Crimson Coating':
        self.blood_count += 1
        if self.blood_count > 3 and (elapsed() - self.last_blood) > 25:
          self.last_blood = elapsed()
        
      elif ability == 'Twisted Viscera' and (elapsed() - self.last_viscera) > 5:
        self.last_viscera = elapsed()
        
      elif ability == 'Brutal Force' and (elapsed() - self.last_force) > 1:
        self.last_force = elapsed()
        
      elif ability == 'Bathed in Blood' and attacker == 'Archfiend of Gore' and (elapsed() - self.last_bath) > 1:
        self.last_bath = elapsed()
        self.bath_count += 1
        self.bath_clicks = 0
      
      elif ability == 'Bathed in Blood' and attacker != 'Archfiend of Gore' and (elapsed() - self.last_bath) < 50:
        self.bath_clicks += 1
        
    def updateWindow(self):
      # Blood rising
      next = max(0,(self.TIMER_BLOOD - (elapsed() - self.last_blood)))
      text = "Blood:   #red#%u#\n" % next
      
      # Twisted Viscera
      next_viscera = max(0,self.TIMER_VISCERA - (elapsed() - self.last_viscera))
      text += "Viscera: #blue#%u#\n" % next_viscera
      
      # Bathed in Blood
      if self.bath_count > 1 and elapsed() - self.last_bath < 30:
        text += "Bath %u:  #yellow#%u# click#" % (self.bath_count-1, self.bath_clicks)
      else:
        next = max(0,(self.TIMER_BATH - (elapsed() - self.last_bath)))
        text += "Bath %u:  #yellow#%u#" % (self.bath_count, next)
      
      self.window.setText(text)
      
    
    def poll(self):
      self.updateWindow()
      self.blood_count = 0
      return LogParser.poll(self)
    
  class TOE_Archlector(LogParser):
    TIMER_DEBUFFS = 22
    TIMER_ENRAGE = 120
    TIMER_BACKLASH = 21
    TIMER_VEIL = 21
    TIMER_REVERSAL = 33
    

    def __init__(self, window):
      self.window = window
      self.finished = False
      
      self.debuffs2 = ("Zaal's Wrack", "Zaal's Ruin", "Zaal's Torment")
      
      self.phase = 1
      self.ghost_spawn = 0
      self.last_debuffs = 0
      self.last_backlash = elapsed() - self.TIMER_BACKLASH + 16
      self.last_veil = elapsed() - self.TIMER_VEIL + 12
      self.last_reversal = elapsed() - self.TIMER_REVERSAL + 8
      
    def parse(self, xxx_todo_changeme8):
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme8
      if attacker == 'Arch Lector Zaal':
      
        if action == 'buff' and ability:
          if ability in self.debuffs2 and elapsed() - self.last_debuffs > self.TIMER_DEBUFFS - 5:
            self.last_debuffs = elapsed()
          elif ability == "Nauseating Backlash" and elapsed() - self.last_backlash > self.TIMER_BACKLASH - 5:
            self.last_backlash = elapsed()
          elif ability == "Veil of the Unliving" and elapsed() - self.last_veil > self.TIMER_VEIL - 5:
            self.last_veil = elapsed()
          elif ability == "Unholy Reversal" and elapsed() - self.last_reversal > self.TIMER_REVERSAL - 5:
            self.last_reversal = elapsed()
      
        if action == 'cast' and ability == 'Expiration':
          self.phase = 2
          self.ghost_spawn = elapsed()
          # Debuffs will be cast within a few seconds
      
      if action == 'die' and target == 'Arch Lector Zaal':
        self.phase = 1
        self.last_backlash = elapsed() - self.TIMER_BACKLASH + 15
        self.last_veil = elapsed() - self.TIMER_VEIL + 5
        
    def updateWindow(self):
      if self.phase == 1:
        time_left = max(0,(self.TIMER_BACKLASH - (elapsed() - self.last_backlash)))
        text = "Backlash:  #yellow#%u#\n" % time_left
        
        time_left = max(0,(self.TIMER_VEIL - (elapsed() - self.last_veil)))
        text += "Veil:      #blue#%u#\n" % time_left
        
        time_left = max(0,(self.TIMER_REVERSAL - (elapsed() - self.last_reversal)))
        text += "Reversal:  #red#%u#" % time_left
        
      elif self.phase == 2:
        time_left = max(0,(self.TIMER_DEBUFFS - (elapsed() - self.last_debuffs)))
        text = "Debuffs:   #blue#%u#\n" % time_left
        
        time_left = max(0,(self.TIMER_ENRAGE - (elapsed() - self.ghost_spawn)))
        text += "Enrage:    %u" % time_left
      
      self.window.setText(text)
      
    
    def poll(self):
      self.updateWindow()
      return LogParser.poll(self)
  
  class TOE_Bat(LogParser):
    TIMER_PARASITE = 120
    TIMER_DAMAGEPHASE = 31

    # http://img401.imageshack.us/img401/3475/tandirapicture000.png
    # Banish Blessing: Every 30+s, one person
    # Parasite: Every two minutes, one person. Miasma, but each transfer only go to two people after 4/8 secs
    #  At twelve stacks, becomes supercharged parasite that removes shield on boss
    # Host: Received with parasite, probably to avoid reinfection
    
    # Nergal's Ruin + Wrath: Root. cone, every 32-37s. Wrath = DoT
    # Sonic Ripple: Duration 3s, effect Deafened. Every 32-33s, with more affected every 2-4s shortly afterwards
    # Deafened: Same as Sonic Ripple
    
    # Shock protection?
    
    # Dimensional Aftershock: AoE, damage, every 2sec. Unknown targeting
    
    
    def __init__(self, window):
      self.window = window
      self.finished = False
      
      self.first_action = elapsed()
      self.parasites = {}
      self.last_parasite = 0
      self.supercharged = 0
      
      self.last_jump = 0
      
    def parse(self, xxx_todo_changeme9):
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme9
      if attacker == 'Bat of Nergal':
        if action == "buff":
        
          if ability == "Nergal's Parasite (1)":
            self.last_parasite = elapsed()
            self.last_jump = elapsed()
          
          # Parasite 1-11
          m = re.match(r"Nergal\'s Parasite \((\d+)\)", ability)
          if m:
            stack = int(m.group(1))
            self.parasites[target] = [elapsed(), stack]
            jump_time = round(elapsed() - self.last_jump)
            # if jump_time > 1: print "%s%u - Parasite jump (%u)" % (" "*(stack-2), jump_time, stack)
            self.last_jump = elapsed()
        
          # Parasite 12
          if ability == 'Supercharged Parasite' and target != 'Bat of Nergal':
              self.parasites[target] = [elapsed(), 12]
        
        # Supercharge done; damage shield is removed
        if action == "cast" and ability and ability == 'Supercharged Parasite':
          self.supercharged = elapsed()
          self.last_parasite = max(elapsed() + 40 - self.TIMER_PARASITE, self.last_parasite)
    
    def updateWindow(self):
      next_parasite = max(self.TIMER_PARASITE - (elapsed() - self.last_parasite), 0)
      
      if (elapsed() - self.supercharged) < (self.TIMER_DAMAGEPHASE + 3):
        text = "Damage: %u\n" % max((self.TIMER_DAMAGEPHASE - (elapsed() - self.supercharged)), 0)
        # 52:38: cast Supercharged Parasite
        # 53:09 last damage
        # 53:15 Sonic Splash
        # 53:18 Nergal's protection
        # 53:18 continue damage
      
      elif next_parasite > 10 and self.parasites:
        text = ""
      else:
        text = "Parasite: %u\n" % next_parasite
      
      if self.parasites:
        lines = []
        list = [(self.parasites[x][1], x[:13], max(0, 8.5 - (elapsed() - self.parasites[x][0]))) for x in list(self.parasites.keys()) if elapsed() - self.parasites[x][0] < 10]
        list.sort(reverse=True)
        if list:
          max_stack = list[0][0]
          for x in list:
            if x[0] == 12:
              text += "#blue#%u %-13s%u#\n" % x
            elif x[0] == max_stack:
              text += "#%u %-13s%u#\n" % x
          
      self.window.setText(text, False)
    
    def poll(self):
      for x in list(self.parasites.keys()):
        if elapsed() - self.parasites[x][0] > 10:
          del self.parasites[x]
      self.updateWindow()
      return LogParser.poll(self)
  
  class HOC_Lurker(StandardBoss):
    def getAbilities(self):
      return [
        AbilityCountdown("Hungry Void", timer=21, attacker="The Lurker at the Threshold", action="cast", ability='Hungry Void'),
        CyclicAbilityCountdown("Cognizance", timer=57, attacker="The Lurker at the Threshold", action="cast", ability='Bilious Mantle'),
        AbilityCountdown("Corrosive Burst", timer=10, attacker="Aspect of the Ruin", action="damage", ability='Corrosive Burst', colours=(6,3)),
      ]
      
  class JC_Sheng(LogParser):
    def __init__(self, window):
      self.window = window
      self.finished = 0 # set to elapsed() when done; poll() will return True a few seconds later
      self.last_action = 0
      self.start = elapsed()
      self.aflame = {} # "player" : last_damaged
      self.last_debuff = elapsed() + 3
    
    def parse(self, xxx_todo_changeme10):
    
      # Abilities by mini-bosses and Sheng
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme10
      if attacker in ("Zhu Meng","Dai Gang","Yi Qin") and ability \
          and ability in ("Qi Drain", "Demoralizing Shout", "Vital Mark"):
        self.last_debuff = elapsed()
      if action == "damage" and ability and ability == "Aflame":
        self.aflame[target] = elapsed()            
      
    def getColouredTimer(self, time):
      if time < 0: time = 0
      if time > 10:   return "#green#%2u#" % time
      elif time > 5:  return "#yellow#%2u#" % time
      else:           return "#red#%2u#" % time
    
    def updateWindow(self):
      
      text = "Debuffs:    %s" % self.getColouredTimer(int(round(24 - (elapsed() - self.last_debuff))))
      
      if not self.aflame:
        text += "\n#grey#Aflame#"
      
      if self.aflame:
        for k in self.aflame:
          if elapsed() - self.aflame[k] < 5:
            if k == "you":  text += "\n- #yellow#You#"
            else:           text += "\n- #blue#%s#" % k
      
        text += "\n  #grey#Aflame#"
      
      
      self.window.setText(text)
      
    
    def poll(self):
      self.updateWindow()
      if self.last_action > 0 and elapsed() - self.last_action > 60:
        # Wipe/reset
        for k,v in list(self.hp_max.items()):
          self.hp[k] = v
        self.last_action = 0
        self.window.setText("")
        self.finished = elapsed()
      return LogParser.poll(self)
  
  class JC_Zodiac(StandardBoss):
    def getAbilities(self):
      return [
        AbilityCountdown("Meteor", timer=30, timer_start=13, timer_suspend=10, ability='Meteor', type='!shield'),
      ]
  
  class JC_Zodiac_old(LogParser):
    TIMER_METEOR = 30
    TIMER_WINDS = 20
    
    def __init__(self, window):
      self.window = window
      self.finished = False
      
      self.last_meteor = elapsed() + 13 - self.TIMER_METEOR
  
    def parse(self, xxx_todo_changeme11):
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme11
      if ability and ability == 'Meteor' and type != 'shield':
        if (elapsed() - self.last_meteor) > 10:
          self.last_meteor = elapsed()
      
      if action == 'damage':
        self.finished = elapsed()
    
    def updateWindow(self):
      next = max(0,(self.TIMER_METEOR - (elapsed() - self.last_meteor)))
      if   next > 10: colour = ""
      elif next > 5:  colour = "yellow"
      else:           colour = "red"
      text = "Meteor:  #%s#%u#\n" % (colour, next)
      
      
      self.window.setText(text)
    
    def poll(self):
      self.updateWindow()
      return LogParser.poll(self)
  
  class JC_Cheng(StandardBoss):
    def getAbilities(self):
      return [
        AbilityCountdown("Golem", timer=65, timer_suspend=10, attacker="Bone Golem", action="cast", ability='Self Destruct', colours=(15,5)),
        AbilityCountdown("Affliction", 33, attacker="Yah Chieng", action="buff", ability="Mortal Affliction"),
        AbilityCountdown("Devouring Pact", 41, attacker="Yah Chieng", action="cast", ability="Devouring Pact", colours=(15,10)),
      ]
  
  class JC_Cheng_old(LogParser):
    TIMER_GOLEM = 65
    TIMER_AFFLICTION = 33
    TIMER_PACT = 41
    
    def __init__(self, window):
      self.window = window
      self.finished = False
      
      self.last_golem = 0
      self.last_affliction = 0
      self.last_pact = 0
  
    def parse(self, xxx_todo_changeme12):
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme12
      if attacker == "Bone Golem" and action == "cast" and ability and ability == "Self Destruct":
        if elapsed() - self.last_golem > 5:
          self.last_golem = elapsed()
      
      if attacker == "Yah Chieng" and action == "buff" and ability and ability == "Mortal Affliction":
        self.last_affliction = elapsed()
      
      if attacker == "Yah Chieng" and action == "cast" and ability and ability == "Devouring Pact":
        self.last_pact = elapsed()
      
      if action == 'damage':
        self.finished = elapsed()
    
    def updateWindow(self):
      next = max(0,(self.TIMER_GOLEM - (elapsed() - self.last_golem)))
      if self.last_golem == 0: colour = ""
      elif next > 15: colour = ""
      elif next > 5:  colour = "yellow"
      else:           colour = "red"
      text = "Golem:          #%s#%u#\n" % (colour, next)
      
      next = max(0,(self.TIMER_AFFLICTION - (elapsed() - self.last_affliction)))
      if self.last_affliction == 0: colour = ""
      elif next > 10: colour = ""
      elif next > 5:  colour = "yellow"
      else:           colour = "red"
      text += "Affliction:     #%s#%u#\n" % (colour, next)
      
      next = max(0,(self.TIMER_PACT - (elapsed() - self.last_pact)))
      if self.last_pact == 0: colour = ""
      elif next > 15: colour = ""
      elif next > 10:  colour = "yellow"
      else:           colour = "red"
      text += "Devouring Pact: #%s#%u#" % (colour, next)
      
      self.window.setText(text)
    
    def poll(self):
      self.updateWindow()
      return LogParser.poll(self)
  
  class JC_Entity(StandardBoss):
    def getAbilities(self):
      return [
        AbilityCountdown("Target", timer=55-3, timer_start=20, timer_suspend=26, attacker="Photon Beam", action="cast", ability='Beam', colours=(15,5)),
        CyclicAbilityCountdown("Vortex", timer=60, attacker="Photon Bomb", action="damage", ability='XX_Pulsing Energy Effect', colours=(15,5)),
      ]
  
  class JC_Entity_old(LogParser):
    TIMER_BEAM = 55 - 3
    TIMER_DEATH = 60
    
    def __init__(self, window):
      self.window = window
      self.finished = False
      
      self.last_beam = elapsed() + 20 - self.TIMER_BEAM
      self.first_death = 0
  
    def parse(self, xxx_todo_changeme13):
      (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme13
      if attacker == "Photon Beam" and action == "cast" and ability and ability == "Beam":
        if elapsed() - self.last_beam > self.TIMER_BEAM/2:
          self.last_beam = elapsed()
      
      if self.first_death == 0 and attacker == "Photon Bomb" and \
            action == "damage" and ability == "XX_Pulsing Energy Effect":
        self.first_death = elapsed()
        
      if action == 'damage':
        self.finished = elapsed()
    
    def updateWindow(self):
      next = max(0,(self.TIMER_BEAM - (elapsed() - self.last_beam)))
      if self.last_beam == 0: colour = ""
      elif next > 15: colour = ""
      elif next > 5:  colour = "yellow"
      else:           colour = "red"
      text = "Target:       #%s#%u#\n" % (colour, next)
      
      if self.first_death == 0:
        next = 0
      else:
        next = self.TIMER_DEATH - ((elapsed() - self.first_death) % self.TIMER_DEATH)
      if next == 60: next = 0
      if self.first_death == 0: colour = "grey"
      elif next > 15: colour = ""
      elif next > 5:  colour = "yellow"
      else:           colour = "red"
      text += "Vortex:       #%s#%u#\n" % (colour, next)
      
      self.window.setText(text)
    
    def poll(self):
      self.updateWindow()
      return LogParser.poll(self)
 
# This class presents your own dps
class DPS(ParserWindow):
  short_text = "DPS meter"
  
  def __init__(self, parent):
    ParserWindow.__init__(self,parent)
    self.total = []
    self.encounter = []
    self.current = []
    self.current_damage = 0
    self.last_action = 0 # number of poll()'s since we last dealt damage
    self.WriteText("All Encounter Now")
  
  def parse(self, xxx_todo_changeme22):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme22
    if action == "damage" and attacker in ("You","you"):
      self.current_damage += amount
      
  def updateWindow(self):
    if self.total:
      self.setText("%5u%6u%6u" % (average(self.total), average(self.encounter), average(self.current)))
      
  def poll(self):
    if self.current_damage == 0:
      self.last_action += 1
    
    # Only add to total/encounter if we are actually fighting
    if self.current_damage:
      # Thirty seconds without dealing damage? We call that end of battle...
      if self.last_action > 30:
        self.encounter = []
        self.last_action = 0
      elif self.last_action > 0: # We do this check to avoid many empty seconds between each encounter
        self.total.extend([0] * self.last_action)
        self.encounter.extend([0] * self.last_action)
        self.last_action = 0
      self.total.append(self.current_damage)
      self.encounter.append(self.current_damage)
    
    self.current = [self.current_damage] + self.current[:4]
    
    # print("%5u%6u%6u" % (average(self.total), average(self.encounter), average(self.current)))

    self.updateWindow()
    self.current_damage = 0
    return False

# This class gives list of available Dread Shadows, with cooldown and time to live
class DS(ParserWindow):
  lines = 2
  short_text = "Dread Shadow countdown"
  
  def __init__(self, parent):
    ParserWindow.__init__(self,parent)
    self.templars = {} # "Name" : time_for_last_dread_shadow
    self.unknown_shadow = 0
  
  def parse(self, xxx_todo_changeme23):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme23
    if not self.unknown_shadow and action == "cast" and ability == "Dread Shadow":
      self.unknown_shadow = elapsed() # Someone just summoned a dread shadow; unknown who
     
    elif self.unknown_shadow and action == "damage" and ability == "Dread Shadow":
      try:
        if self.unknown_shadow - self.templars[attacker] < 20:
          return # We got several active shadows; this is another one
      except:
        pass
      self.templars[attacker] = self.unknown_shadow
      self.unknown_shadow = 0
    
  def updateWindow(self):
    line = [" "," "]
    
    for dt, x in self.templars.items():
      cooldown = int(round(elapsed() - x))
      if cooldown > 60: # off cooldown
        line[0] += "%4s" % dt[0:4]
        line[1] += "    "
      elif cooldown > 17: # on cooldown, pet dead
        line[0] += "#grey#%4s#" % dt[0:4]
        line[1] += "#grey#%3u #" % (60 - cooldown)
      else: # Pet still alive
        line[0] += "%4s" % dt[0:4]
        line[1] += "#green#%3u #" % (17 - cooldown)
      
      # Add some space if we can afford it
      if len(self.templars) <= 3:
        line[0] += " "
        line[1] += " "
    
    self.setText("\n".join(line))
    
  def poll(self):
    self.updateWindow()

# This class displays a matrix of possible mitigation debuffs with colours to indicate timeouts
class DEBUFF(ParserWindow):
  lines = 3
  short_text = "Debuff overview"
  
  types = {
    "Wrack" : 0,
    "Ruin" : 1,
    "Torment" : 2,
  }
  categories = (
    "Spiritual",
    "Physical",
    "Elemental",
  )
  timeout = {
    "Wrack" : 30,
    "Ruin" : 15,
    "Torment" : 30,
  }
  
  def __init__(self, parent):
    ParserWindow.__init__(self,parent)
    
    # The three first numbers are time of last seen wrack, ruin, torment,
    # and last is the torment count
    self.debuffs = {}
    for x in self.categories:
      self.debuffs[x] = [0,0,0,0]
  
  def parse(self, xxx_todo_changeme24):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme24
    if action == "buff" and ability in ("Spiritual Wrack", "Spiritual Ruin", "Spiritual Torment", 
            "Physical Wrack", "Physical Ruin", "Physical Torment", 
            "Elemental Wrack", "Elemental Ruin", "Elemental Torment"):
      cat, type = ability.split(" ")
      try:
        if type == "Torment":
          # Previous torment timed out; reset to 0 and increment
          if elapsed() - self.debuffs[cat][self.types[type]] > self.timeout[type]:
            self.debuffs[cat][3] = 1
          elif self.debuffs[cat][3] < 5:
            self.debuffs[cat][3] += 1
        
        self.debuffs[cat][self.types[type]] = elapsed()
      except IOError:
        pass
    
  def updateWindow(self):
    line = ["#%-12s" % x for x in self.categories]
    now = elapsed()
    for x in range(len(self.categories)):
      for y in self.types:
        # Duration on scale from 0 (just applied) through 1 (timed out) to infinite
        duration = (now-self.debuffs[self.categories[x]][self.types[y]]) / self.timeout[y]
        
        # Reset torment-counter when it times out
        if y == "Torment" and duration >= 1:
          self.debuffs[self.categories[x]][3] = 0
        
        if y == "Torment" and self.debuffs[self.categories[x]][3] in (1,2,3,4):
          text = "%u" % self.debuffs[self.categories[x]][3]
        else:
          text = y[0:1]
        
        if duration < 0.67:
          line[x] += "#green#%s" % text
        elif duration < 1:
          line[x] += "#yellow#%s" % text
        else:
          line[x] += "#red#%s" % text
        
    
    self.setText("\n".join(line))
    
  def poll(self):
    self.updateWindow()

# This class displays timeout for necro dots used by the player
class DOTS(ParserWindow):
  lines = 1
  short_text = "Necro DOT monitor"
  
  TIMEOUT_PB   = 15.5
  TIMEOUT_FTW  = 36.5
  TIMEOUT_MOTD = 30.5
  
  def __init__(self, parent):
    ParserWindow.__init__(self,parent)
    
    self.pb   = elapsed() - self.TIMEOUT_PB
    self.ftw  = elapsed() - self.TIMEOUT_FTW
    self.motd = elapsed() - self.TIMEOUT_MOTD
    
    # The durations can be increased with AA
    self.time_pb   = self.TIMEOUT_PB
    self.time_ftw  = self.TIMEOUT_FTW
    self.time_motd = self.TIMEOUT_MOTD
  
  def parse(self, xxx_todo_changeme25):
    (attacker, action, ability, target, amount, type, crit) = xxx_todo_changeme25
    if attacker == "You":
      # What is the best way of doing this?
      # We must account for lagspikes that could lead to duration anomalies
      # Detect extended duration of dots
      # if action == "damage" and ability:
        # if ability[0:18] == "Pestilential Blast" and elapsed() - self.pb > self.time_pb:
          # self.time_pb += 1
        # elif ability[0:14] == "Flesh to Worms" and elapsed() - self.ftw > self.time_ftw:
          # self.time_ftw += 1
      
      # Detect application of dot
      if action == "buff" and ability:
        if   ability[0:18] == "Pestilential Blast":   self.pb   = elapsed()
        elif ability[0:14] == "Flesh to Worms":       self.ftw  = elapsed()
        elif ability[0:20] == "Mark of the Devourer": self.motd = elapsed()
  
  def updateWindow(self):
    text = " "
    
    # Pestilential blast
    duration = self.time_pb - (elapsed() - self.pb)
    if duration < 0:    text += "#grey#PB"
    elif duration < 2:  text += "#red#%2u" % duration
    elif duration < 5:  text += "#yellow#%2u" % duration
    else:               text += "#green#%2u" % duration
    
    text += "   "
    # Flesh to Worms
    duration = self.time_ftw - (elapsed() - self.ftw)
    if duration < 0:    text += "#grey#FtW"
    elif duration < 2:  text += "#red#%2u " % duration
    elif duration < 5:  text += "#yellow#%2u " % duration
    else:               text += "#green#%2u " % duration
    
    text += "  "
    # Mark of the Devourer
    duration = self.time_motd - (elapsed() - self.motd)
    if duration < 0:    text += "#grey#MotD"
    elif duration < 2:  text += "#red#%2u" % duration
    elif duration < 5:  text += "#yellow#%2u" % duration
    else:               text += "#green#%2u" % duration
    
    self.setText(text)
    
  def poll(self):
    self.updateWindow()

parsers = {
  #enum.RAID : RAID,
  enum.DPS : DPS,
  #enum.DS  : DS,
  #enum.DEBUFF  : DEBUFF,
  #enum.DOTS  : DOTS,
}

# This is the main window for the application.
# It has many sub-windows of type ParserWindow which has the actual logic for the boss-fights
class MainWindow(wx.Frame):
  default_settings = {
    "window_position" : (0,0),
    "always_on_top" :   True,
    "minimal_ui" :      False,
    "save_settings" :   False,
    "font_adjustment" : 1,
    "parsers" :         [enum.DPS,],
  }
  print("Hello 2")

  def __init__(self, title, parser):
    self.settings = self.default_settings
    try:
      fp = open("AOChelper.cfg", "rb")
      saved = pickle.load(fp)
      fp.close()
      for k,v in saved.items():
        self.settings[k] = v
    except:
      pass
    finally:
      # Sanity checks; enable menubar if we don't have any parsers so users won't get confused
      if not self.settings["parsers"]:
        self.settings["minimal_ui"] = False
      
      # Make sure we are not outside of screen
      self.settings["window_position"] = (min(self.settings["window_position"][0], wx.ScreenDC().GetSize()[0] - 50),
                        min(self.settings["window_position"][1], wx.ScreenDC().GetSize()[1] - 50))
                        
      # Temporary hack to merge all raid parsers to one for those with stored settings that include the old, individual parsers
      for x in (enum.TOE, enum.JC):
        if x in self.settings["parsers"]:
          if enum.RAID in self.settings["parsers"]:
            self.settings["parsers"].remove(x)
          else:
            self.settings["parsers"][self.settings["parsers"].index(x)] = enum.RAID
      
    self.parser = parser
    self.font = (23,45)
    self.windows = {}
    self.LastPosition = wx.Point(0,0)
    self.box = wx.BoxSizer(wx.VERTICAL)
    
    wx.Frame.__init__(self, None, title=title, pos=self.settings["window_position"], style=wx.FRAME_NO_TASKBAR) # Border and stuff is set in FixVisualLook, called later in constructor
    
    # Bind events
    self.Bind(wx.EVT_MOVE, self.OnMove)
    self.Bind(wx.EVT_CLOSE, self.OnClose)
    self.Bind(wx.EVT_CONTEXT_MENU, self.ShowMenu)
    
    #self.SetFont(wx.FontFromPixelSize(self.font, wx.MODERN, wx.NORMAL, wx.BOLD))
    #if self.settings["always_on_top"]:
    #  self.SetWindowStyle(self.GetWindowStyle() | wx.STAY_ON_TOP)
    #else:
    #  self.SetWindowStyle(self.GetWindowStyle() & ~wx.STAY_ON_TOP)
    
    # Menu with settings, reachable with right-click and from menubar
    self.menu = wx.Menu()
    self.menubar = wx.MenuBar()
    self.menubar.Append(self.menu, "&Settings");
    
    m_aot = self.menu.AppendCheckItem(enum.AOT, "Always on top")
    m_aot.Check(self.settings["always_on_top"])
    self.Bind(wx.EVT_MENU, self.SettingsChanged, m_aot)
    
    m_tmb = self.menu.AppendCheckItem(enum.MIN, "Minimal UI")
    m_tmb.Check(self.settings["minimal_ui"])
    self.Bind(wx.EVT_MENU, self.SettingsChanged, m_tmb)
    
    m_ss = self.menu.AppendCheckItem(enum.SS, "Save settings on exit")
    m_ss.Check(self.settings["save_settings"])
    self.Bind(wx.EVT_MENU, self.SettingsChanged, m_ss)
    
    m_finc = self.menu.Append(enum.FINC, "Increase font size\t+")
    self.Bind(wx.EVT_MENU, self.SettingsChanged, m_finc)
    
    m_fdec = self.menu.Append(enum.FDEC, "Decrease font size\t-")
    self.Bind(wx.EVT_MENU, self.SettingsChanged, m_fdec)
    
    # Add hotkeys for numpad +/- as well
    self.SetAcceleratorTable(wx.AcceleratorTable([
                            (wx.ACCEL_NORMAL, wx.WXK_NUMPAD_ADD, enum.FINC),
                            (wx.ACCEL_NORMAL, wx.WXK_NUMPAD_SUBTRACT, enum.FDEC),
                          ]))
    
    self.menu.AppendSeparator() # Parsers will be appended after this separator
    
    # List of available parsers
    for id,class_name in parsers.items():
      # Create a menu item for the parser, so we can enable/disable it
      menu_item = self.menu.AppendCheckItem(id, class_name.short_text)
      menu_item.Check(id in self.settings["parsers"])
      self.Bind(wx.EVT_MENU, self.SettingsChanged, menu_item)
    
    self.menu.AppendSeparator()
    m_exit = self.menu.Append(enum.EXIT, "Exit")
    self.Bind(wx.EVT_MENU, self.SettingsChanged, m_exit)
    
    # Add the default parsers
    for id in self.settings["parsers"]:
      self.AddParser(id)
    
    # Fix layout and stuff
    self.FixVisualLook() # Adjust size; font is already correct
    self.SetAutoLayout(True)
    self.SetSizer(self.box)
    self.Layout()
    
  def ShowMenu(self, event):
    self.PopupMenu(self.menu)
  def OnMotion(self, event):
    if event.LeftIsDown():
      self.SetPosition(self.GetPosition() + (event.GetPosition() - self.LastPosition))
  def OnLeftDown(self, event):
    self.LastPosition = event.GetPosition()
    event.Skip(False)
    
  def OnMove(self, event):
    # Move the window a couple of pixels if it is close to a corner
    resx,resy = wx.ScreenDC().GetSize()
    lenx,leny = self.GetSize()
    x,y = self.GetPosition()
    if abs(x) <= 10:
      x = 0
    elif abs(x + lenx - resx) <= 10:
      x = resx - lenx
    if abs(y) <= 10:
      y = 0
    elif abs(y + leny - resy) <= 10:
      y = resy - leny
    self.SetPosition((x,y))
    
    self.settings["window_position"] = (x,y)
    self.SaveSettings()
  def OnClose(self, event):
    ids = [id for id in self.windows]
    for x in ids:
      self.DelParser(x)
    self.parser.exit()
    
    # Wait up to two seconds for parser to exit
    for x in range(10):
      if self.parser.isAlive():
        real_time.sleep(0.2)
    self.Destroy()
  
  def SettingsChanged(self, event):
    id = event.GetId()
    
    if id == enum.AOT:
      self.SetWindowStyle(self.GetWindowStyle() ^ wx.STAY_ON_TOP)
      self.settings["always_on_top"] = (self.GetWindowStyle() & wx.STAY_ON_TOP and True or False)

    elif id == enum.MIN:
      self.settings["minimal_ui"] = (not self.settings["minimal_ui"])
        
    elif id == enum.SS:
      self.settings["save_settings"] = (not self.settings["save_settings"])
      
    elif id == enum.FINC:
      self.settings["font_adjustment"] += 0.1
    elif id == enum.FDEC:
      if self.settings["font_adjustment"] > 0.1:
        self.settings["font_adjustment"] -= 0.1
    
    elif id == enum.EXIT:
      self.Close()
    
    elif id in self.windows:
      self.DelParser(id)
      while id in self.settings["parsers"]:
        self.settings["parsers"].remove(id)
    elif id in parsers:
      self.AddParser(id)
      self.settings["parsers"].append(id)
    
    self.SaveSettings()
    self.FixVisualLook()
  
  def SaveSettings(self):
    try:
      if self.settings["save_settings"]:
        fp = open("AOChelper.cfg", "wb")
        pickle.dump(self.settings, fp)
        fp.close()
      else:
        os.remove("AOChelper.cfg")
    except:
      pass
  
  def AddParser(self, class_id):
    # Create a window for the parser
    p = parsers[class_id](self)
    self.windows[class_id] = p
    self.box.Add(p, p.proportion, wx.EXPAND)
    p.Show(True)
    
    # Hand the ParserWindow to the ParserThread
    self.parser.parsers.append(p)
  
  def DelParser(self, class_id):
    # Remove the LogParser from other thread
    self.parser.parsers.remove(self.windows[class_id])
    
    # Remove the window from our sizer
    self.box.Remove(self.windows[class_id])
    
    # .. and destroy the ParserWindow
    self.windows[class_id].Destroy()
    self.windows.pop(class_id)
  
  # Sometimes the parser thread prints stuff; we use the biggest visible window to show that
  def setText(self, text, scroll=False):
    window = None
    height = -1
    # Look for the biggest window, and output text there
    for v in self.windows.values():
      if v and v.IsShown():
        if v.GetSize()[1] > height:
          window = v
          height = v.GetSize()[1]
    if window:
      window.setText(text, scroll)
  
  def FixVisualLook(self):
    # Borders and menubar; "minimal mode"
    if self.settings["minimal_ui"] and len(self.windows) > 0:
      self.SetMenuBar(None)
      self.SetWindowStyle((self.GetWindowStyle() | wx.NO_BORDER) & (~wx.DEFAULT_FRAME_STYLE) | wx.RESIZE_BORDER)
    else:
      self.SetMenuBar(self.menubar)
      self.SetWindowStyle(self.GetWindowStyle() | wx.DEFAULT_FRAME_STYLE & ~(wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX ))
    
    # Font
    font = self.GetFont()
    font.SetPixelSize((self.font[0]*self.settings["font_adjustment"], self.font[1]*self.settings["font_adjustment"]))
    self.SetFont(font)
    
    x,y = font.GetPixelSize()
    lines = 0
    
    # Size of self and sub-windows
    for w in self.windows.values():
      w.SetFont(font)
      w.SetMinSize((0,w.lines*y+wx.SYS_FRAMESIZE_Y))
      lines += w.lines
    

    print("Hello 3")

    self.SetClientSize((x*18 + wx.SYS_FRAMESIZE_X, y*lines + wx.SYS_FRAMESIZE_Y*len(self.windows)))
    self.OnMove(None) # Emulate a move to dock to sides
  
def usage():
  print("")
  print("AOChelper.py [-z] [-v|-q] [-f <CombatLog-YYYY-MM-DD_HHMM.txt>] [-s 10]")
  print("General options:")
  print("    -z               Discard saved settings")
  print("    -v               Verbose; prints more information on console")
  print("    -q               Quiet; prints less information on console")
  print("    -b               Enable BossDisplay")
  print("    -d               Enable DebuffFinder")
  print()
  print("Playback: options")
  print("    -f <filename>    Parse filename as a combatlog, at original speed")
  print("    -s XX            Speed up playback of file XX times")
  exit()

def main(argv):
  global speedup, start_time, verbose
  verbose = 0
  speedup = 1
  debuff_finder = False
  boss_display = False
  start_time = real_time.time()
  log = None

  try:
    opts, args = getopt.getopt(argv, "hs:f:vqdbz", ["help", "speedup", "file", "verbose", "quiet", "debuff-finder", "boss-display", "no-config"])
  except getopt.GetoptError:
    usage()
  
  for opt, arg in opts:
    if opt in ("-h", "--help"):
      usage()
    elif opt in ("-s", "--speedup"):
      speedup = int(arg)
    elif opt in ("-f", "--file"):
      try: log = open(arg)
      except:
        print("Error: Can't open file '%s'" % arg)
        exit()
    elif opt in ("-v", "--verbose"):
      verbose = 1
    elif opt in ("-q", "--quiet"):
      verbose = 0
    elif opt in ("-d", "--debuff-finder"):
      debuff_finder = True
    elif opt in ("-b", "--boss-display"):
      boss_display = True
    elif opt in ("-z", "--no-config"):
      try:
        os.remove("AOChelper.cfg")
      except:
        pass
  
  # Start parser and output window
  parser = ParserThread(log)
  app    = wx.App(False)
  frame  = MainWindow("AOChelper v0.3", parser)
  parser.window = frame
  
  # Enable this to get a list of all (de)buffs applied. Manual labour to add players to the class is needed
  if debuff_finder:
    parser.parsers.append(DebuffFinder())
  if boss_display:
    parser.parsers.append(BossDisplay())
  # parser.parsers.append(CritDetector())
  
  frame.Show(True)
  parser.start()
  print("Hello 1")

  app.MainLoop()
  
  # We only reach here if window is closed
  parser.exit()

if __name__ == "__main__":
  main(sys.argv[1:])
