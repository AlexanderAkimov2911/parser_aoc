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
