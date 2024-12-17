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
              print("Start logging:\n  /logcombat on\n_________________")
            else:
              self.window.setText("Start logging:\n  /logcombat on\n#grey#Rclick = Settings")
              print("Start logging:\n  /logcombat on\nRclick = Settings")
            sleep(5)
            continue
          else:
            self.window.setText("Logfile found:\n%s" % self.log.name.split("/")[-1])
            print("Logfile found:\n%s" % self.log.name.split("/")[-1])
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
  def parse(self, x):
    (attacker, action, ability, target, amount, type, crit) = x
    raise
  def poll(self):
    # True means that parser is done, and can be removed
    return (self.finished and elapsed() - self.finished > 10)


# This class presents your own dps
class DPS(LogParser):
  short_text = "DPS meter"
  
  def __init__(self, parent):
    LogParser.__init__(self)
    #ParserWindow.__init__(self, parent)
    self.total = [] 
    self.encounter = []
    self.current = []
    self.current_damage = 0
    self.last_action = 0 # number of poll()'s since we last dealt damage
  
  def parse(self, x):
    (attacker, action, ability, target, amount, type, crit) = x
    if action == "damage" and attacker in ("You","you"):
      self.current_damage += amount
      
  def updateWindow(self):
    if self.total:
      print("Enc:%6u Real Time:%6u" % (average(self.encounter), average(self.current)))


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
    
    self.updateWindow()
    self.current_damage = 0
    return False


parsers = {
  #enum.RAID : RAID,
  enum.DPS : DPS,
  #enum.DS  : DS,
  #enum.DEBUFF  : DEBUFF,
  #enum.DOTS  : DOTS,
}

# This is the main window for the application.
# It has many sub-windows of type ParserWindow which has the actual logic for the boss-fights
class MainWindow():
  default_settings = {
    "window_position" : (0,0),
    "always_on_top" :   True,
    "minimal_ui" :      False,
    "save_settings" :   False,
    "font_adjustment" : 1,
    "parsers" :         [enum.DPS,],
  }

  def __init__(self, title, parser):
    self.settings = self.default_settings
                        
    #   # Temporary hack to merge all raid parsers to one for those with stored settings that include the old, individual parsers
    #   for x in (enum.TOE, enum.JC):
    #     if x in self.settings["parsers"]:
    #       if enum.RAID in self.settings["parsers"]:
    #         self.settings["parsers"].remove(x)
    #       else:
    #         self.settings["parsers"][self.settings["parsers"].index(x)] = enum.RAID
      
    self.parser = parser
    #self.font = (23,45)
    self.windows = {}
    
    #wx.Frame.__init__(self, None, title=title, pos=self.settings["window_position"], style=wx.FRAME_NO_TASKBAR) # Border and stuff is set in FixVisualLook, called later in constructor
    
    # List of available parsers
    #for id,class_name in parsers.items():
      # Create a menu item for the parser, so we can enable/disable it
      #menu_item = self.menu.AppendCheckItem(id, class_name.short_text)
      #menu_item.Check(id in self.settings["parsers"])
      #self.Bind(wx.EVT_MENU, self.SettingsChanged, menu_item)
    
    # Add the default parsers
    for id in self.settings["parsers"]:
      self.AddParser(id)
    
  def AddParser(self, class_id):
    # Create a window for the parser
    p = parsers[class_id](self)
    self.windows[class_id] = p
    
    # Hand the ParserWindow to the ParserThread
    self.parser.parsers.append(p)
  
  # Sometimes the parser thread prints stuff; we use the biggest visible window to show that
  def setText(self, text, scroll=False):
    window = None

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
  verbose = 1
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
  frame  = MainWindow("AOChelper v0.3", parser)
  parser.window = frame
  
  # Enable this to get a list of all (de)buffs applied. Manual labour to add players to the class is needed
  if debuff_finder:
    parser.parsers.append(DebuffFinder())
  if boss_display:
    parser.parsers.append(BossDisplay())
  # parser.parsers.append(CritDetector())
  
  parser.start()


if __name__ == "__main__":
  main(sys.argv)
