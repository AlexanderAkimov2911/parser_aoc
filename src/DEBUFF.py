
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

