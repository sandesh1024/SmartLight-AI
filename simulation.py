# SmartLight AI - Traffic Simulation (Fixed)
# Bugs Fixed:
# 1. repeat() called inside initialize() thread - causes double threading (moved to Main)
# 2. preEmergencyGreen/preEmergencyYellow missing global declaration in checkEmergency()
# 3. emergencyCountdown decremented in BOTH checkEmergency() AND repeat() - fixed: only in repeat()
# 4. setTime() calls detect_vehicles() again (already called in checkEmergency()) - removed duplicate
# 5. signals[1].red set to wrong value (signals[0].red + ts1...) causes wrong red time
# 6. signals[3].red same wrong value as signals[0].red - fixed
# 7. simulationTime() calls os._exit(1) without pygame.quit() - fixed
# 8. vehicle.move() called in both repeat() thread AND pygame loop - race condition fixed (only in pygame loop)
# 9. repeat() uses time.sleep(1) in main logic but is called from initialize() which is itself a thread
# 10. generateVehicles() started twice - once in Main.__init__ and once would be in initialize thread

import random
import time
import threading
import pygame
import sys
import os

# ── DEFAULT VALUES ───────────────────────────────────────────────────
defaultRed     = 60
defaultYellow  = 3
defaultGreen   = 5
defaultMinimum = 3
defaultMaximum = 10

signals        = []
noOfSignals    = 4
simTime        = 300
timeElapsed    = 0

currentGreen   = 0
nextGreen      = 1
currentYellow  = 0

speeds = {'car':2.5,'bus':2.0,'truck':1.8,'rickshaw':2.2,'bike':3.0,'ambulance':3.5}

x = {'right':[0,0,0],'down':[755,727,697],'left':[1400,1400,1400],'up':[602,627,657]}
y = {'right':[348,370,398],'down':[0,0,0],'left':[498,466,436],'up':[800,800,800]}

vehicles = {
    'right':{0:[],1:[],2:[],'crossed':0},
    'down': {0:[],1:[],2:[],'crossed':0},
    'left': {0:[],1:[],2:[],'crossed':0},
    'up':   {0:[],1:[],2:[],'crossed':0}
}
vehicleTypes     = {0:'car',1:'bus',2:'truck',3:'rickshaw',4:'bike',5:'ambulance'}
directionNumbers = {0:'right',1:'down',2:'left',3:'up'}

signalCoods       = [(530,230),(810,230),(810,570),(530,570)]
signalTimerCoods  = [(530,210),(810,210),(810,550),(530,550)]
vehicleCountCoods = [(480,210),(880,210),(880,550),(480,550)]

stopLines   = {'right':590,'down':330,'left':800,'up':535}
defaultStop = {'right':580,'down':320,'left':810,'up':545}
stops       = {'right':[580,580,580],'down':[320,320,320],'left':[810,810,810],'up':[545,545,545]}

mid = {
    'right':{'x':705,'y':445},'down':{'x':695,'y':450},
    'left':{'x':695,'y':425},'up':{'x':695,'y':400}
}
rotationAngle = 3
gap  = 15
gap2 = 10

# ── EMERGENCY STATE ──────────────────────────────────────────────────
emergencyDetected    = False
emergencyDirection   = None
emergencyCountdown   = 0
emergencyGreenTime   = 5
lastEmergencyTime    = 0
emergencyInterval    = 35
immediateSwitch      = False
emergencyActive      = False
emergencyYellowPhase = False
emergencyYellowTime  = 3
preEmergencyGreen    = 0   # ✅ FIX: declared at module level so global works in functions
preEmergencyYellow   = 0
detectionTime        = 2

pygame.init()
simulation = pygame.sprite.Group()


# ── TRAFFIC SIGNAL CLASS ─────────────────────────────────────────────
class TrafficSignal:
    def __init__(self, red, yellow, green):
        self.red           = red
        self.yellow        = yellow
        self.green         = green
        self.minimum       = defaultMinimum
        self.maximum       = defaultMaximum
        self.signalText    = "---"
        self.totalGreenTime= 0
        self.originalGreen = green


