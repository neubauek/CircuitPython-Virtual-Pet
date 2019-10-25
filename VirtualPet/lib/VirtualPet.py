# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
`VirtualPet.py`
====================================================

CircuitPython virtual pet class for virtual pet game
* Author(s): Kevin Neubauer
"""
class VirtualPet:
    agingRate = 0.0000025
    healthRate = 0.0005
    poopHealthMultiplier = 0.001

    sleepRate = {
		'hunger': 0.0001,
		'poop': 0.0001,
		'happiness': 0.00002,
		'discipline': 0.00002
	}

    awakeRate = {
		'hunger': 0.0005,
		'poop': 0.0005,
		'happiness': 0.0004,
		'discipline': 0.0004	
	}

    def __init__(self):
        self.hunger = 100
        self.happiness = 100
        self.health = 100
        self.discipline = 100
        self.poopLevel = 0
        self.weight = 1
        self.age = 0
        self.awake = True
        self.dead = False

    def decrementHunger(self):
    	if (self.awake):
    		self.hunger = self.hunger - self.awakeRate["hunger"]
    	else:
    		self.hunger = self.hunger - self.sleepRate["hunger"]

    def decrementHappiness(self):
 		if (self.awake):
 			self.happiness = self.happiness - self.awakeRate["happiness"]
		else:
			self.happiness = self.happiness - self.sleepRate["happiness"]

    def decrementDiscipline(self):
		if (self.awake):
			self.discipline = self.discipline - self.awakeRate["discipline"]
		else:
			self.discipline = self.discipline - self.sleepRate["discipline"]

    def incrementPoopLevel(self):
		if (self.awake):
			self.poopLevel = self.poopLevel + self.awakeRate["poop"]
		else:
			self.poopLevel = self.poopLevel + self.sleepRate["poop"]

    def incrementAge(self):
		self.age = self.age + self.agingRate

    def decrementHealth(self):
		self.health = self.health - self.healthRate + self.countPoops() * self.poopHealthMultiplier

    def countPoops(self):
		return int(self.poopLevel/10)

    def checkOverallHealth(self):
		if (self.hunger <= 0 or self.health <= 0 or self.happiness <= 0):
			self.dead = True

    def lifeTick(self):
    	self.decrementHunger()
    	self.decrementHappiness()
    	self.decrementDiscipline()
    	self.incrementPoopLevel()
    	self.incrementAge()
    	self.decrementHealth()
    	self.checkOverallHealth()