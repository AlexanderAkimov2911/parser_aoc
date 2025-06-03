import sys, os, threading, getopt, re, pickle, platform
import time as real_time
import datetime
#from textual.app import App, ComposeResult
#from textual.widgets import Button, Footer, Header

speedup = 1
elapsed_rewind = 0


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

  log_status = None
  log_file = None

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
    if platform.system() == "Windows":
      logs = [(os.path.getmtime(x), x) for x in ["%s\%s" % (self.logdir, y) for y in os.listdir(self.logdir) if y[0:10] == "CombatLog-"]]
    elif platform.system() == "Linux":
      logs = [(os.path.getmtime(x), x) for x in ["%s/%s" % (self.logdir, y) for y in os.listdir(self.logdir) if y[0:10] == "CombatLog-"]]
    else:
      print(f"Unsupported OS")
      exit()

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
            ParserThread.log_status = 0
            MainWindow.PrintText()
            #self.window.Close(True)
            exit()
          elif self.log == None:
            ParserThread.log_status = 1
            MainWindow.PrintText()
            sleep(5)
            continue
          else:
            ParserThread.log_status = 2
            ParserThread.log_file = self.log.name
            MainWindow.PrintText()
        except:
          if verbose:
            raise
          try:
            #self.window.Close(True)
            print(f"Playback {self.log}")
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
            #MainWindow.PrintText("Done!")
            print(f"Done!")
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
                #MainWindow.PrintText("New log:\n%s" % self.log.name.split("/")[-1])
                print(f"New log:\n {self.log.name}")
            
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
      
      
      #MainWindow.PrintText("[00:00:00] %s" % line)
      print(f"[00:00:00] {line}")
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

  # Real time combat monitor
  dps_real_time = None
  dps_encounter = None
  dps_targets = set()
  dps_encounter_time = None

  # Necromancer dots monitor
  dots_text = None
  player_is_necro = 0


  def __init__(self, parent):
    LogParser.__init__(self)

    # Real time combat monitor
    self.total = [] 
    self.encounter = []
    self.current = []
    self.current_damage = 0
    self.last_action = 0 # number of poll()'s since we last dealt damage
    self.encounter_active = 0
    self.stopwatch_active = 0
    self.start = real_time.time()

    self.TIMEOUT_PB   = 15.5
    self.TIMEOUT_FTW  = 24.5
    self.TIMEOUT_MOTD = 30.5

    # Necromancer dots monitor
    self.pb   = elapsed() - self.TIMEOUT_PB
    self.ftw  = elapsed() - self.TIMEOUT_FTW
    self.motd = elapsed() - self.TIMEOUT_MOTD
    
    # The durations can be increased with AA
    self.time_pb   = self.TIMEOUT_PB
    self.time_ftw  = self.TIMEOUT_FTW
    self.time_motd = self.TIMEOUT_MOTD
    


  def parse(self, x):
    (attacker, action, ability, target, amount, type, crit) = x
    # Real time combat monitor
    if action == "damage" and attacker in ("You","you"):
      self.current_damage += amount
      DPS.dps_targets.add(target)
 
    # Necromancer dots monitor
    if attacker == "You" and action == "buff" and ability:
      if   ability[0:18] == "Pestilential Blast":   
        self.pb   = elapsed()
        DPS.player_is_necro = 1
      elif ability[0:14] == "Flesh to Worms":       
        self.ftw  = elapsed()
        DPS.player_is_necro = 1
      elif ability[0:20] == "Mark of the Devourer": 
        self.motd = elapsed()
        DPS.player_is_necro = 1



      
  def updateWindow(self):
    if self.total:
      DPS.dps_encounter = int(average(self.encounter))
      DPS.dps_real_time = int(average(self.current))

    if self.player_is_necro == 1:
      # Necromancer dots monitor
      text = " "
    
      # Pestilential blast
      duration = self.time_pb - (elapsed() - self.pb)
      if duration < 0:    text += "PB: 0"
      else:               text += "PB: %2u" % duration
    
      text += "   "
      # Flesh to Worms
      duration = self.time_ftw - (elapsed() - self.ftw)
      if duration < 0:    text += "Worms: 0"
      else:               text += "Worms: %2u" % duration
    
      text += "  "
      # Mark of the Devourer
      duration = self.time_motd - (elapsed() - self.motd)
      if duration < 0:    text += "Mark: 0"
      else:               text += "Mark: %2u" % duration

      DPS.dots_text = text

    MainWindow.PrintText()

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
      self.encounter_active = 1
      self.total.append(self.current_damage)
      self.encounter.append(self.current_damage)
    
    self.current = [self.current_damage] + self.current[:4]
    
    if self.last_action > 30:
      self.encounter_active = 0


    # encounter stopwatch 
    if self.encounter_active == 1 and self.stopwatch_active == 0:
      self.start = real_time.time()
      self.stopwatch_active = 1
    elif self.encounter_active == 1 and self.stopwatch_active == 1:
      self.total_secs = round(real_time.time() - self.start)
      self.convert = str(datetime.timedelta(seconds = self.total_secs))
      DPS.dps_encounter_time = self.convert
    elif self.encounter_active == 0 and self.stopwatch_active == 1:
      self.stopwatch_active = 0

    self.updateWindow()
    self.current_damage = 0
    return False



# This is the main window for the application.
# It has many sub-windows of type ParserWindow which has the actual logic for the boss-fights
class MainWindow():

  def PrintText():
    if ParserThread.log_status == 0: # Stage of opening the game folder
      print(f"No combatlogs found!\nPlease run this program either from your AOC-folder or a folder parallell to that")
    elif ParserThread.log_status == 1: # Stage of find actual CombatLog
      print(f"\033[H\033[J")
      print(f"Game folder found. \nStart logging:\n/logcombat on")
    elif ParserThread.log_status == 2: # Stage of battle
      print("\033[H\033[J")
      print("   Age of Conan combat monitor")
      #print(f"Logfile found: {ParserThread.log_file}") 
      print(f"   Encounter DPS:{DPS.dps_encounter} \n   Real Time DPS:{DPS.dps_real_time}")
      print(f"   Ecounter time: {DPS.dps_encounter_time}")
      print(f"   Targets in battle: {DPS.dps_targets}")
      if DPS.player_is_necro == 1:
        print(f"   Necromancer DOTS timeout:\n  {DPS.dots_text}")

   


def main():
  global speedup, start_time, verbose
  verbose = 1
  speedup = 1
  start_time = real_time.time()
  log = None

  parser = ParserThread(log)
  parser.parsers.append(DPS(4))
  parser.start()




if __name__ == "__main__":
  main()
