
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
 