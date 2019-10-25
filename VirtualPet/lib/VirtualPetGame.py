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
`VirtualPetGame.py`
====================================================

CircuitPython virtual pet game for Kevin Neubauer's Circuit Python Badge _.
with SH1106 128x64 OLED screen.
* Author(s): Kevin Neubauer

Want to design your own pet?
Paint the screens using: https://www.pixilart.com
Use existing art for size reference.
After painted, encode them in 0/1 format using: https://www.dcode.fr/binary-image
"""
import VirtualPet.lib.VirtualPetFramebuf as VPB
import VirtualPet.lib.VirtualPet as VP
import time
import board
import digitalio
import audioio
import neopixel
import random
import array
import math
from adafruit_debouncer import Debouncer
try:
    import audiocore
except ImportError:
    audiocore = audioio

SCRWIDTH = 128;
SCRHEIGHT = 64;
WHITE = 1;
BLACK = 0;

HEALTHWARNING = 25
HEALTHDANGER = 10

PIX_NUM = 10
PIX_RED = (255, 0, 0)
PIX_YELLOW = (255, 150, 0)
PIX_GREEN = (0, 255, 0)
PIX_CYAN = (0, 255, 255)
PIX_BLUE = (0, 0, 255)
PIX_PURPLE = (180, 0, 255)
PIX_OFF = (0, 0, 0)

pixels = neopixel.NeoPixel(board.NEOPIXEL, PIX_NUM, brightness=0.05)

GAMEMENU = {}
GAMEMENU[1] = ["Feed/Water", "Snack", "Meal", "Water"]
GAMEMENU[2] = ["Play Game"]
GAMEMENU[3] = ["Sleep"]
GAMEMENU[4] = ["Clean"]
GAMEMENU[5] = ["Doctor"]
GAMEMENU[6] = ["Discipline"]
GAMEMENU[7] = ["Display Stats"]
GAMEMENU[8] = ["Sound"]
GAMEMENU[9] = ["Lights"]

class VirtualPetGame:
    def __init__(self):
        # Main frame buffer
        self.fb = VPB.VirtualPetFramebuf(SCRWIDTH, SCRHEIGHT)
        self.splash()
        self.fb.clearDisplay();

        self.speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
        self.speaker_enable.switch_to_output(value=False)

        # Initialize frequently used animation screens
        # Avoids reading them from file every time
        with open ("VirtualPet/assets/petWalkLeft1.txt", "r") as myfile:
            try:
                self.animateLeft1=myfile.readlines()
            finally:
                myfile.close()

        with open ("VirtualPet/assets/petWalkLeft2.txt", "r") as myfile:
            try:
                self.animateLeft2=myfile.readlines()
            finally:
                myfile.close()

        with open ("VirtualPet/assets/petWalkRight1.txt", "r") as myfile:
            try:
                self.animateRight1=myfile.readlines()
            finally:
                myfile.close()

        with open ("VirtualPet/assets/petWalkRight2.txt", "r") as myfile:
            try:
                self.animateRight2=myfile.readlines()
            finally:
                myfile.close()

        with open ("VirtualPet/assets/foreground.txt", "r") as myfile:
            try:
                self.foreground=myfile.readlines()
            finally:
                myfile.close()

        with open ("VirtualPet/assets/background.txt", "r") as myfile:
            try:
                self.background=myfile.readlines()
            finally:
                myfile.close()

        with open ("VirtualPet/assets/petEating1.txt", "r") as myfile:
            try:
                self.eating1=myfile.readlines()
            finally:
                myfile.close()

        with open ("VirtualPet/assets/petEating2.txt", "r") as myfile:
            try:
                self.eating2=myfile.readlines()
            finally:
                myfile.close()

        with open ("VirtualPet/assets/buttonDown.txt", "r") as myfile:
            try:
                self.buttonDown=myfile.readlines()
            finally:
                myfile.close()

        with open ("VirtualPet/assets/buttonUp.txt", "r") as myfile:
            try:
                self.buttonUp=myfile.readlines()
            finally:
                myfile.close()

        self.renderMainLandscape()

        self.soundEnabled = True #Flag for enabling/disabling sound
        self.lightsEnabled = True #Flag for enabling/disabling lights
        self.inMinigame = False #Flag for determining whether in minigame
        self.menuOpen = False #Flag for determining whether menu is open
        self.menuSelected = 0 #Variable for storing which menu item is selected
        self.subMenuSelected = 0 #Variable for storing which submenu item is selected
        self.actionSelected = "" #Variable for storing an action selected from menu
        self.maxAnimateLeftPos = 0 #Idle pet animation Left direction bounds
        self.maxAnimateRightPos = SCRWIDTH-27 #Idle pet animation Right direction bounds
        self.animateDirection = "Left" #Direction of idle animation sequence
        self.currentAnimatePos = SCRWIDTH-27 #Current position of animation sequence
        self.animateStep = 1 #What step are we on in the animate sequence
        self.pause = False #Variable to hold game rendering (display stats)
        self.pooChangeState = False #Variable to track poo change state

        self._sample = None
        self._sine_wave = None
        self._sine_wave_sample = None

        # Minigame variables
        self.minigame_game_sequence = []
        self.minigame_player_sequence = []
        self.minigame_cur_round = 1
        self.minigame_hiscore = 0

        # Init 3 buttons
        self.lButton = digitalio.DigitalInOut(board.LEFT_BUTTON)
        self.lButton.switch_to_input(pull=digitalio.Pull.DOWN)
        self.mButton = digitalio.DigitalInOut(board.MIDDLE_BUTTON)
        self.mButton.switch_to_input(pull=digitalio.Pull.DOWN)
        self.rButton = digitalio.DigitalInOut(board.RIGHT_BUTTON)
        self.rButton.switch_to_input(pull=digitalio.Pull.DOWN)

        self.pet = VP.VirtualPet() # Our pet! Yay!

        self.mainLoop() # Go to game loop

    # Main game loop
    def mainLoop(self):
        while (True):
            if (self.lightsEnabled):
                if (self.pet.happiness < HEALTHDANGER or self.pet.health < HEALTHDANGER or self.pet.hunger < HEALTHDANGER):
                    #health danger
                    pixels.fill(PIX_RED)
                elif (self.pet.happiness < HEALTHWARNING or self.pet.health < HEALTHWARNING or self.pet.hunger < HEALTHWARNING):
                    #health warning
                    pixels.fill(PIX_YELLOW)
                elif (self.pet.countPoops() >= 1):
                    pixels.fill(PIX_PURPLE)
                else:
                    pixels.fill(PIX_OFF)

            if (self.pet.dead):
                self.dead()
                pixels.fill(PIX_OFF)
            else:
                # Menu Action
                if self.lButton.value:
                    if (self.menuOpen == False):
                        # Main menu not already open
                        self.menuOpen = True
                        self.menuSelected = 1
                        self.subMenuSelected = 0
                        self.renderMenu(self.menuSelected, self.subMenuSelected)
                    elif (self.subMenuSelected > 0): #Submenu navigation
                        if (self.subMenuSelected == len(GAMEMENU[self.menuSelected])-1):
                            self.subMenuSelected = 1
                        else:
                            self.subMenuSelected = self.subMenuSelected + 1
                        self.renderMenu(self.menuSelected, self.subMenuSelected)
                    else:
                        # Main menu already open
                        if (self.menuSelected == len(GAMEMENU)): # End of the road, reset menu selected variable
                            self.menuSelected = 1
                        else:
                            self.menuSelected = self.menuSelected + 1
                        self.renderMenu(self.menuSelected, 0)

                # Select
                if self.mButton.value:
                    if (not self.menuSelected == 0):
                        if (len(GAMEMENU[self.menuSelected]) > 1):
                            # Menu has submenus
                            if (self.subMenuSelected == 0):
                                # First time visting submenu
                                self.subMenuSelected = 1
                                self.renderMenu(self.menuSelected, self.subMenuSelected)
                            else:
                                # Select submenu action
                                self.actionSelected = GAMEMENU[self.menuSelected][self.subMenuSelected]
                                self.resetMenu()
                                self.clearMenuArea()
                                self.renderMainLandscape()
                        else:
                            # Select menu action
                            self.actionSelected = GAMEMENU[self.menuSelected][self.subMenuSelected]
                            self.resetMenu()
                            self.clearMenuArea()
                            self.renderMainLandscape()

                # Cancel / Close
                if self.rButton.value:
                    self.resetMenu()
                    self.actionSelected = ""
                    self.clearMenuArea()
                    self.renderMainLandscape()

                # If our pet is not dead
                # Add one tick to its life
                self.pet.lifeTick()

                if (not self.actionSelected == ""):
                    #print ("do action: " + self.actionSelected)
                    switcher = {
                        "Snack":self.feedSnack,
                        "Meal":self.feedMeal,
                        "Water":self.waterPet,
                        "Play Game":self.playMinigame,
                        "Sleep":self.toggleSleep,
                        "Clean":self.clean,
                        "Doctor":self.doctor,
                        "Discipline":self.discipline,
                        "Display Stats":self.displayStats,
                        "Sound":self.toggleSound,
                        "Lights":self.toggleLights
                    }
                    func = switcher.get(self.actionSelected)
                    func()
                    self.actionSelected = "" #reset after doing action

                if (self.pet.awake and (not self.pet.dead)):
                    self.idleAnimate()

                if (self.animateDirection == "Left"):
                    self.currentAnimatePos = self.currentAnimatePos - 10
                    self.animateStep = self.animateStep + 1
                    if (self.currentAnimatePos < self.maxAnimateLeftPos):
                        self.animateDirection = "Right"
                        self.currentAnimatePos = 0
                        self.animateStep = 1
                else:
                    self.currentAnimatePos = self.currentAnimatePos + 10
                    self.animateStep = self.animateStep + 1
                    if (self.currentAnimatePos > self.maxAnimateRightPos):
                        self.animateDirection = "Left"
                        self.currentAnimatePos = SCRWIDTH-27
                        self.animateStep = 1

    def feedSnack(self):
        if (self.pet.awake):
            self.feedPet("Snack")

    def feedMeal(self):
        if (self.pet.awake):
            self.feedPet("Meal")

    def waterPet(self):
        if (self.pet.awake):
            self.feedPet("Water")

    def feedPet(self, strFoodType):
        if (self.disciplineCheck()):
            self.fb.clearDisplay()

            if (strFoodType == "Snack"):
                self.fb.setContentsFromFile("VirtualPet/assets/snack1.txt", 0, 0)
            elif (strFoodType == "Meal"):
                self.fb.setContentsFromFile("VirtualPet/assets/meal1.txt", 0, 0)
            else:
                self.fb.setContentsFromFile("VirtualPet/assets/water1.txt", 0, 0)
            self.fb.screenPrint()

            for i in range(0, 1):
                self.fb.setContentsFromList(self.eating1, 64, 0)
                self.fb.screenPrint()
                self.fb.setContentsFromList(self.eating2, 64, 0)
                self.fb.screenPrint()

            if (self.soundEnabled):
                self.playAudio("VirtualPet/assets/audio/feedPet.wav")

            if (strFoodType == "Snack"):
                self.fb.setContentsFromFile("VirtualPet/assets/snack2.txt", 0, 0)
            elif (strFoodType == "Meal"):
                self.fb.setContentsFromFile("VirtualPet/assets/meal2.txt", 0, 0)
            else:
                self.fb.setContentsFromFile("VirtualPet/assets/water2.txt", 0, 0)
            self.fb.screenPrint()

            for i in range(0, 1):
                self.fb.setContentsFromList(self.eating1, 64, 0)
                self.fb.screenPrint()
                self.fb.setContentsFromList(self.eating2, 64, 0)
                self.fb.screenPrint()

            if (strFoodType == "Snack"):
                self.fb.setContentsFromFile("VirtualPet/assets/snack3.txt", 0, 0)
            elif (strFoodType == "Meal"):
                self.fb.setContentsFromFile("VirtualPet/assets/meal3.txt", 0, 0)
            else:
                self.fb.setContentsFromFile("VirtualPet/assets/water3.txt", 0, 0)
            self.fb.screenPrint()

            for i in range(0, 1):
                self.fb.setContentsFromList(self.eating1, 64, 0)
                self.fb.screenPrint()
                self.fb.setContentsFromList(self.eating2, 64, 0)
                self.fb.screenPrint()

            if (strFoodType == "Snack"):
                self.fb.fill_rect(0, 0, 64, 64, BLACK)
                self.pet.health += 0.5
                self.pet.hunger += 10
                self.pet.poopLevel += 0.025
                self.pet.weight += 0.01
            elif (strFoodType == "Meal"):
                self.fb.fill_rect(0, 0, 64, 64, BLACK)
                self.pet.health -= 1
                self.pet.hunger += 20
                self.pet.poopLevel += 0.05
                self.pet.weight += 0.05
            else:
                self.fb.fill_rect(0, 0, 64, 64, BLACK)
                self.pet.hunger += 5
                self.pet.poopLevel += 0.01

            if (self.pet.hunger > 100):
                self.pet.hunger = 100

            self.fb.screenPrint()
        else:
            #Failed discipline check
            self.fb.setContentsFromFile("VirtualPet/assets/faildiscipline.txt", self.currentAnimatePos, 0)
            self.fb.screenPrint()
            if (self.soundEnabled):
                self.playAudio("VirtualPet/assets/audio/faildiscipline.wav")

        self.fb.clearDisplay()
        self.renderMainLandscape()
        self.resetMenu()

    def playAudio(self, file_name):
        self.speaker_enable.value = True
        with audioio.AudioOut(board.SPEAKER) as audio:
            wavefile = audiocore.WaveFile(open(file_name, "rb"))
            audio.play(wavefile)
            while audio.playing:
                pass
        self.speaker_enable.value = False

    def disciplineCheck(self):
        """
        Weighted random chance check based on pet's discipline level.
        The higher the level of pet discipline, the greater chance of returning True value.
        """
        a = [(1-(self.pet.discipline/100)), (self.pet.discipline/100)]
        r = random.random()
        p = 0
        for i, v in enumerate(a):
            p += v
            if r < p:
               return i
        # p may not equal exactly 1.0 due to floating-point rounding errors
        # so if we get here, just try again (the errors are small, so this
        # should not happen very often).  You could also just put it in the
        # last bin or pick a bin at random, depending on your tolerance for
        # small biases
        return disciplineCheck()

    def playMinigame(self):
        """
        Code adapted from: https://medium.com/@IranNeto/building-simon-genius-game-on-the-beaglebone-with-python-d371c2bacbed
        """
        self.inMinigame = True
        self.fb.clearDisplay()

        while (self.inMinigame):
            self.minigame_gen_cur_round()
            self.minigame_get_player_input()

            # DEBUG
            #print (self.minigame_game_sequence)
            #print (self.minigame_player_sequence)

            if (not self.minigame_validate_input()):
                self.fb.clearDisplay()
                self.fb.setContentsFromFile("VirtualPet/assets/minigameFail.txt", 0, 0)
                self.fb.screenPrint()
                if (self.lightsEnabled):
                    pixels.fill(PIX_RED)
                    time.sleep(0.25)
                    pixels.fill(PIX_OFF)
                if (self.soundEnabled):
                    self.play_tone(100, 1)
            else:
                if (self.lightsEnabled):
                    pixels.fill(PIX_GREEN)
                    time.sleep(0.25)
                    pixels.fill(PIX_OFF)
                self.minigame_cur_round += 1

        if (self.minigame_hiscore < self.minigame_cur_round):
            self.minigame_hiscore = self.minigame_cur_round

        self.minigame_game_sequence = []
        self.minigame_player_sequence = []
        self.minigame_cur_round = 1
        self.resetMenu()
        self.fb.clearDisplay()
        self.renderMainLandscape()
        self.pet.happiness += 15
        if (self.pet.happiness < 100):
            self.pet.happiness = 100

    def minigame_gen_cur_round(self):
        posX = {}
        posY = {}
        tone = {}
        posX[0] = 0
        posX[1] = 50
        posX[2] = 100
        posY[0] = 30
        posY[1] = 30
        posY[2] = 30
        tone[0] = 350
        tone[1] = 400
        tone[2] = 440

        self.fb.clearDisplay()
        self.fb.text("Hi Score: " + str(self.minigame_hiscore), 0, 0, WHITE)
        self.fb.text("Round: " + str(self.minigame_cur_round), 0, 8, WHITE)
        self.fb.setContentsFromList(self.buttonUp, posX[0], posY[0]+20)
        self.fb.setContentsFromList(self.buttonUp, posX[1], posY[1]+20)
        self.fb.setContentsFromList(self.buttonUp, posX[2], posY[2]+20)
        self.fb.screenPrint()
        seq = random.randint(0,2)
        self.minigame_game_sequence.append(seq)
        for count in range(0, self.minigame_cur_round):
            curSeq = self.minigame_game_sequence[count]
            self.fb.setContentsFromList(self.animateLeft1, posX[curSeq], posY[curSeq])
            self.fb.setContentsFromList(self.buttonDown, posX[curSeq], posY[curSeq]+20)
            self.fb.screenPrint()
            if (self.soundEnabled):
                self.play_tone(tone[curSeq], 0.25)
            time.sleep(0.5)
            self.fb.setContentsFromList(self.buttonUp, posX[curSeq], posY[curSeq]+20)
            self.fb.fill_rect(posX[curSeq], posY[curSeq], 26, 20, BLACK)
            self.fb.screenPrint()

    def minigame_get_player_input(self):
        # Debounced buttons work better in minigame
        lButtonDB = Debouncer(self.lButton)
        mButtonDB = Debouncer(self.mButton)
        rButtonDB = Debouncer(self.rButton)

        if (self.minigame_cur_round > 1):
            del self.minigame_player_sequence[:]

        number_of_plays = 0
        play_begin_time = time.time()
        play_end_time = time.time()

        #Give 3 seconds for every item in the sequence for the current round
        while ((play_end_time - play_begin_time) < self.minigame_cur_round + 3):
            lButtonDB.update()
            mButtonDB.update()
            rButtonDB.update()

            if (lButtonDB.fell):
                self.minigame_player_sequence.append(0)
                number_of_plays += 1
                if (self.soundEnabled):
                    self.play_tone(350, 0.25)
                time.sleep(0.25)

            if (mButtonDB.fell):
                self.minigame_player_sequence.append(1)
                number_of_plays += 1
                if (self.soundEnabled):
                    self.play_tone(400, 0.25)
                time.sleep(0.25)

            if (rButtonDB.fell):
                self.minigame_player_sequence.append(2)
                number_of_plays += 1
                if (self.soundEnabled):
                    self.play_tone(450, 0.25)
                time.sleep(0.25)

            play_end_time = time.time()

            if (number_of_plays == self.minigame_cur_round):
                break

            if (number_of_plays < self.minigame_cur_round):
                pass

    def minigame_validate_input(self):
        if (len(self.minigame_game_sequence) != len(self.minigame_player_sequence)):
            self.inMinigame = False
            return False
        for i in range(0, self.minigame_cur_round):
            if (self.minigame_player_sequence[i] != self.minigame_game_sequence[i]):
                self.inMinigame = False
                return False

        return True

    def toggleSleep(self):
        if (self.pet.awake):
            self.clearPetArea()
            self.fb.setContentsFromFile("VirtualPet/assets/sleeping.txt", self.currentAnimatePos, 30)
            self.pet.awake = False
            self.fb.screenPrint()
            self.resetMenu()
            if (self.soundEnabled):
                self.playAudio("VirtualPet/assets/audio/sleep.wav")
        else:
            self.pet.awake = True
            self.resetMenu()

    def dead(self):
        self.clearPetArea()
        self.fb.setContentsFromFile("VirtualPet/assets/dead.txt", self.currentAnimatePos, 30)
        self.fb.fill_rect(0, 0, SCRWIDTH-1, 29, BLACK)
        self.fb.rect(0, 0, SCRWIDTH-1, 29, WHITE)
        self.fb.rect(0, 0, SCRWIDTH-1, 12, WHITE)
        self.fb.text("GAME OVER", 8, 2, WHITE)
        self.fb.text("Press Reset", 8, 16, WHITE)
        self.fb.screenPrint()
        if (self.soundEnabled):
            self.playAudio("VirtualPet/assets/audio/die.wav")

            #Disable sound else it will loop forever until reset
            self.soundEnabled = False

    def clean(self):
        if (self.pet.awake):
            self.pet.poopLevel = 0
            self.pooChangeState = False
            self.fb.setContentsFromFile("VirtualPet/assets/clean1.txt", 0, 0)
            self.fb.screenPrint()
            if (self.soundEnabled):
                self.playAudio("VirtualPet/assets/audio/clean.wav")
            self.fb.setContentsFromFile("VirtualPet/assets/clean2.txt", 0, 0)
            self.fb.screenPrint()
            self.fb.setContentsFromFile("VirtualPet/assets/clean3.txt", 0, 0)
            self.fb.screenPrint()
            self.resetMenu()
            self.fb.clearDisplay()
            self.renderMainLandscape()

    def doctor(self):
        if (self.pet.awake):
            if (self.pet.health < 60):
                self.pet.health = 100
                self.fb.setContentsFromFile("VirtualPet/assets/doctor1.txt", 0, 0)
                self.fb.screenPrint()
                self.fb.setContentsFromFile("VirtualPet/assets/doctor2.txt", 0, 0)
                self.fb.screenPrint()
                if (self.soundEnabled):
                    self.playAudio("VirtualPet/assets/audio/doctor.wav")
                self.fb.setContentsFromFile("VirtualPet/assets/doctor3.txt", 0, 0)
                self.fb.screenPrint()
                time.sleep(0.5)
            else:
                self.fb.fill_rect(10, 20, 115, 10, WHITE)
                self.fb.text("Pet is healthy", 11, 21, BLACK)
                self.fb.screenPrint()
                time.sleep(3)

            self.resetMenu()
            self.fb.clearDisplay()
            self.renderMainLandscape()

    def discipline(self):
        if (self.pet.awake):
            self.pet.discipline += 12
            if (self.pet.discipline > 100):
                self.pet.discipline = 100
            if ((self.pet.happiness - 3) > 0):
                self.pet.happiness -= 3
            self.fb.setContentsFromFile("VirtualPet/assets/discipline1.txt", 0, 0)
            self.fb.screenPrint()
            self.fb.setContentsFromFile("VirtualPet/assets/discipline2.txt", 0, 0)
            self.fb.screenPrint()
            self.fb.setContentsFromFile("VirtualPet/assets/discipline1.txt", 0, 0)
            self.fb.screenPrint()
            self.fb.setContentsFromFile("VirtualPet/assets/discipline2.txt", 0, 0)
            self.fb.screenPrint()
            if (self.soundEnabled):
                self.playAudio("VirtualPet/assets/audio/discipline.wav")
            self.resetMenu()
            self.fb.clearDisplay()
            self.renderMainLandscape()

    def displayStats(self):
        lAlign = 0
        self.pause = True

        while (self.pause):
            self.fb.clearDisplay()
            #Page 1
            self.fb.text("Pet Stats", lAlign, 2, WHITE)
            self.fb.text("%.2f Hunger" % self.pet.hunger, lAlign, 14, WHITE)
            self.fb.text("%.2f Happiness" % self.pet.happiness, lAlign, 26, WHITE)
            self.fb.text("%.2f Health" % self.pet.health, lAlign, 38, WHITE)
            self.fb.text("%.2f Discipline" %self.pet.discipline, lAlign, 50, WHITE)
            self.fb.screenPrint()

            if (self.lButton.value or self.mButton.value or self.rButton.value):
                self.pause = False

        self.pause = True

        while (self.pause):
            self.fb.clearDisplay()
            #Page 2
            self.fb.text("Pet Stats", lAlign, 2, WHITE)
            self.fb.text("%.2f Poopiness" % self.pet.poopLevel, lAlign, 14, WHITE)
            self.fb.text("%.2f Weight" % self.pet.weight, lAlign, 26, WHITE)
            self.fb.text("%.2f Age" % self.pet.age, lAlign, 38, WHITE)
            self.fb.screenPrint()

            if (self.lButton.value or self.mButton.value or self.rButton.value):
                self.pause = False

        self.fb.clearDisplay()
        self.resetMenu()
        self.renderMainLandscape()

    def toggleSound(self):
        self.soundEnabled = not self.soundEnabled
        self.resetMenu()

    def toggleLights(self):
        if (self.lightsEnabled):
            self.lightsEnabled = False
            pixels.fill(PIX_OFF)
        else:
            self.lightsEnabled = True
        self.resetMenu()

    def renderMainLandscape(self):
        self.fb.setContentsFromList(self.background, 0, 0)
        self.fb.setContentsFromList(self.foreground, 0, 50)
        self.fb.screenPrint()

    def idleAnimate(self):
        self.clearPetArea()
        if (self.animateStep % 2 == 0): #Even step
            if (self.animateDirection == "Left"):
                self.fb.setContentsFromList(self.animateLeft2, self.currentAnimatePos, 30)
            else:
                self.fb.setContentsFromList(self.animateRight2, self.currentAnimatePos, 30)
            self.fb.screenPrint()
        else: #Odd step
            if (self.animateDirection == "Left"):
                self.fb.setContentsFromList(self.animateLeft1, self.currentAnimatePos, 30)
            else:
                self.fb.setContentsFromList(self.animateRight1, self.currentAnimatePos, 30)
            self.fb.screenPrint()

        if (not self.menuOpen):
            poopCount = self.pet.countPoops()
            if (poopCount > 3):
                poopCount = 3
            if (poopCount >= 1):
                if (self.pooChangeState == False):
                    self.pooChangeState = True
                    if (self.soundEnabled):
                        self.playAudio("VirtualPet/assets/audio/poo.wav")

                xPos = 0
                for i in range(0, poopCount):
                    self.fb.setContentsFromFile("VirtualPet/assets/poo.txt", xPos, 0)
                    xPos += 40

    # Clear out the pet idle animation area
    def clearPetArea(self):
        self.fb.fill_rect(0, 30, SCRWIDTH-1, 20, BLACK)

    # Reset menu variables to default state
    def resetMenu(self):
        self.menuOpen = False
        self.menuSelected = 1
        self.subMenuSelected = 0

    # Splash screen for start of game
    def splash(self):
        self.fb.setContentsFromFile("VirtualPet/splash.txt", 0, 0)
        self.fb.text("Kevin Neubauer", 0, 40, WHITE)
        self.fb.text("@kevinneubauer", 0, 48, WHITE)
        self.fb.text("bit.ly/2BMEg3O", 0, 56, WHITE)
        self.fb.screenPrint()
        time.sleep(4)

    def clearMenuArea(self):
        self.fb.fill_rect(0, 0, SCRWIDTH-1, 29, BLACK)

    def renderMenu(self, menuPos, subMenuPos):
        self.clearMenuArea()

        self.fb.rect(0, 0, SCRWIDTH-1, 29, WHITE)
        self.fb.rect(0, 0, SCRWIDTH-1, 12, WHITE)
        if (subMenuPos > 0): #sub menu
            self.fb.fill_rect(0, 0, SCRWIDTH-1, 12, WHITE)
            self.fb.fill_rect(1, 18, 1, 5, WHITE)
            self.fb.fill_rect(2, 19, 1, 3, WHITE)
            self.fb.fill_rect(3, 20, 1, 1, WHITE)
            self.fb.text(GAMEMENU[menuPos][0], 8, 2, BLACK)
            self.fb.text(GAMEMENU[menuPos][subMenuPos], 8, 16, WHITE)
        else: #top level menu
            if (GAMEMENU[menuPos][0] == "Sleep"):
                self.fb.fill_rect(1, 18, 1, 5, WHITE)
                self.fb.fill_rect(2, 19, 1, 3, WHITE)
                self.fb.fill_rect(3, 20, 1, 1, WHITE)
                self.fb.fill_rect(0, 0, SCRWIDTH-1, 12, WHITE)
                self.fb.text(GAMEMENU[menuPos][0], 8, 2, BLACK)
                self.fb.text(("Disable", "Enable")[self.pet.awake], 8, 16, WHITE)
            elif (GAMEMENU[menuPos][0] == "Sound"):
                self.fb.fill_rect(1, 18, 1, 5, WHITE)
                self.fb.fill_rect(2, 19, 1, 3, WHITE)
                self.fb.fill_rect(3, 20, 1, 1, WHITE)
                self.fb.fill_rect(0, 0, SCRWIDTH-1, 12, WHITE)
                self.fb.text(GAMEMENU[menuPos][0], 8, 2, BLACK)
                self.fb.text(("Enable", "Disable")[self.soundEnabled], 8, 16, WHITE)
            elif (GAMEMENU[menuPos][0] == "Lights"):
                self.fb.fill_rect(1, 18, 1, 5, WHITE)
                self.fb.fill_rect(2, 19, 1, 3, WHITE)
                self.fb.fill_rect(3, 20, 1, 1, WHITE)
                self.fb.fill_rect(0, 0, SCRWIDTH-1, 12, WHITE)
                self.fb.text(GAMEMENU[menuPos][0], 8, 2, BLACK)
                self.fb.text(("Enable", "Disable")[self.lightsEnabled], 8, 16, WHITE)
            else:
                self.fb.fill_rect(1, 3, 1, 5, WHITE)
                self.fb.fill_rect(2, 4, 1, 3, WHITE)
                self.fb.fill_rect(3, 5, 1, 1, WHITE)
                self.fb.text(GAMEMENU[menuPos][0], 8, 2, WHITE)

        self.fb.screenPrint()

    def _sine_sample(self, length):
        tone_volume = (2 ** 15) - 1
        shift = 2 ** 15
        for i in range(length):
            yield int(tone_volume * math.sin(2*math.pi*(i / length)) + shift)

    def _generate_sample(self, length=100):
        if self._sample is not None:
            return
        self._sine_wave = array.array("H", self._sine_sample(length))
        self._sample = audioio.AudioOut(board.SPEAKER)
        self._sine_wave_sample = audiocore.RawSample(self._sine_wave)

    def play_tone(self, frequency, duration):
        """ Produce a tone using the speaker. Try changing frequency to change
        the pitch of the tone.

        :param int frequency: The frequency of the tone in Hz
        :param float duration: The duration of the tone in seconds
        """
        # Play a tone of the specified frequency (hz).
        self.start_tone(frequency)
        time.sleep(duration)
        self.stop_tone()

    def start_tone(self, frequency):
        """ Produce a tone using the speaker. Try changing frequency to change
        the pitch of the tone.

        :param int frequency: The frequency of the tone in Hz
        """
        self.speaker_enable.value = True
        length = 100
        if length * frequency > 8000:
            length = 8000 // frequency
        self._generate_sample(length)
        # Start playing a tone of the specified frequency (hz).
        self._sine_wave_sample.sample_rate = int(len(self._sine_wave) * frequency)
        if not self._sample.playing:
            self._sample.play(self._sine_wave_sample, loop=True)

    def stop_tone(self):
        """ Use with start_tone to stop the tone produced.
        """
        # Stop playing any tones.
        if self._sample is not None and self._sample.playing:
            self._sample.stop()
            self._sample.deinit()
            self._sample = None
        self.speaker_enable.value = False