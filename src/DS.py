
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
    