# ── VEHICLE DETECTOR ─────────────────────────────────────────────────
class VehicleDetector:
    def __init__(self):
        self.detection_results  = {'right':0,'down':0,'left':0,'up':0}
        self.emergency_vehicles = {'right':False,'down':False,'left':False,'up':False}

    def detect_vehicles(self):
        """Count stopped vehicles per direction. Sets emergency flag if ambulance stopped in LEFT."""
        global emergencyDetected, emergencyDirection, emergencyCountdown, immediateSwitch

        self.detection_results  = {'right':0,'down':0,'left':0,'up':0}
        self.emergency_vehicles = {'right':False,'down':False,'left':False,'up':False}

        for direction in ['right','down','left','up']:
            total = 0
            for lane in [0,1,2]:
                for v in vehicles[direction][lane]:
                    if v.crossed == 0:
                        stopped = False
                        if direction=='right' and (abs(v.x-v.stop)<5 or v.x>=v.stop):
                            stopped = True
                        elif direction=='down' and (abs(v.y-v.stop)<5 or v.y>=v.stop):
                            stopped = True
                        elif direction=='left' and (abs(v.x-v.stop)<5 or v.x<=v.stop):
                            stopped = True
                        elif direction=='up' and (abs(v.y-v.stop)<5 or v.y<=v.stop):
                            stopped = True
                        if stopped:
                            total += 1
                            if direction == 'left' and v.vehicleClass == 'ambulance':
                                self.emergency_vehicles['left'] = True
            self.detection_results[direction] = total

        # ✅ FIX: Emergency detection ONLY here, not also in checkEmergency
        if (self.emergency_vehicles['left'] and not emergencyDetected
                and not emergencyActive and not emergencyYellowPhase):
            emergencyDetected  = True
            emergencyDirection = 'left'
            emergencyCountdown = 3
            immediateSwitch    = True
            print("🚑 EMERGENCY: Ambulance stopped at LEFT signal!")

        print(f"Stopped → R:{self.detection_results['right']} D:{self.detection_results['down']} L:{self.detection_results['left']} U:{self.detection_results['up']}")
        return self.detection_results

vehicle_detector = VehicleDetector()


