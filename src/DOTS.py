
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