# ── VEHICLE CLASS ────────────────────────────────────────────────────
class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite.__init__(self)
        self.lane             = lane
        self.vehicleClass     = vehicleClass
        self.speed            = speeds[vehicleClass]
        self.direction_number = direction_number
        self.direction        = direction
        self.x                = x[direction][lane]
        self.y                = y[direction][lane]
        self.crossed          = 0
        self.willTurn         = will_turn
        self.turned           = 0
        self.rotateAngle      = 0
        self.has_stopped      = False
        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1

        try:
            self.originalImage = pygame.image.load(f"images/{direction}/{vehicleClass}.png")
        except:
            w = 50 if vehicleClass in ('bus','truck') else 30 if vehicleClass=='bike' else 40
            h = 25 if vehicleClass in ('bus','truck') else 15 if vehicleClass=='bike' else 20
            self.originalImage = pygame.Surface((w,h))
            colors = {'car':(220,50,50),'bus':(50,50,220),'truck':(50,180,50),
                      'rickshaw':(220,220,50),'bike':(220,130,50),'ambulance':(240,240,240)}
            self.originalImage.fill(colors.get(vehicleClass,(128,128,128)))
            if vehicleClass == 'ambulance':
                pygame.draw.line(self.originalImage,(255,0,0),(w//2,2),(w//2,h-2),3)
                pygame.draw.line(self.originalImage,(255,0,0),(2,h//2),(w-2,h//2),3)

        self.currentImage = self.originalImage.copy()

        # Set stop position
        if direction == 'right':
            prev = vehicles[direction][lane][self.index-1] if self.index>0 and vehicles[direction][lane][self.index-1].crossed==0 else None
            self.stop = (prev.stop - prev.currentImage.get_rect().width - gap) if prev else defaultStop[direction]
            x[direction][lane] = max(0, x[direction][lane] - (self.currentImage.get_rect().width + gap))
        elif direction == 'left':
            prev = vehicles[direction][lane][self.index-1] if self.index>0 and vehicles[direction][lane][self.index-1].crossed==0 else None
            self.stop = (prev.stop + prev.currentImage.get_rect().width + gap) if prev else defaultStop[direction]
            x[direction][lane] += self.currentImage.get_rect().width + gap
        elif direction == 'down':
            prev = vehicles[direction][lane][self.index-1] if self.index>0 and vehicles[direction][lane][self.index-1].crossed==0 else None
            self.stop = (prev.stop - prev.currentImage.get_rect().height - gap) if prev else defaultStop[direction]
            y[direction][lane] -= self.currentImage.get_rect().height + gap
        elif direction == 'up':
            prev = vehicles[direction][lane][self.index-1] if self.index>0 and vehicles[direction][lane][self.index-1].crossed==0 else None
            self.stop = (prev.stop + prev.currentImage.get_rect().height + gap) if prev else defaultStop[direction]
            y[direction][lane] += self.currentImage.get_rect().height + gap

        simulation.add(self)

    def move(self):
        # ✅ FIX: move() is ONLY called from the pygame loop — no thread calls this
        spd = self.speed
        if self.index > 0:
            fv = vehicles[self.direction][self.lane][self.index-1]
            if   self.direction=='right': dist = fv.x-(self.x+self.currentImage.get_rect().width)
            elif self.direction=='down':  dist = fv.y-(self.y+self.currentImage.get_rect().height)
            elif self.direction=='left':  dist = self.x-(fv.x+fv.currentImage.get_rect().width)
            else:                         dist = self.y-(fv.y+fv.currentImage.get_rect().height)
            if dist < 50: spd = max(0.5, self.speed*(dist/50))

        can_go = {
            'right': currentGreen==0 and currentYellow==0,
            'down':  currentGreen==1 and currentYellow==0,
            'left':  (currentGreen==2 and currentYellow==0) or (emergencyActive and emergencyDirection=='left'),
            'up':    currentGreen==3 and currentYellow==0,
        }

        d = self.direction
        if d == 'right':
            if self.crossed==0 and self.x+self.currentImage.get_rect().width>stopLines[d]:
                self.crossed=1; vehicles[d]['crossed']+=1
            if not self.willTurn:
                if ((self.x+self.currentImage.get_rect().width<=self.stop or self.crossed==1 or can_go[d]) and
                    (self.index==0 or self.x+self.currentImage.get_rect().width<vehicles[d][self.lane][self.index-1].x-gap2)):
                    self.x += spd
            else:
                if self.crossed==0 or self.x+self.currentImage.get_rect().width<mid[d]['x']:
                    if ((self.x+self.currentImage.get_rect().width<=self.stop or self.crossed==1 or can_go[d]) and
                        (self.index==0 or self.x+self.currentImage.get_rect().width<vehicles[d][self.lane][self.index-1].x-gap2 or vehicles[d][self.lane][self.index-1].turned==1)):
                        self.x += spd
                else:
                    if self.turned==0:
                        self.rotateAngle+=rotationAngle
                        self.currentImage=pygame.transform.rotate(self.originalImage,-self.rotateAngle)
                        self.x+=2; self.y+=1.8
                        if self.rotateAngle>=90: self.turned=1
                    elif self.index==0 or self.y+self.currentImage.get_rect().height<vehicles[d][self.lane][self.index-1].y-gap2:
                        self.y+=spd

        elif d == 'down':
            if self.crossed==0 and self.y+self.currentImage.get_rect().height>stopLines[d]:
                self.crossed=1; vehicles[d]['crossed']+=1
            if not self.willTurn:
                if ((self.y+self.currentImage.get_rect().height<=self.stop or self.crossed==1 or can_go[d]) and
                    (self.index==0 or self.y+self.currentImage.get_rect().height<vehicles[d][self.lane][self.index-1].y-gap2)):
                    self.y += spd
            else:
                if self.crossed==0 or self.y+self.currentImage.get_rect().height<mid[d]['y']:
                    if ((self.y+self.currentImage.get_rect().height<=self.stop or self.crossed==1 or can_go[d]) and
                        (self.index==0 or self.y+self.currentImage.get_rect().height<vehicles[d][self.lane][self.index-1].y-gap2 or vehicles[d][self.lane][self.index-1].turned==1)):
                        self.y += spd
                else:
                    if self.turned==0:
                        self.rotateAngle+=rotationAngle
                        self.currentImage=pygame.transform.rotate(self.originalImage,-self.rotateAngle)
                        self.x-=2.5; self.y+=2
                        if self.rotateAngle>=90: self.turned=1
                    elif self.index==0 or self.x>vehicles[d][self.lane][self.index-1].x+gap2:
                        self.x-=spd

        elif d == 'left':
            if self.crossed==0 and self.x<stopLines[d]:
                self.crossed=1; vehicles[d]['crossed']+=1
            if not self.willTurn:
                if ((self.x>=self.stop or self.crossed==1 or can_go[d]) and
                    (self.index==0 or self.x>vehicles[d][self.lane][self.index-1].x+gap2)):
                    self.x -= spd
            else:
                if self.crossed==0 or self.x>mid[d]['x']:
                    if ((self.x>=self.stop or self.crossed==1 or can_go[d]) and
                        (self.index==0 or self.x>vehicles[d][self.lane][self.index-1].x+gap2 or vehicles[d][self.lane][self.index-1].turned==1)):
                        self.x -= spd
                else:
                    if self.turned==0:
                        self.rotateAngle+=rotationAngle
                        self.currentImage=pygame.transform.rotate(self.originalImage,-self.rotateAngle)
                        self.x-=1.8; self.y-=2.5
                        if self.rotateAngle>=90: self.turned=1
                    elif self.index==0 or self.y>vehicles[d][self.lane][self.index-1].y+gap2:
                        self.y-=spd

        elif d == 'up':
            if self.crossed==0 and self.y<stopLines[d]:
                self.crossed=1; vehicles[d]['crossed']+=1
            if not self.willTurn:
                if ((self.y>=self.stop or self.crossed==1 or can_go[d]) and
                    (self.index==0 or self.y>vehicles[d][self.lane][self.index-1].y+gap2)):
                    self.y -= spd
            else:
                if self.crossed==0 or self.y>mid[d]['y']:
                    if ((self.y>=self.stop or self.crossed==1 or can_go[d]) and
                        (self.index==0 or self.y>vehicles[d][self.lane][self.index-1].y+gap2 or vehicles[d][self.lane][self.index-1].turned==1)):
                        self.y -= spd
                else:
                    if self.turned==0:
                        self.rotateAngle+=rotationAngle
                        self.currentImage=pygame.transform.rotate(self.originalImage,-self.rotateAngle)
                        self.x+=1; self.y-=1
                        if self.rotateAngle>=90: self.turned=1
                    elif self.index==0 or self.x<vehicles[d][self.lane][self.index-1].x-gap2:
                        self.x+=spd


# ── HELPERS ──────────────────────────────────────────────────────────
def calculateGreenTime(count):
    if count==0: return 3
    if count==1: return 4
    if count==2: return 6
    if count==3: return 8
    return 10

def getGreenTime(direction):
    if direction=='right': return 10
    if direction=='down':  return 6
    if direction=='up':    return 3
    return calculateGreenTime(vehicle_detector.detection_results.get('left',0))

def printStatus():
    for i in range(noOfSignals):
        if i==currentGreen:
            if currentYellow==0:
                status='EMERGENCY' if (emergencyActive and directionNumbers[i]=='left') else 'GREEN'
                timer=emergencyCountdown if emergencyActive else signals[i].green
            else:
                status='EMERG YELLOW' if emergencyYellowPhase else 'YELLOW'
                timer=emergencyYellowTime if emergencyYellowPhase else signals[i].yellow
        else:
            status='RED'; timer=signals[i].red
        print(f"  {status} TS{i+1}({directionNumbers[i]}) Timer:{timer}")
    print(f"  Time: {timeElapsed}s\n")


# ── SIGNAL LOGIC (runs in its own thread) ────────────────────────────
def repeat():
    """
    ✅ FIX: repeat() is a standalone thread — NOT called from initialize()
    All timing via time.sleep(1). pygame loop never touches timing.
    """
    global currentGreen, currentYellow, nextGreen, timeElapsed
    global emergencyDetected, emergencyCountdown, emergencyActive
    global emergencyYellowPhase, emergencyYellowTime, immediateSwitch
    global preEmergencyGreen, preEmergencyYellow, lastEmergencyTime

    time.sleep(1)
    print("🔄 Signal logic thread started")

    while True:
        timeElapsed += 1
        printStatus()

        # Generate emergency vehicle periodically
        if (timeElapsed - lastEmergencyTime >= emergencyInterval
                and not emergencyDetected and not emergencyActive and not emergencyYellowPhase):
            generateEmergencyVehicle()

        # ✅ FIX: detect_vehicles() called ONCE per tick here only
        vehicle_detector.detect_vehicles()

        # ── Emergency countdown before switching ──
        if emergencyDetected and immediateSwitch and not emergencyActive and not emergencyYellowPhase:
            if emergencyCountdown > 0:
                # ✅ FIX: countdown decremented ONLY here, not in checkEmergency too
                emergencyCountdown -= 1
                print(f"🚨 Emergency switching in {emergencyCountdown}s...")
                time.sleep(1)
                continue

            if currentGreen != 2:
                # ✅ FIX: preEmergencyGreen declared at module level so 'global' works
                preEmergencyGreen    = currentGreen
                preEmergencyYellow   = currentYellow
                emergencyYellowPhase = True
                emergencyYellowTime  = 3
                immediateSwitch      = False
                currentYellow        = 1
                signals[currentGreen].yellow = emergencyYellowTime
                print("🟡 Emergency yellow phase started")
            time.sleep(1)
            continue

        # ── Emergency yellow phase ──
        if emergencyYellowPhase:
            if emergencyYellowTime > 0:
                emergencyYellowTime -= 1
                print(f"🟡 Emergency yellow: {emergencyYellowTime}s left")
                time.sleep(1)
                continue
            else:
                emergencyYellowPhase = False
                emergencyActive      = True
                emergencyCountdown   = emergencyGreenTime
                currentGreen         = 2
                currentYellow        = 0
                signals[2].green     = emergencyGreenTime
                signals[2].yellow    = defaultYellow
                print(f"🟢 Emergency green: {emergencyGreenTime}s for LEFT")
                time.sleep(1)
                continue

        # ── Emergency green phase ──
        if emergencyActive:
            if signals[currentGreen].green > 0:
                signals[currentGreen].green         -= 1
                signals[currentGreen].totalGreenTime += 1
                emergencyCountdown -= 1
                print(f"🚑 Emergency active: {emergencyCountdown}s left")
                time.sleep(1)
                continue
            else:
                emergencyActive   = False
                emergencyDetected = False
                currentGreen      = (2+1) % noOfSignals
                currentYellow     = 0
                nextGreen         = (currentGreen+1) % noOfSignals
                gt = getGreenTime(directionNumbers[currentGreen])
                signals[currentGreen].green        = gt
                signals[currentGreen].originalGreen= gt
                signals[currentGreen].yellow       = defaultYellow
                print(f"✅ Emergency done. Back to normal: {directionNumbers[currentGreen]} {gt}s")
                time.sleep(1)
                continue

        # ── Normal cycle: check upcoming vehicles ──
        if signals[currentGreen].green == detectionTime:
            nd = directionNumbers[nextGreen]
            gt = getGreenTime(nd)
            signals[nextGreen].green        = gt
            signals[nextGreen].originalGreen= gt
            print(f"🔍 Pre-set {nd} green to {gt}s")

        # Green counting down
        if currentYellow==0 and signals[currentGreen].green>0:
            signals[currentGreen].green         -= 1
            signals[currentGreen].totalGreenTime += 1
            time.sleep(1)
            continue

        # Transition to yellow
        if currentYellow==0 and signals[currentGreen].green<=0:
            currentYellow = 1
            for i in range(3):
                stops[directionNumbers[currentGreen]][i] = defaultStop[directionNumbers[currentGreen]]
                for v in vehicles[directionNumbers[currentGreen]][i]:
                    v.stop = defaultStop[directionNumbers[currentGreen]]
            print(f"🟡 Yellow: {directionNumbers[currentGreen]}")
            time.sleep(1)
            continue

        # Yellow counting down
        if currentYellow==1 and signals[currentGreen].yellow>0:
            signals[currentGreen].yellow -= 1
            time.sleep(1)
            continue

        # Signal change
        if currentYellow==1 and signals[currentGreen].yellow<=0:
            currentYellow = 0
            currentGreen  = nextGreen
            nextGreen     = (currentGreen+1) % noOfSignals
            gt = getGreenTime(directionNumbers[currentGreen])
            signals[currentGreen].green        = gt
            signals[currentGreen].originalGreen= gt
            signals[currentGreen].yellow       = defaultYellow
            print(f"🟢 {directionNumbers[currentGreen]} green: {gt}s")
            time.sleep(1)


def generateEmergencyVehicle():
    global lastEmergencyTime
    lastEmergencyTime = timeElapsed
    print("🚑 Generating emergency convoy in LEFT")
    for _ in range(random.randint(1,2)):
        Vehicle(random.randint(0,2), vehicleTypes[random.randint(0,4)], 2, 'left', 0)
        time.sleep(0.05)
    Vehicle(0, 'ambulance', 2, 'left', 0)


def generateVehicles():
    print("🚗 Vehicle generation started")
    while True:
        try:
            vt = random.randint(0,4)
            ln = random.randint(0,2)
            r  = random.randint(0,99)
            if   r < 45: dn,d = 0,'right'
            elif r < 75: dn,d = 3,'up'
            elif r < 90: dn,d = 1,'down'
            else:        dn,d = 2,'left'
            Vehicle(ln, vehicleTypes[vt], dn, d, 0)
            time.sleep(random.uniform(0.5,1.5) if d in ('right','up') else random.uniform(1.5,3.0))
        except Exception as e:
            print(f"Vehicle gen error: {e}")
            time.sleep(1)


def initialize():
    """Initialize signals only — does NOT start repeat() thread"""
    # ✅ FIX: Correct red times
    # Signal index 2 (left) starts green first
    ts1 = TrafficSignal(defaultRed, defaultYellow, defaultGreen)
    ts2 = TrafficSignal(defaultRed, defaultYellow, defaultGreen)
    ts3 = TrafficSignal(0,          defaultYellow, defaultGreen)  # left starts green
    ts4 = TrafficSignal(defaultRed, defaultYellow, defaultGreen)
    signals.extend([ts1, ts2, ts3, ts4])

    # ✅ FIX: Correct red times for all signals
    # Signal 0 (right) waits for: left green + left yellow + its own position in cycle
    signals[0].red = ts3.green + ts3.yellow + defaultGreen + defaultYellow  # after left & down
    signals[1].red = ts3.green + ts3.yellow                                  # after left
    signals[2].red = 0                                                        # starts green
    # ✅ FIX: signals[3] had same wrong value as signals[0]
    signals[3].red = ts3.green + ts3.yellow + (defaultGreen + defaultYellow)*2  # after left,down,right

    print("🚦 Signals initialized: Right=10s Down=6s Left=3-10s Up=3s")


# ── PYGAME MAIN LOOP ─────────────────────────────────────────────────
class Main:
    def __init__(self):
        print("🚦 SmartLight AI Traffic Simulation")
        print("🟢 Green times: Right=10s, Down=6s, Up=3s, Left=adaptive 3-10s")
        print("🚑 Emergency: ambulance in LEFT lane triggers priority green")

        initialize()

        # ✅ FIX: repeat() started as thread from Main, NOT from inside initialize()
        threading.Thread(target=repeat,           daemon=True).start()
        threading.Thread(target=generateVehicles, daemon=True).start()

        self.run_simulation()

    def run_simulation(self):
        screenW, screenH = 1250, 900
        screen = pygame.display.set_mode((screenW, screenH))
        pygame.display.set_caption("SmartLight AI - Traffic Simulation")

        try:
            background = pygame.image.load('images/mod_int2.png')
        except:
            background = pygame.Surface((screenW, screenH))
            background.fill((80,80,80))
            pygame.draw.rect(background,(50,50,50),(0,360,screenW,160))
            pygame.draw.rect(background,(50,50,50),(580,0,160,screenH))
            for i in range(0,screenW,40):
                pygame.draw.line(background,(255,255,0),(i,440),(i+20,440),2)
            for i in range(0,screenH,40):
                pygame.draw.line(background,(255,255,0),(660,i),(660,i+20),2)

        # Create signal images
        def makeSig(litColor):
            s = pygame.Surface((44,110))
            s.fill((30,30,30))
            for cy,col in [(18,(200,0,0)),(55,(200,200,0)),(92,(0,200,0))]:
                c = col if col==litColor else tuple(v//5 for v in col)
                pygame.draw.circle(s,c,(22,cy),14)
            return s

        redSig    = makeSig((200,0,0))
        yellowSig = makeSig((200,200,0))
        greenSig  = makeSig((0,200,0))

        font  = pygame.font.Font(None,30)
        small = pygame.font.Font(None,24)
        clock = pygame.time.Clock()

        WHITE  = (255,255,255)
        BLACK  = (0,0,0)
        GREEN  = (0,220,0)
        YELLOW = (220,220,0)
        RED    = (220,0,0)
        CYAN   = (0,220,220)
        ORANGE = (255,165,0)

        print("🎮 Pygame loop started")

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # ✅ FIX: proper cleanup instead of os._exit(1)
                    pygame.quit()
                    sys.exit()

            screen.blit(background,(0,0))

            # Draw signals
            for i in range(noOfSignals):
                sx,sy = signalCoods[i]
                tx,ty = signalTimerCoods[i]
                cx,cy = vehicleCountCoods[i]
                d     = directionNumbers[i]

                if i == currentGreen:
                    if currentYellow == 1:
                        img   = yellowSig
                        txt   = str(emergencyYellowTime if emergencyYellowPhase else signals[i].yellow)
                        color = YELLOW
                    elif emergencyActive and d=='left':
                        img   = greenSig if (timeElapsed%2==0) else yellowSig
                        txt   = f"AMB {emergencyCountdown}s"
                        color = ORANGE
                    else:
                        img   = greenSig
                        txt   = str(signals[i].green)
                        color = GREEN
                else:
                    img   = redSig
                    txt   = str(signals[i].red) if signals[i].red<=15 else "---"
                    color = RED

                screen.blit(img,(sx,sy))
                screen.blit(font.render(txt,True,color,BLACK),(tx,ty))

                # Stopped vehicles (W=waiting) and Crossed (C=crossed)
                stopped = vehicle_detector.detection_results.get(d,0)
                crossed = vehicles[d]['crossed']
                screen.blit(small.render(f"W:{stopped} C:{crossed}",True,BLACK,WHITE),(cx,cy))

            # Info bar
            r = vehicle_detector.detection_results
            screen.blit(font.render(f"Waiting → R:{r['right']} D:{r['down']} L:{r['left']} U:{r['up']}",True,GREEN,BLACK),(20,810))
            screen.blit(font.render(f"Time: {timeElapsed}s / {simTime}s",True,WHITE,BLACK),(20,840))
            screen.blit(small.render("Green: Right=10s  Down=6s  Up=3s  Left=3-10s (adaptive)",True,CYAN),(20,870))

            # Emergency banner
            if emergencyDetected or emergencyYellowPhase or emergencyActive:
                pygame.draw.rect(screen,RED,(10,10,520,72))
                pygame.draw.rect(screen,WHITE,(12,12,516,68),2)
                if emergencyYellowPhase:
                    screen.blit(font.render("🟡 EMERGENCY YELLOW — switching to LEFT",True,YELLOW),(20,20))
                    screen.blit(small.render(f"Emergency green in {emergencyYellowTime}s",True,WHITE),(20,46))
                elif emergencyActive:
                    screen.blit(font.render("🚑 EMERGENCY GREEN — LEFT LANE PRIORITY",True,GREEN),(20,20))
                    screen.blit(small.render(f"{emergencyCountdown}s remaining",True,WHITE),(20,46))
                else:
                    screen.blit(font.render("🚨 AMBULANCE DETECTED — LEFT LANE",True,WHITE),(20,20))
                    screen.blit(small.render(f"Switching in {emergencyCountdown}s...",True,YELLOW),(20,46))

            # Simulation complete
            if timeElapsed >= simTime:
                pygame.draw.rect(screen,BLACK,(300,350,650,200))
                pygame.draw.rect(screen,WHITE,(302,352,646,196),2)
                screen.blit(font.render("=== SIMULATION COMPLETE ===",True,GREEN),(320,370))
                total = sum(vehicles[directionNumbers[i]]['crossed'] for i in range(noOfSignals))
                screen.blit(font.render(f"Total vehicles crossed: {total}",True,WHITE),(320,410))
                for i,d in enumerate(['right','down','left','up']):
                    screen.blit(small.render(f"{d.upper()}: {vehicles[d]['crossed']} vehicles",True,CYAN),(320,445+i*25))
                screen.blit(small.render("Close window to exit",True,(180,180,180)),(320,550))

            # ✅ FIX: vehicle.move() called ONLY here in pygame loop — not in any thread
            vehicle_count = 0
            for v in simulation:
                screen.blit(v.currentImage,(v.x,v.y))
                v.move()
                vehicle_count += 1

            screen.blit(font.render(f"Vehicles on road: {vehicle_count}",True,WHITE,BLACK),(20,100))

            pygame.display.update()
            clock.tick(60)


if __name__ == "__main__":
    Main()