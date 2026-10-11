#!/usr/bin/env python3
"""
Artificial Life Simulation v5 — PyGame
========================================
Taxonomic differentiation: Mammals, Reptiles, Fungi, Plants each with
unique biology. 16 evolvable traits, diet spectrum, species auto-classification,
lineage evolution tracking, individual adaptation, parasitism.
Spatial grid for performance. 5-panel UI.

Mammals: warm-blooded, live birth, nursing, fur insulation, higher energy.
Reptiles: cold-blooded, egg-laying, basking behavior, scales (armor bonus).
Fungi: spore reproduction, mycelium energy networks, disease resistance.
Plants: root networks, seasonal dormancy, growth stages, seeding spread.

Controls: SPACE Pause  F Food  G Grid  L Lineage  R Reset
          +/- Speed  1-5 Tabs  CLICK Inspect
          E Event  D Disease  B Bloom  ESC Quit
"""

import pygame, random, math, sys
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from collections import defaultdict, deque

# ─── Constants ────────────────────────────────────────────────────────────────
SW, SH = 960, 780
PW = 440
SCR_W, SCR_H = SW + PW, 780
FPS = 60
DARK_BG = (18, 18, 24)
PANEL_BG = (28, 28, 38)
GRID_C = (30, 30, 42)
WHITE = (255, 255, 255)
TEXT_C = (200, 200, 210)
HILITE = (100, 255, 180)
DIV = (60, 60, 80)
TAB_A = (50, 50, 70)
TAB_I = (32, 32, 44)
PLANT_C = (40, 180, 80)
PREY_C = (60, 200, 255)
PRED_C = (255, 70, 70)
DECOMP_C = (200, 140, 255)

INIT_PREY, INIT_PRED, INIT_DECOMP, INIT_PLANT = 60, 12, 15, 120
MAX_PLANT = 400
PLANT_RATE = 0.4
PLANT_E = 40
MAX_PREY, MAX_PRED, MAX_DECOMP = 300, 100, 80
MAX_PARTICLES = 500

SEASON_LEN = 1800
SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
S_COL = {"Spring": (120, 220, 120), "Summer": (240, 220, 80),
         "Autumn": (220, 140, 60), "Winter": (140, 180, 240)}
S_FOOD = {"Spring": 1.5, "Summer": 1.0, "Autumn": 0.5, "Winter": 0.2}
S_ENRG = {"Spring": 1.0, "Summer": 1.1, "Autumn": 1.2, "Winter": 1.5}

STAGE_EGG = 0; STAGE_JUV = 1; STAGE_ADULT = 2; STAGE_ELDER = 3
STAGE_NAMES = ["Egg", "Juvenile", "Adult", "Elder"]

S_WANDER = "wander"; S_FLEE = "flee"; S_HUNT = "hunt"; S_EAT = "eat"
S_SLEEP = "sleep"; S_AMBUSH = "ambush"; S_MOB = "mob"; S_COURT = "court"
S_SCAV = "scavenge"; S_FRENZY = "frenzy"; S_PACK = "pack"; S_PARENT = "parent"
S_PLAY = "play"; S_MIGRATE = "migrate"; S_TERRITORY = "territory"
S_HATCH = "hatch"; S_FORAGE = "forage"; S_DECOMPOSE = "decompose"
S_PARASITE = "parasite"
S_BASK = "bask"; S_SPORE = "spore"

# ─── Taxonomy types ──────────────────────────────────────────────────────────
T_MAMMAL = "mammal"; T_REPTILE = "reptile"; T_FUNGI = "fungi"; T_PLANT = "plant"
TAXONOMY = [T_MAMMAL, T_REPTILE, T_FUNGI, T_PLANT]
TAXON_COLORS = {T_MAMMAL: (220, 180, 140), T_REPTILE: (100, 200, 120),
                T_FUNGI: (200, 140, 255), T_PLANT: (40, 180, 80)}
TAXON_LABELS = {T_MAMMAL: "Mam", T_REPTILE: "Rep", T_FUNGI: "Fun", T_PLANT: "Plt"}


# Spatial grid cell size for performance
CELL = 100
GCOLS = (SW + CELL - 1) // CELL
GROWS = (SH + CELL - 1) // CELL

_nid = [0]
def uid(): _nid[0] += 1; return _nid[0]
def rst_id(): _nid[0] = 0

def clamp(v, lo, hi): return max(lo, min(hi, v))
def dst(x1, y1, x2, y2): return math.hypot(x2 - x1, y2 - y1)
def ang(x1, y1, x2, y2): return math.atan2(y2 - y1, x2 - x1)
def lerpc(c1, c2, t):
    t = clamp(t, 0, 1)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
def hsv2rgb(h, s, v):
    h %= 360; c = v * s; x = c * (1 - abs((h / 60) % 2 - 1)); m = v - c
    if h < 60:    r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else:         r, g, b = c, 0, x
    return (int((r+m)*255), int((g+m)*255), int((b+m)*255))

def build_grid(creatures):
    g = [[[] for _ in range(GROWS)] for _ in range(GCOLS)]
    for c in creatures:
        if not c.alive: continue
        cx = int(c.x // CELL); cy = int(c.y // CELL)
        cx = clamp(cx, 0, GCOLS-1); cy = clamp(cy, 0, GROWS-1)
        g[cx][cy].append(c)
    return g

def query_grid(grid, x, y, radius):
    results = []
    c0 = clamp(int((x - radius) // CELL), 0, GCOLS-1)
    c1 = clamp(int((x + radius) // CELL), 0, GCOLS-1)
    r0 = clamp(int((y - radius) // CELL), 0, GROWS-1)
    r1 = clamp(int((y + radius) // CELL), 0, GROWS-1)
    r2 = radius * radius
    for cx in range(c0, c1+1):
        for cy in range(r0, r1+1):
            for c in grid[cx][cy]:
                dx = c.x - x; dy = c.y - y
                if dx*dx + dy*dy <= r2:
                    results.append(c)
    return results

# ─── Small helper classes ─────────────────────────────────────────────────────
class Particle:
    __slots__ = ("x","y","vx","vy","life","ml","color","sz")
    def __init__(self, x, y, vx, vy, life, color, sz=2):
        self.x=x; self.y=y; self.vx=vx; self.vy=vy; self.life=life; self.ml=life; self.color=color; self.sz=sz
    def update(self):
        self.x += self.vx; self.y += self.vy; self.vy -= 0.01; self.life -= 1
        return self.life > 0
    def draw(self, srf):
        a = clamp(self.life / self.ml, 0, 1)
        r = max(1, int(self.sz * a))
        c = lerpc(DARK_BG, self.color, a)
        pygame.draw.circle(srf, c, (int(self.x), int(self.y)), r)

class Corpse:
    __slots__ = ("x","y","energy","radius","age","species","toxicity","hue")
    def __init__(self, cr):
        self.x=cr.x; self.y=cr.y; self.energy=cr.max_energy*0.3
        self.radius=cr.genome.size*0.8; self.age=0
        self.species=cr.species; self.toxicity=cr.genome.toxicity; self.hue=cr.genome.hue
    def decay(self):
        self.age += 1; self.energy -= 0.12; self.radius = max(1, self.radius - 0.003)
        return self.energy > 0 and self.age < 600

class FertileZone:
    __slots__ = ("x","y","radius","strength","life","max_life")
    def __init__(self, x, y, radius=60, strength=1.5, life=600):
        self.x=x; self.y=y; self.radius=radius; self.strength=strength
        self.life=life; self.max_life=life
    def update(self):
        self.life -= 1; self.strength = 1.5 * (self.life / self.max_life)
        return self.life > 0

class Nest:
    __slots__ = ("x","y","owner_id","lineage_id","strength","life","species","hue")
    def __init__(self, x, y, owner):
        self.x=x; self.y=y; self.owner_id=owner.id; self.lineage_id=owner.lineage_id
        self.strength=1.0; self.life=1200; self.species=owner.species; self.hue=owner.genome.hue
    def update(self):
        self.life -= 1; self.strength = clamp(self.life / 1200, 0, 1)
        return self.life > 0

@dataclass
class SimEvent:
    tick: int; text: str; color: Tuple[int,int,int]; icon: str

class EventLog:
    def __init__(self, mx=250): self.events = deque(maxlen=mx)
    def add(self, t, txt, c=TEXT_C, ic="*"): self.events.appendleft(SimEvent(t, txt, c, ic))
    def recent(self, n=50): return list(self.events)[:n]

class DiseaseOutbreak:
    def __init__(self, tick, x, y, name="Plague", vir=0.3, leth=0.05, rad=80):
        self.tick=tick; self.x=x; self.y=y; self.name=name
        self.vir=vir; self.leth=leth; self.rad=rad
        self.dur=random.randint(300,800); self.active=True; self.infected=0; self.dead=0
        self.color=(180,50,220)

class Disaster:
    def __init__(self, tick, dt, x, y, rad, dur, col):
        self.tick=tick; self.dt=dt; self.x=x; self.y=y; self.rad=rad; self.dur=dur
        self.col=col; self.active=True; self.age=0; self.killed=0
    def update(self):
        self.age += 1
        if self.age > self.dur: self.active = False
    def crad(self):
        if self.dt == "meteor":
            if self.age < self.dur*0.3: return self.rad * self.age / (self.dur*0.3)
            elif self.age < self.dur*0.6: return self.rad
            else: return self.rad * (1 - (self.age - self.dur*0.6)/(self.dur*0.4))
        return self.rad * min(1, self.age / 30)
    def draw(self, srf):
        r = int(self.crad())
        if r < 2: return
        a = int(clamp(1 - self.age/self.dur, 0, 1) * 40)
        if self.dt == "fire":
            f = random.randint(-10, 10)
            c = (clamp(self.col[0]+f,0,255), clamp(self.col[1]+f//2,0,255), self.col[2])
            s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*c, a+20), (r,r), r)
            pygame.draw.circle(s, (*c, a+40), (r,r), r//2)
            srf.blit(s, (int(self.x)-r, int(self.y)-r))
        elif self.dt == "flood":
            s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.col, a), (r,r), r)
            srf.blit(s, (int(self.x)-r, int(self.y)-r))
        elif self.dt == "meteor":
            i = int(clamp(1-self.age/self.dur,0,1)*60)
            s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255,255,200,i), (r,r), r)
            srf.blit(s, (int(self.x)-r, int(self.y)-r))
        elif self.dt == "bloom":
            s = pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.col, a//2), (r,r), r)
            srf.blit(s, (int(self.x)-r, int(self.y)-r))

# ─── Species Record ───────────────────────────────────────────────────────────
class SpeciesRecord:
    def __init__(self, sid, base_species, avg_traits):
        self.sid = sid
        self.base = base_species
        self.avg_traits = dict(avg_traits)
        self.pop = 1
        self.peak = 1
        self.alive = True
        self.birth_tick = 0
        self.name = self._gen_name()
        self.color = hsv2rgb(avg_traits.get("hue", 180), 0.7, 0.9)
        self.trait_history = []  # list of (tick, {trait: avg})
        self.generation = 0

    def _gen_name(self):
        dp = self.avg_traits.get("diet_pref", 0.5)
        ag = self.avg_traits.get("aggression", 0.5)
        # Taxonomy-based prefix
        tax = self.avg_traits.get("_taxonomy", "")
        if tax == T_MAMMAL: tax_label = "M."
        elif tax == T_REPTILE: tax_label = "R."
        elif tax == T_FUNGI: tax_label = "F."
        else: tax_label = ""
        if dp < 0.25:
            prefix = "Herbi"
        elif dp < 0.5:
            prefix = "Omniv"
        elif dp < 0.75:
            prefix = "Mesoc"
        else:
            prefix = "Carni"
        if ag > 0.7:
            mid = "ferox "
        elif ag < 0.3:
            mid = "dulcis "
        else:
            mid = "medius "
        suffixes = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
                     "iota", "kappa", "lambda", "mu", "nu", "xi", "pi", "rho"]
        return tax_label + prefix + " " + mid + suffixes[self.sid % len(suffixes)]

    def snapshot(self, tick, creatures):
        if not creatures:
            return
        n = len(creatures)
        avg = {}
        for tn in Genome.NAMES:
            avg[tn] = sum(getattr(c.genome, tn) for c in creatures) / n
        # Store majority taxonomy
        tax_counts = defaultdict(int)
        for c in creatures:
            tax_counts[c.taxonomy] += 1
        avg["_taxonomy"] = max(tax_counts, key=tax_counts.get) if tax_counts else "mammal"
        self.avg_traits = avg
        self.color = hsv2rgb(avg.get("hue", 180), 0.7, 0.9)
        self.trait_history.append((tick, dict(avg)))
        if len(self.trait_history) > 20:
            self.trait_history.pop(0)
        self.name = self._gen_name()

    def trait_trend(self, trait_name):
        if len(self.trait_history) < 3:
            return 0.0
        old = self.trait_history[0][1].get(trait_name, 0)
        new = self.trait_history[-1][1].get(trait_name, 0)
        rng = Genome.RANGES[Genome.NAMES.index(trait_name)] if trait_name in Genome.NAMES else (0,1)
        span = rng[1] - rng[0]
        if span == 0: return 0
        return (new - old) / span

# ─── Genome (16 evolvable traits) ─────────────────────────────────────────────
@dataclass
class Genome:
    speed: float=2.0
    size: float=5.0
    perception: float=80.0
    efficiency: float=1.0
    aggression: float=0.5
    sociability: float=0.3
    hue: float=200.0
    lifespan: float=3000.0
    fertility: float=0.5
    toxicity: float=0.0
    mutation_rate: float=0.25
    armor: float=0.0
    camouflage: float=0.0
    intelligence: float=0.3
    regeneration: float=0.0
    diet_pref: float=0.0
    NAMES = ["speed","size","perception","efficiency","aggression","sociability",
             "hue","lifespan","fertility","toxicity","mutation_rate",
             "armor","camouflage","intelligence","regeneration","diet_pref"]
    LABELS = ["Spd","Sz","Prc","Eff","Agg","Soc","Hue","Life","Fert",
              "Tox","Mut","Arm","Cam","Int","Reg","Diet"]
    RANGES = [(0.5,6.0),(3.0,14.0),(20,220),(0.2,2.5),(0,1),(0,1),(0,360),
              (800,6000),(0.1,1.0),(0,1),(0.05,0.6),(0,1),(0,1),(0,1),(0,1),(0,1)]
    def mutate(self, cs=None):
        s = cs if cs is not None else self.mutation_rate
        v = []
        for i,n in enumerate(self.NAMES):
            lo,hi = self.RANGES[i]; val = getattr(self, n)
            v.append(clamp(val + random.gauss(0, s*(hi-lo)*0.08), lo, hi))
        return Genome(*v)
    @staticmethod
    def crossover(g1, g2):
        v = []
        for i,n in enumerate(Genome.NAMES):
            lo,hi = Genome.RANGES[i]
            v.append(clamp(getattr(g1,n)*random.random() + getattr(g2,n)*(1-random.random()), lo, hi))
        c = Genome(*v)
        c.mutation_rate = clamp((g1.mutation_rate+g2.mutation_rate)/2 + random.gauss(0,0.02), 0.05, 0.6)
        return c.mutate()
    def trait_vector(self):
        return [getattr(self, n) for n in self.NAMES]

# ─── Lineage (with evolution tracking) ────────────────────────────────────────
class Lineage:
    def __init__(self, fid, hue, sp):
        self.fid=fid; self.hue=hue; self.sp=sp; self.color=hsv2rgb(hue,0.7,0.9)
        self.n=1; self.births=0; self.max_gen=0; self.alive=True
        self.species_id = -1
        self.trait_snapshots = []  # (tick, avg_genome_dict)
    def rcol(self): self.color = hsv2rgb(self.hue, 0.7, 0.9)
    def snapshot_traits(self, tick, creatures):
        if not creatures: return
        n = len(creatures)
        avg = {}
        for tn in Genome.NAMES:
            avg[tn] = sum(getattr(c.genome, tn) for c in creatures) / n
        self.hue = avg["hue"]; self.rcol()
        self.trait_snapshots.append((tick, avg))
        if len(self.trait_snapshots) > 15:
            self.trait_snapshots.pop(0)

# ─── Plant ────────────────────────────────────────────────────────────────────
class Plant:
    __slots__ = ("x","y","energy","radius","max_energy","growth_stage","dormant",
                 "root_links","age","plant_type","toxicity")
    def __init__(self, x, y, energy=PLANT_E):
        self.x=x; self.y=y; self.energy=energy; self.radius=random.uniform(2.5,4.5)
        self.max_energy = PLANT_E * 1.5
        self.growth_stage = 0  # 0=seedling,1=mature,2=flowering,3=seeding
        self.dormant = False
        self.root_links = 0
        self.age = 0
        self.toxicity = random.random() < 0.1  # 10% of plants are toxic
        # Plant sub-types for diversity
        self.plant_type = random.choice(["grass", "bush", "tree"])

    def update(self, season, neighbor_count=0):
        """Update plant growth based on season and neighbors."""
        self.age += 1
        self.root_links = neighbor_count

        # Seasonal dormancy
        if season == "Winter":
            self.dormant = True
            self.energy -= 0.005  # minimal drain while dormant
            if self.growth_stage > 0 and random.random() < 0.001:
                self.growth_stage -= 1  # can regress in winter
            return False

        self.dormant = False
        food_mult = S_FOOD[season]

        # Photosynthesis: gain energy based on season
        if not self.dormant:
            photo_gain = 0.08 * food_mult
            # Root network bonus: plants near other plants grow faster
            if neighbor_count > 0:
                photo_gain *= (1.0 + min(neighbor_count * 0.1, 0.5))
            # Tree-type plants are more efficient but slower
            if self.plant_type == "tree":
                photo_gain *= 1.3
            elif self.plant_type == "grass":
                photo_gain *= 0.8
            self.energy = min(self.max_energy, self.energy + photo_gain)

        # Growth stages
        if self.energy > PLANT_E * 0.3 and self.growth_stage == 0:
            self.growth_stage = 1  # seedling -> mature
        if self.energy > PLANT_E * 0.8 and self.age > 200 and self.growth_stage == 1:
            self.growth_stage = 2  # mature -> flowering
        if self.energy > PLANT_E * 1.1 and self.age > 500 and self.growth_stage == 2:
            self.growth_stage = 3  # flowering -> seeding

        # Size based on growth stage and type
        base_r = {"grass": 2.0, "bush": 3.5, "tree": 5.0}.get(self.plant_type, 3.0)
        stage_mult = [0.6, 1.0, 1.2, 1.1][min(self.growth_stage, 3)]
        self.radius = base_r * stage_mult

        # Seeding plants spread
        can_spread = (self.growth_stage == 3 and self.energy > PLANT_E * 0.9
                       and food_mult > 0.8)
        return can_spread

    def fire_vulnerability(self):
        """Trees burn easily, grass less so."""
        return {"grass": 0.3, "bush": 0.6, "tree": 0.9}.get(self.plant_type, 0.5)

# ─── Creature base with diet, adaptation, life stages ─────────────────────────
class Creature:
    def __init__(self, x, y, genome, energy, base_color, species_name):
        self.id = uid(); self.x=x; self.y=y; self.genome=genome
        self.energy=energy; self.max_energy=energy; self.base_color=base_color
        self.species_name = species_name
        self.vx = random.uniform(-1,1); self.vy = random.uniform(-1,1)
        self.age = 0; self.alive = True; self.repro_cd = 0
        self.wander_ang = random.uniform(0, math.pi*2)
        self.parent_ids: Tuple[int,...] = (); self.lineage_id = 0
        self.lineage_depth = 0; self.children_count = 0
        self.stage = STAGE_JUV
        self.stage_timer = 0; self.egg_hatch_time = 0
        self.state = S_WANDER; self.state_timer = 0
        self.sleep_thresh = 0.2; self.kills = 0
        self.diseased = False; self.disease_timer = 0; self.disease_immune = 0
        self.alarm = 0.0; self.protecting = None
        self.dominance_score = 0.0; self.is_alpha = False
        self.play_target = None
        # Species classification
        self.species_id = -1
        # Individual adaptation (Lamarckian, NOT inherited)
        self.adapt = {n: 0.0 for n in Genome.NAMES}
        # Experience counters
        self.exp_flee = 0; self.exp_hunt = 0; self.exp_eat_plant = 0
        self.exp_eat_meat = 0; self.exp_social = 0; self.exp_fight = 0
        self.parasite_host = None  # for decomposer parasitism
        self.parasite_energy_drain = 0.0
        # Taxonomy
        self.taxonomy = T_MAMMAL
        self.bask_timer = 0
        self.spore_cooldown = 0
        self.root_links = 0  # for plants: number of connected plant neighbors
        self.growth_stage = 0  # for plants: 0=seedling,1=mature,2=flowering,3=seeding
        self.dormant = False  # for plants: winter dormancy

    @property
    def species(self): return self.species_name

    @property
    def display_color(self):
        return hsv2rgb(self.genome.hue, 0.65, 0.92)

    @property
    def disease_resistance(self):
        base = clamp(self.genome.efficiency * 0.5 + self.genome.size * 0.05, 0.05, 0.95)
        return clamp(base + self.genome.intelligence * 0.1, 0.05, 0.98)

    @property
    def stage_name(self):
        return STAGE_NAMES[self.stage]

    def eff_trait(self, name):
        """Get effective trait value including adaptation."""
        base = getattr(self.genome, name)
        return clamp(base + self.adapt.get(name, 0.0),
                      Genome.RANGES[Genome.NAMES.index(name)][0],
                      Genome.RANGES[Genome.NAMES.index(name)][1])

    def is_mammal(self): return self.taxonomy == T_MAMMAL
    def is_reptile(self): return self.taxonomy == T_REPTILE
    def is_fungi(self): return self.taxonomy == T_FUNGI

    @property
    def metabolic_mult(self):
        """Energy cost multiplier based on taxonomy and season context."""
        # Mammals: warm-blooded, higher baseline cost but stable
        if self.taxonomy == T_MAMMAL:
            return 1.12
        # Reptiles: cold-blooded, lower cost but need external heat
        elif self.taxonomy == T_REPTILE:
            return 0.82
        # Fungi: slow metabolism
        elif self.taxonomy == T_FUNGI:
            return 0.75
        return 1.0

    @property
    def cold_resistance(self):
        """How well the creature resists cold (seasonal energy penalty)."""
        if self.taxonomy == T_MAMMAL:
            return 0.7  # fur insulation
        elif self.taxonomy == T_REPTILE:
            return 0.15  # very vulnerable to cold
        elif self.taxonomy == T_FUNGI:
            return 0.4  # underground mycelium survives
        return 0.0

    @property
    def heat_resistance(self):
        """How well the creature tolerates heat/fire."""
        if self.taxonomy == T_REPTILE:
            return 0.6  # scales reflect heat
        elif self.taxonomy == T_MAMMAL:
            return 0.3  # fur is a liability
        elif self.taxonomy == T_FUNGI:
            return 0.2  # very vulnerable
        return 0.0

    @property
    def natural_armor(self):
        """Taxonomy-based armor bonus (added to evolved armor)."""
        if self.taxonomy == T_REPTILE:
            return 0.12  # scales
        elif self.taxonomy == T_MAMMAL:
            return 0.03  # thick hide
        return 0.0

    def season_energy_mult(self, season):
        """Get effective energy multiplier for a given season."""
        base = S_ENRG[season]
        if season == "Winter":
            # Mammals are well insulated; reptiles suffer greatly
            cold_factor = 1.0 - (1.0 - self.cold_resistance) * 0.4
            return base * cold_factor
        elif season == "Summer":
            # Reptiles thrive; mammals overheat slightly
            if self.taxonomy == T_REPTILE:
                return base * 0.9  # less energy cost in warmth
            elif self.taxonomy == T_MAMMAL:
                return base * 1.05
        return base

    def try_bask(self, season, particles):
        """Reptile basking: gain energy from sunlight when cold."""
        if self.taxonomy != T_REPTILE or season == "Summer":
            return False
        if self.energy > self.max_energy * 0.7:
            return False
        if self.state not in (S_WANDER,):
            return False
        # Reptiles bask when it's cold and they need energy
        if season in ("Winter", "Autumn") and self.energy < self.max_energy * 0.5:
            self.state = S_BASK
            self.bask_timer = random.randint(60, 180)
            self.vx = 0; self.vy = 0
            return True
        elif season == "Spring" and self.energy < self.max_energy * 0.3:
            self.state = S_BASK
            self.bask_timer = random.randint(30, 90)
            self.vx = 0; self.vy = 0
            return True
        return False

    def update_bask(self, season, particles):
        """Process basking state for reptiles."""
        self.vx *= 0.9; self.vy *= 0.9
        self.bask_timer -= 1
        # Gain energy from "sunlight" - more in summer, less in winter
        sun_map = {"Spring": 0.12, "Summer": 0.25, "Autumn": 0.08, "Winter": 0.04}
        gain = sun_map.get(season, 0.1) * self.eff_trait("efficiency")
        # Larger reptiles absorb more heat (surface area to volume)
        gain *= (0.5 + self.eff_trait("size") / 14.0)
        self.energy = min(self.max_energy, self.energy + gain)
        # Occasional warmth particle
        if self.bask_timer % 20 == 0:
            particles.append(Particle(
                self.x + random.uniform(-3, 3), self.y - self.eff_trait("size") - 2,
                random.uniform(-0.1, 0.1), random.uniform(-0.3, -0.1),
                random.randint(20, 40), (255, 220, 100), 2))
        if self.bask_timer <= 0 or self.energy > self.max_energy * 0.75:
            self.state = S_WANDER


    def _stage_mults(self):
        if self.stage == STAGE_EGG: return (0, 0.5, 0.3, 0.3)
        elif self.stage == STAGE_JUV: return (1.15, 0.7, 0.9, 0.8)
        elif self.stage == STAGE_ELDER: return (0.75, 1.1, 1.3, 1.2)
        return (1.0, 1.0, 1.0, 1.0)

    def _advance_stage(self):
        if self.stage == STAGE_EGG and self.age >= self.egg_hatch_time:
            self.stage = STAGE_JUV; return True
        if self.stage == STAGE_JUV and self.age > self.genome.lifespan * 0.15:
            self.stage = STAGE_ADULT; return True
        if self.stage == STAGE_ADULT and self.age > self.genome.lifespan * 0.75:
            self.stage = STAGE_ELDER; return True
        return False

    def _norm_vel(self):
        sm, _, _, _ = self._stage_mults()
        spd = self.eff_trait("speed") * sm
        mag = math.hypot(self.vx, self.vy)
        if mag > 0: self.vx = (self.vx/mag)*spd; self.vy = (self.vy/mag)*spd

    def move(self, sw, sh, emult=1.0):
        if self.stage == STAGE_EGG:
            self.age += 1; return
        self.x += self.vx; self.y += self.vy
        _, sz_m, _, ec_m = self._stage_mults()
        r = self.eff_trait("size") * sz_m
        if self.x < r: self.x=r; self.vx*=-1
        elif self.x > sw-r: self.x=sw-r; self.vx*=-1
        if self.y < r: self.y=r; self.vy*=-1
        elif self.y > sh-r: self.y=sh-r; self.vy*=-1
        _, _, _, ecm = self._stage_mults()
        eff = self.eff_trait("efficiency")
        spd = self.eff_trait("speed")
        sz = self.eff_trait("size")
        cost = 0.035 * eff * (spd/2) * (sz/6) * ecm * emult
        cost *= self.metabolic_mult  # taxonomy metabolism
        cost *= (1.0 + (self.genome.armor + self.natural_armor) * 0.12)  # armor costs energy
        self.energy -= cost
        # Regeneration
        regen = self.eff_trait("regeneration") * 0.04 * (0.5 if self.diseased else 1.0)
        self.energy = min(self.max_energy, self.energy + regen)
        self.age += 1
        if self.repro_cd > 0: self.repro_cd -= 1
        if self.disease_immune > 0: self.disease_immune -= 1
        if self.alarm > 0: self.alarm = max(0, self.alarm - 0.015)
        self._advance_stage()

    def apply_adaptation(self):
        """Apply small trait shifts based on experience (Lamarckian)."""
        if self.age % 200 != 0 or self.stage == STAGE_EGG: return
        rate = 0.002  # 0.2% shift per adaptation cycle
        if self.exp_flee > 10:
            self.adapt["speed"] += rate * min(self.exp_flee / 50, 1.0)
            self.adapt["perception"] += rate * 0.5 * min(self.exp_flee / 50, 1.0)
        if self.exp_hunt > 10:
            self.adapt["aggression"] += rate * 0.5 * min(self.exp_hunt / 30, 1.0)
            self.adapt["intelligence"] += rate * 0.3 * min(self.exp_hunt / 30, 1.0)
        if self.exp_eat_plant > 20:
            self.adapt["diet_pref"] -= rate * 0.5 * min(self.exp_eat_plant / 60, 1.0)
            self.adapt["efficiency"] += rate * 0.3
        if self.exp_eat_meat > 10:
            self.adapt["diet_pref"] += rate * 0.5 * min(self.exp_eat_meat / 30, 1.0)
        if self.exp_social > 20:
            self.adapt["sociability"] += rate * 0.3 * min(self.exp_social / 50, 1.0)
        if self.exp_fight > 5:
            self.adapt["armor"] += rate * 0.4 * min(self.exp_fight / 15, 1.0)
            self.adapt["size"] += rate * 0.2 * min(self.exp_fight / 15, 1.0)
        # Decay experience
        self.exp_flee *= 0.7; self.exp_hunt *= 0.7; self.exp_eat_plant *= 0.7
        self.exp_eat_meat *= 0.7; self.exp_social *= 0.7; self.exp_fight *= 0.7

    def wander(self):
        self.wander_ang += random.gauss(0, 0.5)
        self.vx += math.cos(self.wander_ang)*0.3; self.vy += math.sin(self.wander_ang)*0.3
        self._norm_vel()

    def steer_to(self, tx, ty, w=0.5):
        a = ang(self.x, self.y, tx, ty)
        self.vx += math.cos(a)*w; self.vy += math.sin(a)*w; self._norm_vel()

    def steer_away(self, tx, ty, w=0.6):
        a = ang(tx, ty, self.x, self.y)
        self.vx += math.cos(a)*w; self.vy += math.sin(a)*w; self._norm_vel()

    def flock(self, neighbors):
        if self.eff_trait("sociability") < 0.1 or not neighbors: return
        sx=sy=n=0
        for o in neighbors:
            if o.id==self.id or not o.alive: continue
            d = dst(self.x,self.y,o.x,o.y)
            if 0 < d < self.eff_trait("perception") * 0.6:
                sx+=o.x; sy+=o.y; n+=1
                if d < self.eff_trait("size")*3:
                    self.steer_away(o.x, o.y, w=0.2*self.eff_trait("sociability"))
        if n > 0: self.steer_to(sx/n, sy/n, w=0.15*self.eff_trait("sociability"))

    def emit_alarm(self, neighbors):
        if self.alarm < 0.3: return
        for o in neighbors:
            if o.id==self.id or not o.alive: continue
            d = dst(self.x,self.y,o.x,o.y)
            if d < self.eff_trait("perception")*0.8:
                o.alarm = min(1.0, o.alarm + self.alarm*0.3*(1-d/(self.eff_trait("perception")*0.8)))

    def try_sleep(self, particles):
        if self.energy < self.max_energy * self.sleep_thresh and self.stage in (STAGE_ADULT, STAGE_ELDER):
            if self.state not in (S_FLEE, S_MOB, S_FRENZY, S_AMBUSH):
                self.state = S_SLEEP; self.state_timer = random.randint(60, 180)
                self.vx=0; self.vy=0; return True
        return False

    def update_sleep(self, particles):
        self.vx*=0.9; self.vy*=0.9
        rec = 0.15 * (0.3 if self.diseased else 1.0)
        self.energy = min(self.max_energy, self.energy + rec)
        self.state_timer -= 1
        if self.state_timer % 15 == 0:
            particles.append(Particle(self.x+random.uniform(-5,5), self.y-self.eff_trait("size"),
                                       random.uniform(-0.2,0.2), random.uniform(-0.3,-0.1),
                                       random.randint(30,50), (150,150,220), 2))
        if self.state_timer <= 0 or self.energy > self.max_energy*0.6:
            self.state = S_WANDER

    def try_scavenge(self, corpses):
        dp = self.eff_trait("diet_pref")
        if self.energy > self.max_energy*0.7 or self.stage == STAGE_EGG: return False
        meat_eff = 0.3 + dp * 0.5  # herbivores can scavenge poorly
        if meat_eff < 0.2: return False
        for c in corpses:
            d = dst(self.x,self.y,c.x,c.y)
            if d < self.eff_trait("perception")*0.5:
                self.steer_to(c.x, c.y, 0.6)
                if d < self.eff_trait("size") + c.radius:
                    gain = c.energy*0.5*meat_eff*(1-c.toxicity*0.4)
                    self.energy = min(self.max_energy, self.energy+gain)
                    self.exp_eat_meat += 1
                    if c.toxicity > 0.5 and random.random() < c.toxicity*0.1:
                        self.diseased=True; self.disease_timer=random.randint(100,300)
                    c.energy=0; self.state=S_EAT; self.state_timer=10
                return True
        return False

    def territorial_check(self, same_species, particles):
        if self.eff_trait("aggression") < 0.6 or self.stage != STAGE_ADULT: return
        for o in same_species:
            if o.id==self.id or not o.alive or o.stage != STAGE_ADULT: continue
            d = dst(self.x,self.y,o.x,o.y)
            if d < self.eff_trait("size")*3 and d > 0:
                my_str = self.eff_trait("size") * self.eff_trait("aggression") * (self.energy/self.max_energy)
                their_str = o.eff_trait("size") * o.eff_trait("aggression") * (o.energy/o.max_energy)
                armor_reduct = 1.0 - o.eff_trait("armor") * 0.3
                if my_str > their_str and random.random() < 0.02:
                    dmg = 5 * armor_reduct
                    o.energy -= dmg; o.steer_away(self.x, self.y, 0.8)
                    self.energy -= 1
                    self.exp_fight += 1; o.exp_fight += 1
                    for _ in range(3):
                        particles.append(Particle((self.x+o.x)/2, (self.y+o.y)/2,
                                                   random.uniform(-1,1), random.uniform(-1,1),
                                                   12, (255,200,100), 2))

    def play_behavior(self, same_species_juvs, particles):
        if self.stage != STAGE_JUV or self.eff_trait("sociability") < 0.2: return
        if self.play_target and (not self.play_target.alive or self.state != S_PLAY):
            self.play_target = None; self.state = S_WANDER
        if self.play_target and self.state == S_PLAY:
            d = dst(self.x,self.y,self.play_target.x,self.play_target.y)
            if d < self.eff_trait("size")*2:
                self.play_target.state = S_PLAY
                self.play_target.play_target = self
                self.state = S_WANDER; self.play_target = None
                self.energy -= 0.5
            else:
                self.steer_to(self.play_target.x, self.play_target.y, 0.4)
            return
        if random.random() < 0.01:
            candidates = [o for o in same_species_juvs if o.id!=self.id and o.alive
                          and dst(self.x,self.y,o.x,o.y) < self.eff_trait("perception")*0.5]
            if candidates:
                self.play_target = random.choice(candidates)
                self.state = S_PLAY; self.state_timer = random.randint(60, 150)

    def draw(self, srf, lin_mode=False, lin_reg=None):
        if not self.alive: return
        _, sz_m, _, _ = self._stage_mults()
        r = max(2, int(self.eff_trait("size") * sz_m))
        er = clamp(self.energy / self.max_energy, 0, 1)
        if lin_mode and lin_reg and self.lineage_id in lin_reg:
            base = lin_reg[self.lineage_id].color
        else:
            base = self.display_color
        # Taxonomy tint: blend base color with taxonomy color
        tax_col = TAXON_COLORS.get(self.taxonomy, base)
        base = lerpc(base, tax_col, 0.15)
        if self.stage == STAGE_EGG:
            color = lerpc((60, 60, 50), base, 0.5)
        elif self.stage == STAGE_JUV:
            color = lerpc((80, 180, 100), base, 0.7)
        elif self.stage == STAGE_ELDER:
            color = lerpc(base, (200, 180, 140), 0.3)
        else:
            color = lerpc((50,50,50), base, er)
        if self.state == S_SLEEP: color = lerpc(color, (100,100,180), 0.4)
        elif self.state == S_AMBUSH: color = lerpc(color, (80,80,80), 0.5)
        elif self.state == S_FRENZY: color = lerpc(color, (255,200,50), 0.3)
        elif self.state == S_MOB: color = lerpc(color, (255,255,100), 0.2)
        elif self.state == S_PLAY: color = lerpc(color, (180,255,180), 0.2)
        elif self.state == S_PARASITE: color = lerpc(color, (255,100,255), 0.3)
        elif self.state == S_BASK: color = lerpc(color, (255, 220, 100), 0.25)
        elif self.state == S_SPORE: color = lerpc(color, (220, 180, 255), 0.3)
        if self.diseased: color = lerpc(color, (180,50,220), 0.3)
        if self.is_alpha:
            pygame.draw.circle(srf, (255, 215, 0), (int(self.x), int(self.y)), r+2, 2)
        if self.stage == STAGE_EGG:
            egg_rect = pygame.Rect(int(self.x)-r, int(self.y)-int(r*1.3), r*2, int(r*2.6))
            pygame.draw.ellipse(srf, color, egg_rect)
            pygame.draw.ellipse(srf, lerpc(color, WHITE, 0.3), egg_rect, 1)
            if self.age % 20 < 3: self.x += random.uniform(-0.5, 0.5)
        else:
            # Taxonomy-specific body shapes
            if self.taxonomy == T_REPTILE and self.stage != STAGE_EGG:
                # Reptiles: slightly angular/scaled look
                pygame.draw.circle(srf, color, (int(self.x), int(self.y)), r)
                # Scale pattern: small dots around edge
                n_scales = max(4, r // 2)
                for i in range(n_scales):
                    a = (i / n_scales) * math.pi * 2
                    sx = int(self.x + math.cos(a) * (r - 1))
                    sy = int(self.y + math.sin(a) * (r - 1))
                    pygame.draw.circle(srf, lerpc(color, (100, 180, 100), 0.3), (sx, sy), 1)
            elif self.taxonomy == T_MAMMAL and self.stage != STAGE_EGG:
                # Mammals: fuzzy outline
                pygame.draw.circle(srf, color, (int(self.x), int(self.y)), r)
                # Fur effect: slightly larger, semi-transparent ring
                if r > 3:
                    fs = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
                    pygame.draw.circle(fs, (*lerpc(color, (200, 180, 150), 0.3), 40), (r*2, r*2), r+2, 2)
                    srf.blit(fs, (int(self.x)-r*2, int(self.y)-r*2))
            elif self.taxonomy == T_FUNGI and self.stage != STAGE_EGG:
                # Fungi: irregular shape with small protrusions
                pygame.draw.circle(srf, color, (int(self.x), int(self.y)), r)
                # Mycelium tendrils
                for i in range(3):
                    a = (i / 3) * math.pi * 2 + self.age * 0.02
                    ex = int(self.x + math.cos(a) * (r + 4))
                    ey = int(self.y + math.sin(a) * (r + 4))
                    pygame.draw.line(srf, lerpc(color, WHITE, 0.2),
                                     (int(self.x + math.cos(a)*r), int(self.y + math.sin(a)*r)),
                                     (ex, ey), 1)
            else:
                pygame.draw.circle(srf, color, (int(self.x), int(self.y)), r)
        # Armor ring
        arm = self.eff_trait("armor")
        if arm > 0.2 and self.stage != STAGE_EGG:
            aa = int(clamp(arm * 80, 0, 60))
            as_ = pygame.Surface((r*4,r*4), pygame.SRCALPHA)
            pygame.draw.circle(as_, (200,200,220,aa), (r*2,r*2), r+2, 2)
            srf.blit(as_, (int(self.x)-r*2, int(self.y)-r*2))
        # Camouflage shimmer
        cam = self.eff_trait("camouflage")
        if cam > 0.3 and self.stage != STAGE_EGG:
            cs = pygame.Surface((r*4,r*4), pygame.SRCALPHA)
            ca = int(cam * 40)
            pygame.draw.circle(cs, (*DARK_BG, ca), (r*2, r*2), r+1)
            srf.blit(cs, (int(self.x)-r*2, int(self.y)-r*2))
        # Toxicity ring
        if self.eff_trait("toxicity") > 0.3 and self.stage != STAGE_EGG:
            ta = int(clamp(self.eff_trait("toxicity")*100, 0, 80))
            ts = pygame.Surface((r*4,r*4), pygame.SRCALPHA)
            pygame.draw.circle(ts, (200,255,50,ta), (r*2,r*2), r+3, 2)
            srf.blit(ts, (int(self.x)-r*2, int(self.y)-r*2))
        if self.stage != STAGE_EGG:
            outline = lerpc(color, WHITE, 0.25)
            pygame.draw.circle(srf, outline, (int(self.x), int(self.y)), r, 1)
            mag = math.hypot(self.vx, self.vy)
            if mag > 0.1:
                dx=self.vx/mag*(r+3); dy=self.vy/mag*(r+3)
                pygame.draw.line(srf, outline, (int(self.x),int(self.y)), (int(self.x+dx),int(self.y+dy)), 1)
        if self.alarm > 0.5:
            pygame.draw.circle(srf, (255,255,100), (int(self.x+r+2), int(self.y-r-2)), 3)
        if self.stage == STAGE_JUV:
            pygame.draw.circle(srf, (140,220,140), (int(self.x-r-3), int(self.y-r-3)), 2)
        elif self.stage == STAGE_ELDER:
            pygame.draw.circle(srf, (220,200,140), (int(self.x-r-3), int(self.y-r-3)), 3)
            pygame.draw.circle(srf, (255,255,255), (int(self.x-r-3), int(self.y-r-3)), 3, 1)
        if self.state == S_COURT:
            pulse = 0.5 + 0.5*math.sin(self.age*0.15)
            cr = int(r+5+pulse*4)
            cs = pygame.Surface((cr*2,cr*2), pygame.SRCALPHA)
            pygame.draw.circle(cs, (255,180,220,int(50*pulse)), (cr,cr), cr, 2)
            srf.blit(cs, (int(self.x)-cr, int(self.y)-cr))
        if self.is_alpha and self.stage == STAGE_ADULT:
            pts = [(int(self.x-4), int(self.y-r-6)), (int(self.x), int(self.y-r-10)),
                   (int(self.x+4), int(self.y-r-6))]
            pygame.draw.polygon(srf, (255, 215, 0), pts)
            pygame.draw.polygon(srf, (200, 170, 0), pts, 1)
        if self.state == S_PLAY:
            pygame.draw.circle(srf, (180,255,180), (int(self.x), int(self.y-r-5)), 2)
        # Parasite indicator
        if self.parasite_host is not None:
            pygame.draw.circle(srf, (255,100,255), (int(self.x), int(self.y)), r+4, 1)

# ─── Prey (herbivore-omnivore spectrum) ───────────────────────────────────────
class Prey(Creature):
    def __init__(self, x, y, genome=None, parent_ids=(), lineage_id=0, lineage_depth=0, stage=STAGE_JUV):
        g = genome or Genome(speed=2.0, size=5.0, perception=80.0, efficiency=1.0,
            aggression=0.5, sociability=0.3, hue=random.uniform(160,220),
            lifespan=3000, fertility=0.5, toxicity=0.0, mutation_rate=0.25,
            armor=0.05, camouflage=0.1, intelligence=0.3, regeneration=0.05, diet_pref=0.05)
        super().__init__(x, y, g, energy=100, base_color=PREY_C, species_name="prey")
        self.max_energy = 100; self.parent_ids = parent_ids
        self.lineage_id = lineage_id; self.lineage_depth = lineage_depth
        self.stage = stage; self.egg_hatch_time = random.randint(80, 200) if stage == STAGE_EGG else 0
        self.migration_target = None
        # Assign taxonomy: prey are 50% mammal, 50% reptile
        if genome is not None and hasattr(genome, '_taxonomy'):
            self.taxonomy = genome._taxonomy
        else:
            self.taxonomy = random.choice([T_MAMMAL, T_REPTILE])
        # Mammal prey have slightly higher energy capacity
        if self.taxonomy == T_MAMMAL:
            self.max_energy = 110
            if genome is None:
                self.genome.sociability = clamp(self.genome.sociability + 0.1, 0, 1)
        elif self.taxonomy == T_REPTILE:
            self.max_energy = 90
            if genome is None:
                self.genome.armor = clamp(self.genome.armor + 0.1, 0, 1)
                self.genome.camouflage = clamp(self.genome.camouflage + 0.1, 0, 1)

    @property
    def reproduction_threshold(self):
        return 100 - self.eff_trait("fertility")*45

    def update(self, plants, predators, prey_list, corpses, nests, fertile_zones,
               sw, sh, season, particles, elog, grid=None):
        evts = []
        if self.stage == STAGE_EGG:
            sem = self.season_energy_mult(season)
            # Reptile eggs develop slower in cold
            if self.taxonomy == T_REPTILE and season == "Winter":
                sem *= 1.3  # higher energy drain for cold eggs
            self.move(sw, sh, 0.3*sem)
            if self.energy <= 0: self.alive = False; evts.append(("egg_death",))
            return None, evts
        self.apply_adaptation()
        if self.diseased:
            self.disease_timer -= 1; self.energy -= 0.08
            if self.disease_timer <= 0: self.diseased = False; self.disease_immune = 300
            elif random.random() < 0.002: self.alive = False; evts.append(("disease_death",)); return None, evts

        # Parasite drain
        if self.parasite_host is not None:
            self.energy -= self.parasite_energy_drain
            if self.energy < self.max_energy * 0.1:
                self.parasite_host = None; self.parasite_energy_drain = 0

        dp = self.eff_trait("diet_pref")
        intel = self.eff_trait("intelligence")
        perc = self.eff_trait("perception")

        if self.state == S_SLEEP:
            self.update_sleep(particles)
            self.move(sw, sh, 0.15*self.season_energy_mult(season))
            return self._chk_death(season, evts), evts

        # --- BASK (reptile prey) ---
        if self.state == S_BASK:
            self.update_bask(season, particles)
            self.move(sw, sh, 0.1*self.season_energy_mult(season))
            return self._chk_death(season, evts), evts

        # --- MIGRATE ---
        if self.state == S_MIGRATE:
            if self.migration_target:
                self.steer_to(*self.migration_target, 0.6)
                if dst(self.x, self.y, *self.migration_target) < 30:
                    self.state = S_WANDER; self.migration_target = None
            else:
                self.state = S_WANDER
            self.state_timer -= 1
            if self.state_timer <= 0: self.state = S_WANDER

        # --- FLEE ---
        elif self.state == S_FLEE:
            self.exp_flee += 1
            self.state_timer -= 1
            self.wander_ang += random.gauss(0, 0.3)
            self.vx += math.cos(self.wander_ang)*0.2; self.vy += math.sin(self.wander_ang)*0.2
            self._norm_vel()
            if self.state_timer <= 0 or self.alarm < 0.1: self.state = S_WANDER

        # --- MOB ---
        elif self.state == S_MOB:
            self.state_timer -= 1
            self.exp_fight += 1
            if self.state_timer <= 0: self.state = S_WANDER

        # --- FORAGE (plants) ---
        elif self.state == S_FORAGE:
            self.state_timer -= 1
            self.vx *= 0.8; self.vy *= 0.8
            if self.state_timer <= 0: self.state = S_WANDER

        # --- EAT ---
        elif self.state == S_EAT:
            self.state_timer -= 1; self.vx*=0.8; self.vy*=0.8
            if self.state_timer <= 0: self.state = S_WANDER

        # --- COURT ---
        elif self.state == S_COURT:
            self.vx*=0.9; self.vy*=0.9; self.state_timer -= 1
            if self.state_timer <= 0: self.state = S_WANDER

        # --- WANDER ---
        elif self.state == S_WANDER:
            # Check for nearby plants (diet: herbivore side)
            plant_eff = 1.0 - dp * 0.7  # 0.3 to 1.0 plant efficiency
            if plant_eff > 0.3:
                best_p, best_pd = None, float("inf")
                for p in plants:
                    d = dst(self.x, self.y, p.x, p.y)
                    if d < perc * (0.7 + intel*0.3) and d < best_pd:
                        best_pd, best_p = d, p
                if best_p and self.energy < self.max_energy * 0.85:
                    self.steer_to(best_p.x, best_p.y, 0.5)
                    if best_pd < self.eff_trait("size") + best_p.radius:
                        gain = best_p.energy * plant_eff * self.eff_trait("efficiency") * 0.7
                        self.energy = min(self.max_energy, self.energy + gain)
                        self.exp_eat_plant += 1
                        # Toxic plant penalty
                        if hasattr(best_p, 'toxicity') and best_p.toxicity:
                            self.energy -= 8
                            if random.random() < 0.2:
                                self.diseased = True
                                self.disease_timer = random.randint(50, 150)
                        best_p.energy = 0
                        self.state = S_FORAGE; self.state_timer = 10

            # Cross-diet: scavenge if carnivore-leaning
            if dp > 0.5 and self.energy < self.max_energy * 0.5:
                self.try_scavenge(corpses)

            # Check predators using grid
            flee = False
            if grid:
                nearby_preds = query_grid(grid, self.x, self.y, perc)
                for pred in nearby_preds:
                    if pred.species_name != "predator" or not pred.alive: continue
                    d = dst(self.x, self.y, pred.x, pred.y)
                    camo_bonus = self.eff_trait("camouflage") * 20
                    eff_perc = perc * (0.8 + intel*0.2) + camo_bonus
                    if d < eff_perc:
                        self.alarm = min(1.0, self.alarm + 0.3)
                        self.steer_away(pred.x, pred.y, 0.7)
                        self.state = S_FLEE; self.state_timer = random.randint(30, 80)
                        self.emit_alarm([o for o in query_grid(grid, self.x, self.y, perc*0.8)
                                         if o.species_name == "prey" and o.alive])
                        flee = True
                        # Mob behavior if sociable
                        if self.eff_trait("sociability") > 0.5:
                            neighbors = [o for o in query_grid(grid, self.x, self.y, perc*0.6)
                                         if o.species_name == "prey" and o.alive and o.id != self.id]
                            if len(neighbors) >= 3:
                                self.state = S_MOB; self.state_timer = random.randint(40, 100)
                                for o in neighbors[:5]:
                                    if o.state in (S_WANDER, S_FLEE):
                                        o.state = S_MOB; o.state_timer = self.state_timer
                                evts.append(("mob_formed", len(neighbors)+1))
                                flee = False
                        break
            if not flee:
                # Migration in winter
                if season == "Winter" and self.energy < self.max_energy*0.4 and random.random() < 0.01:
                    self.migration_target = (random.uniform(100,SW-100), random.uniform(100,SH-100))
                    self.state = S_MIGRATE; self.state_timer = random.randint(100,300)
                    evts.append(("migration", 1))
                else:
                    # Reptile basking behavior
                    if not self.try_bask(season, particles):
                        self.wander()
                    self.try_sleep(particles)

        if self.state not in (S_FLEE, S_MOB, S_FRENZY, S_SLEEP, S_AMBUSH, S_MIGRATE, S_PLAY):
            if grid:
                near_prey = [o for o in query_grid(grid, self.x, self.y, perc*0.6)
                             if o.species_name == "prey" and o.alive]
                self.flock(near_prey)
                self.territorial_check(near_prey, particles)
                self.play_behavior([o for o in near_prey if o.stage == STAGE_JUV], particles)

        self.move(sw, sh, self.season_energy_mult(season))

        # Nest protection
        in_nest = False
        for n in nests:
            if dst(self.x, self.y, n.x, n.y) < 20: in_nest = True; break
        if in_nest and self.stage == STAGE_JUV:
            self.energy = min(self.max_energy, self.energy + 0.02)

        r = self._chk_death(season, evts)
        if r is not None: return r, evts

        if self.stage != STAGE_ADULT: return None, evts
        cd = max(60, int(180-self.eff_trait("fertility")*120))
        if (self.energy > self.reproduction_threshold and self.repro_cd <= 0
                and self.state not in (S_FLEE, S_MOB, S_FRENZY, S_SLEEP)):
            if grid:
                candidates = [o for o in query_grid(grid, self.x, self.y, perc*0.4)
                              if o.species_name == "prey" and o.alive and o.stage == STAGE_ADULT]
            else:
                candidates = prey_list
            mate = self._find_mate(candidates)
            if mate:
                self.state = S_COURT; self.state_timer = 20; mate.state = S_COURT; mate.state_timer = 20
                cg = Genome.crossover(self.genome, mate.genome)
                self.energy *= 0.4; mate.energy *= 0.4; mate.repro_cd = cd
                pids = (self.id, mate.id); mate.children_count += 1
                evts.append(("birth", "prey", "sexual", self.lineage_id))
                mx, my = (self.x+mate.x)/2, (self.y+mate.y)/2
                for _ in range(5):
                    particles.append(Particle(mx, my, random.uniform(-1,1), random.uniform(-1,1), random.randint(15,30), (255,180,220), 2))
            else:
                cg = self.genome.mutate(); self.energy *= 0.5; pids = (self.id,)
                evts.append(("birth", "prey", "asexual", self.lineage_id))
            self.repro_cd = cd; self.children_count += 1
            cx = clamp(self.x+random.uniform(-15,15), 10, sw-10)
            cy = clamp(self.y+random.uniform(-15,15), 10, sh-10)
            lid = self.lineage_id or self.id
            # Mammals: live birth (juvenile). Reptiles: egg-laying.
            if self.taxonomy == T_MAMMAL:
                birth_stage = STAGE_JUV
                child_energy = 45
                cg._taxonomy = T_MAMMAL  # pass taxonomy to child
            else:
                birth_stage = STAGE_EGG
                child_energy = 30
                cg._taxonomy = T_REPTILE
                # Reptile eggs take longer in cold seasons
                if season == "Winter": child_energy = 25
            child = Prey(cx, cy, genome=cg, parent_ids=pids, lineage_id=lid,
                         lineage_depth=self.lineage_depth+1, stage=birth_stage)
            child.energy = child_energy
            child.taxonomy = self.taxonomy  # inherit taxonomy
            # Mammal nursing: parent provides extra care
            if self.eff_trait("sociability") > 0.5:
                self.state = S_PARENT; self.state_timer = random.randint(60,150); self.protecting = child
            return child, evts
        return None, evts

    def _chk_death(self, season, evts):
        if self.age > self.eff_trait("lifespan"): self.alive = False; evts.append(("old_age","prey",self.id)); return "corpse"
        if self.energy <= 0: self.alive = False; evts.append(("starvation","prey",self.id)); return "corpse"
        return None

    def _find_mate(self, candidates):
        if self.eff_trait("sociability") < 0.2: return None
        for o in candidates:
            if o.id==self.id or not o.alive or o.stage != STAGE_ADULT: continue
            d = dst(self.x,self.y,o.x,o.y)
            if (d < self.eff_trait("perception")*0.4 and o.energy > o.reproduction_threshold*0.8
                    and o.repro_cd <= 0 and o.state not in (S_FLEE,S_MOB,S_FRENZY,S_SLEEP)
                    and abs(o.genome.hue-self.genome.hue) < 60):
                return o
        return None

# ─── Predator (carnivore-omnivore spectrum) ───────────────────────────────────
class Predator(Creature):
    def __init__(self, x, y, genome=None, parent_ids=(), lineage_id=0, lineage_depth=0, stage=STAGE_JUV):
        g = genome or Genome(speed=2.8, size=7.0, perception=120.0, efficiency=1.3,
            aggression=0.6, sociability=0.2, hue=random.uniform(0,30),
            lifespan=3500, fertility=0.4, toxicity=0.0, mutation_rate=0.25,
            armor=0.1, camouflage=0.05, intelligence=0.4, regeneration=0.02, diet_pref=0.9)
        super().__init__(x, y, g, energy=140, base_color=PRED_C, species_name="predator")
        self.max_energy = 140; self.hunt_cd = 0; self.parent_ids = parent_ids
        self.lineage_id = lineage_id; self.lineage_depth = lineage_depth
        self.stage = stage; self.egg_hatch_time = random.randint(100, 250) if stage == STAGE_EGG else 0
        self.ambush_target = None; self.ambush_timer = 0
        # Assign taxonomy: predators are 50% mammal, 50% reptile
        if genome is not None and hasattr(genome, '_taxonomy'):
            self.taxonomy = genome._taxonomy
        else:
            self.taxonomy = random.choice([T_MAMMAL, T_REPTILE])
        if self.taxonomy == T_MAMMAL:
            self.max_energy = 150
            if genome is None:
                self.genome.intelligence = clamp(self.genome.intelligence + 0.1, 0, 1)
                self.genome.sociability = clamp(self.genome.sociability + 0.05, 0, 1)
        elif self.taxonomy == T_REPTILE:
            self.max_energy = 130
            if genome is None:
                self.genome.armor = clamp(self.genome.armor + 0.15, 0, 1)
                self.genome.camouflage = clamp(self.genome.camouflage + 0.1, 0, 1)
                self.genome.speed = clamp(self.genome.speed + 0.3, 0.5, 6.0)

    @property
    def reproduction_threshold(self):
        return 140 - self.eff_trait("fertility")*50

    def update(self, prey_list, pred_list, corpses, nests, sw, sh, season, particles, elog, grid=None, plants=None):
        evts = []
        if self.stage == STAGE_EGG:
            sem = self.season_energy_mult(season)
            if self.taxonomy == T_REPTILE and season == "Winter":
                sem *= 1.3
            self.move(sw, sh, 0.3*sem)
            if self.energy <= 0: self.alive = False; evts.append(("egg_death",))
            return None, evts
        self.apply_adaptation()
        if self.diseased:
            self.disease_timer -= 1; self.energy -= 0.1
            if self.disease_timer <= 0: self.diseased = False; self.disease_immune = 300
            elif random.random() < 0.002: self.alive = False; evts.append(("disease_death",)); return None, evts

        self.dominance_score = self.eff_trait("size") * self.eff_trait("aggression") * (self.energy / self.max_energy)
        if self.stage == STAGE_ELDER: self.dominance_score *= 0.7
        elif self.stage == STAGE_JUV: self.dominance_score *= 0.3

        dp = self.eff_trait("diet_pref")
        intel = self.eff_trait("intelligence")
        perc = self.eff_trait("perception")
        armor = self.eff_trait("armor")
        self.plants_ref = plants or []

        if self.state == S_SLEEP:
            self.update_sleep(particles)
            self.move(sw, sh, 0.2*self.season_energy_mult(season))
            if self.hunt_cd > 0: self.hunt_cd -= 1
            return self._chk_death(season, evts), evts

        # --- BASK (reptile predators) ---
        if self.state == S_BASK:
            self.update_bask(season, particles)
            self.move(sw, sh, 0.1*self.season_energy_mult(season))
            if self.hunt_cd > 0: self.hunt_cd -= 1
            return self._chk_death(season, evts), evts

        if self.energy < self.max_energy*0.35: self.try_scavenge(corpses)

        # --- AMBUSH ---
        if self.state == S_AMBUSH:
            self.vx*=0.95; self.vy*=0.95; self.ambush_timer -= 1; self.energy -= 0.01
            if self.ambush_target:
                d = dst(self.x,self.y,self.ambush_target.x,self.ambush_target.y)
                if d < self.eff_trait("size") + self.ambush_target.eff_trait("size") + 5:
                    prey_armor = self.ambush_target.eff_trait("armor")
                    gain = self.ambush_target.energy*0.8*(1-self.ambush_target.eff_trait("toxicity")*0.6)*(1-prey_armor*0.2)
                    self.energy = min(self.max_energy, self.energy+gain)
                    if self.ambush_target.eff_trait("toxicity") > 0.5: self.energy -= self.ambush_target.eff_trait("toxicity")*15
                    self.ambush_target.alive = False; self.kills += 1; self.hunt_cd = 30
                    self.exp_hunt += 1
                    evts.append(("ambush_kill", self.id))
                    for _ in range(8):
                        particles.append(Particle(self.ambush_target.x, self.ambush_target.y,
                                                   random.uniform(-2,2), random.uniform(-2,2), 20, (255,100,100), 3))
                    self.ambush_target = None; self.state = S_EAT; self.state_timer = 20
                elif not self.ambush_target.alive or d > perc*1.5:
                    self.ambush_target = None; self.state = S_WANDER
            if self.ambush_timer <= 0: self.state = S_WANDER; self.ambush_target = None

        # --- PACK HUNT ---
        elif self.state == S_PACK:
            np_d, np_c = float("inf"), None
            prey_search = prey_list
            if grid:
                prey_search = query_grid(grid, self.x, self.y, perc*1.3)
            for p in prey_search:
                if p.species_name != "prey" or not p.alive: continue
                d = dst(self.x,self.y,p.x,p.y); ed = d + p.eff_trait("toxicity")*40
                if d < perc*1.3 and ed < np_d: np_d, np_c = d, p
            if np_c:
                pcx, pcy, pn = 0, 0, 0
                pred_search = pred_list
                if grid:
                    pred_search = query_grid(grid, self.x, self.y, perc)
                for o in pred_search:
                    if o.id!=self.id and o.alive and o.species_name == "predator":
                        pcx+=o.x; pcy+=o.y; pn+=1
                if pn > 0:
                    pcx/=pn; pcy/=pn
                    fa = ang(pcx, pcy, np_c.x, np_c.y)
                    self.steer_to(np_c.x+math.cos(fa+random.uniform(-0.5,0.5))*30,
                                  np_c.y+math.sin(fa+random.uniform(-0.5,0.5))*30, 0.5)
                else: self.steer_to(np_c.x, np_c.y, 0.6)
                rd = dst(self.x,self.y,np_c.x,np_c.y)
                if rd < self.eff_trait("size") + np_c.eff_trait("size"):
                    gain = np_c.energy*0.7*(1-np_c.eff_trait("toxicity")*0.6)*(1-np_c.eff_trait("armor")*0.2)
                    self.energy = min(self.max_energy, self.energy+gain)
                    np_c.alive = False; self.kills += 1; self.hunt_cd = 30
                    self.exp_hunt += 1
                    evts.append(("pack_kill", self.id, np_c.id))
                    for _ in range(6):
                        particles.append(Particle(np_c.x, np_c.y, random.uniform(-2,2), random.uniform(-2,2), 20, (255,150,50), 3))
                    self.state = S_WANDER
            else: self.state = S_WANDER

        # --- FRENZY ---
        elif self.state == S_FRENZY:
            self.state_timer -= 1; self.exp_hunt += 1
            np_d, np_c = float("inf"), None
            prey_search = prey_list
            if grid:
                prey_search = query_grid(grid, self.x, self.y, perc*1.5)
            for p in prey_search:
                if p.species_name != "prey" or not p.alive: continue
                d = dst(self.x,self.y,p.x,p.y)
                if d < perc*1.5 and d < np_d: np_d, np_c = d, p
            if np_c:
                self.steer_to(np_c.x, np_c.y, 0.9)
                if np_d < self.eff_trait("size") + np_c.eff_trait("size"):
                    self.energy = min(self.max_energy, self.energy+np_c.energy*0.6)
                    np_c.alive = False; self.kills += 1; self.hunt_cd = 20
            else: self.wander()
            mag = math.hypot(self.vx, self.vy)
            if mag > 0: self.vx=(self.vx/mag)*self.eff_trait("speed")*1.3; self.vy=(self.vy/mag)*self.eff_trait("speed")*1.3
            if self.state_timer <= 0 or self.energy > self.max_energy*0.5: self.state = S_WANDER

        # --- PLAY ---
        elif self.state == S_PLAY:
            self.state_timer -= 1
            if self.play_target and self.play_target.alive:
                d = dst(self.x,self.y,self.play_target.x,self.play_target.y)
                if d < self.eff_trait("size")*2:
                    self.play_target.state = S_PLAY; self.play_target.play_target = self
                    self.state = S_WANDER; self.play_target = None
                else: self.steer_to(self.play_target.x, self.play_target.y, 0.5)
            else: self.state = S_WANDER
            if self.state_timer <= 0: self.state = S_WANDER

        elif self.state == S_EAT:
            self.state_timer -= 1; self.vx*=0.8; self.vy*=0.8
            self.energy = min(self.max_energy, self.energy+0.2)
            if self.state_timer <= 0: self.state = S_WANDER

        elif self.state == S_COURT:
            self.vx*=0.9; self.vy*=0.9; self.state_timer -= 1
            if self.state_timer <= 0: self.state = S_WANDER

        # --- WANDER ---
        elif self.state == S_WANDER:
            # Omnivore: eat plants if diet_pref is low
            if dp < 0.5 and self.energy < self.max_energy * 0.6:
                # Predators can eat plants if they evolved that way
                plant_eff = (1.0 - dp) * 0.5 * self.eff_trait("efficiency")
                best_pp, best_ppd = None, float("inf")
                for p in self.plants_ref:
                    d = dst(self.x, self.y, p.x, p.y)
                    if d < perc * 0.5 and d < best_ppd:
                        best_ppd, best_pp = d, p
                if best_pp:
                    self.steer_to(best_pp.x, best_pp.y, 0.4)
                    if best_ppd < self.eff_trait("size") + best_pp.radius:
                        gain = best_pp.energy * plant_eff * 0.5
                        self.energy = min(self.max_energy, self.energy + gain)
                        self.exp_eat_plant += 1
                        best_pp.energy = 0
                        self.state = S_EAT; self.state_timer = 10
                else:
                    self.try_scavenge(corpses)

            if self.energy < self.max_energy*0.15 and self.eff_trait("aggression") > 0.6:
                self.state = S_FRENZY; self.state_timer = random.randint(80,200)
                evts.append(("predator_frenzy", self.id))
            elif (self.eff_trait("speed") < 3.0 and perc > 100
                  and self.hunt_cd <= 0 and random.random() < 0.005):
                prey_search = prey_list
                if grid:
                    prey_search = query_grid(grid, self.x, self.y, perc)
                for p in prey_search:
                    if p.species_name == "prey" and p.alive and dst(self.x,self.y,p.x,p.y) < perc:
                        self.state = S_AMBUSH; self.ambush_timer = random.randint(100,300)
                        self.ambush_target = p; self.vx=0; self.vy=0
                        evts.append(("ambush_start", self.id)); break
            elif self.eff_trait("sociability") > 0.4:
                nearby = []
                if grid:
                    nearby = [o for o in query_grid(grid, self.x, self.y, perc*0.6)
                              if o.species_name == "predator" and o.alive and o.id != self.id]
                if len(nearby) >= 2:
                    self.state = S_PACK
                    for o in nearby:
                        if o.state == S_WANDER: o.state = S_PACK
                    evts.append(("pack_formed", len(nearby)+1))
            else:
                hunt_p = perc*(0.8+self.eff_trait("aggression")*0.5)
                np_d, np_c = float("inf"), None
                prey_search = prey_list
                if grid:
                    prey_search = query_grid(grid, self.x, self.y, hunt_p)
                for p in prey_search:
                    if p.species_name != "prey" or not p.alive: continue
                    # Camouflage reduces detection
                    camo_penalty = p.eff_trait("camouflage") * 30
                    d = dst(self.x,self.y,p.x,p.y); ed = d + p.eff_trait("toxicity")*40 + camo_penalty
                    if d < hunt_p and ed < np_d: np_d, np_c = d, p

                # Kleptoparasitism
                if not np_c and self.eff_trait("aggression") > 0.7:
                    pred_search = pred_list
                    if grid:
                        pred_search = query_grid(grid, self.x, self.y, perc*0.5)
                    for o in pred_search:
                        if o.id != self.id and o.alive and o.species_name == "predator":
                            if o.hunt_cd > 20 and o.hunt_cd < 35:
                                if dst(self.x,self.y,o.x,o.y) < perc*0.5:
                                    if self.dominance_score > o.dominance_score * 1.3:
                                        gain = o.energy * 0.15
                                        o.energy -= gain; self.energy = min(self.max_energy, self.energy + gain)
                                        o.steer_away(self.x, self.y, 0.6)
                                        evts.append(("klepto", self.id, o.id))
                                        for _ in range(3):
                                            particles.append(Particle((self.x+o.x)/2,(self.y+o.y)/2,
                                                                       random.uniform(-1,1),random.uniform(-1,1), 12, (255,220,100), 2))
                                        break

                if np_c:
                    self.steer_to(np_c.x, np_c.y, 0.5+self.eff_trait("aggression")*0.3)
                    if np_d < perc*0.5:
                        mag = math.hypot(self.vx, self.vy)
                        if mag > 0: self.vx=(self.vx/mag)*self.eff_trait("speed")*1.2; self.vy=(self.vy/mag)*self.eff_trait("speed")*1.2
                    if np_d < self.eff_trait("size") + np_c.eff_trait("size"):
                        prey_armor = np_c.eff_trait("armor")
                        gain = np_c.energy*0.7*(1-np_c.eff_trait("toxicity")*0.6)*(1-prey_armor*0.2)
                        self.energy = min(self.max_energy, self.energy+gain)
                        if np_c.eff_trait("toxicity") > 0.5: self.energy -= np_c.eff_trait("toxicity")*15
                        np_c.alive = False; self.kills += 1; self.hunt_cd = 30
                        self.exp_hunt += 1
                        evts.append(("kill", self.id, np_c.id))
                        for _ in range(6):
                            particles.append(Particle(np_c.x, np_c.y, random.uniform(-2,2), random.uniform(-2,2), 20, (255,100,100), 3))
                        self.state = S_EAT; self.state_timer = 20
                else: self.wander()

            # Reptile basking
            if not self.try_bask(season, particles):
                self.try_sleep(particles)
            if self.stage == STAGE_JUV:
                juvs = [o for o in (pred_list if not grid else query_grid(grid, self.x, self.y, perc))
                        if o.species_name == "predator" and o.stage == STAGE_JUV]
                self.play_behavior(juvs, particles)

        if self.state in (S_WANDER,):
            if grid:
                near_preds = [o for o in query_grid(grid, self.x, self.y, perc)
                              if o.species_name == "predator" and o.alive]
                self.flock(near_preds)
                self.territorial_check(near_preds, particles)

        # Alpha check
        self.is_alpha = False
        if self.stage == STAGE_ADULT:
            if grid:
                competitors = [o for o in query_grid(grid, self.x, self.y, perc*0.8)
                               if o.species_name == "predator" and o.alive and o.stage == STAGE_ADULT and o.id != self.id]
                self.is_alpha = all(self.dominance_score >= o.dominance_score for o in competitors)
            else:
                found_competitor = False
                for o in pred_list:
                    if o.id != self.id and o.alive and o.stage == STAGE_ADULT:
                        if dst(self.x,self.y,o.x,o.y) < perc*0.8:
                            found_competitor = True
                            if o.dominance_score > self.dominance_score:
                                self.is_alpha = False; break
                if not found_competitor:
                    self.is_alpha = True

        self.move(sw, sh, self.season_energy_mult(season))
        if self.hunt_cd > 0: self.hunt_cd -= 1

        r = self._chk_death(season, evts)
        if r is not None: return r, evts

        if self.stage != STAGE_ADULT: return None, evts
        cd = max(100, int(280-self.eff_trait("fertility")*160))
        if (self.energy > self.reproduction_threshold and self.repro_cd <= 0
                and self.age > 80 and self.state == S_WANDER):
            if grid:
                candidates = [o for o in query_grid(grid, self.x, self.y, perc*0.4)
                              if o.species_name == "predator" and o.alive and o.stage == STAGE_ADULT]
            else:
                candidates = pred_list
            mate = self._find_mate(candidates)
            if mate:
                self.state=S_COURT; self.state_timer=20; mate.state=S_COURT; mate.state_timer=20
                cg = Genome.crossover(self.genome, mate.genome)
                self.energy*=0.4; mate.energy*=0.4; mate.repro_cd=cd
                pids=(self.id, mate.id); mate.children_count+=1
                evts.append(("birth","predator","sexual",self.lineage_id))
                mx, my = (self.x+mate.x)/2, (self.y+mate.y)/2
                for _ in range(5):
                    particles.append(Particle(mx,my,random.uniform(-1,1),random.uniform(-1,1),random.randint(15,30),(255,150,180),2))
            else:
                cg = self.genome.mutate(); self.energy*=0.5; pids=(self.id,)
                evts.append(("birth","predator","asexual",self.lineage_id))
            self.repro_cd=cd; self.children_count+=1
            cx=clamp(self.x+random.uniform(-20,20),10,sw-10); cy=clamp(self.y+random.uniform(-20,20),10,sh-10)
            lid = self.lineage_id or self.id
            # Mammals: live birth. Reptiles: egg-laying.
            if self.taxonomy == T_MAMMAL:
                birth_stage = STAGE_JUV
                child_energy = 55
                cg._taxonomy = T_MAMMAL
            else:
                birth_stage = STAGE_EGG
                child_energy = 40
                cg._taxonomy = T_REPTILE
            child = Predator(cx, cy, genome=cg, parent_ids=pids, lineage_id=lid,
                             lineage_depth=self.lineage_depth+1, stage=birth_stage)
            child.energy = child_energy
            child.taxonomy = self.taxonomy
            return child, evts
        return None, evts

    def _chk_death(self, season, evts):
        if self.age > self.eff_trait("lifespan"): self.alive=False; evts.append(("old_age","predator",self.id)); return "corpse"
        if self.energy <= 0: self.alive=False; evts.append(("starvation","predator",self.id)); return "corpse"
        return None

    def _find_mate(self, candidates):
        if self.eff_trait("sociability") < 0.15: return None
        for o in candidates:
            if o.id==self.id or not o.alive or o.stage != STAGE_ADULT: continue
            d = dst(self.x,self.y,o.x,o.y)
            if (d < self.eff_trait("perception")*0.4 and o.energy > o.reproduction_threshold*0.8
                    and o.repro_cd <= 0 and o.state == S_WANDER
                    and abs(o.genome.hue-self.genome.hue) < 60):
                return o
        return None

# ─── Decomposer (scavenger/parasite spectrum) ─────────────────────────────────
class Decomposer(Creature):
    def __init__(self, x, y, genome=None, parent_ids=(), lineage_id=0, lineage_depth=0, stage=STAGE_JUV):
        g = genome or Genome(speed=1.5, size=4.0, perception=100.0, efficiency=0.7,
            aggression=0.1, sociability=0.4, hue=random.uniform(260, 310),
            lifespan=2500, fertility=0.6, toxicity=0.0, mutation_rate=0.3,
            armor=0.0, camouflage=0.15, intelligence=0.2, regeneration=0.1, diet_pref=0.3)
        super().__init__(x, y, g, energy=80, base_color=DECOMP_C, species_name="decomposer")
        self.max_energy = 80; self.parent_ids = parent_ids
        self.lineage_id = lineage_id; self.lineage_depth = lineage_depth
        self.stage = stage; self.egg_hatch_time = random.randint(60, 150) if stage == STAGE_EGG else 0
        self.parasite_target = None
        self.parasite_timer = 0
        # All decomposers are fungi
        self.taxonomy = T_FUNGI
        if genome is None:
            self.genome.toxicity = clamp(self.genome.toxicity + 0.15, 0, 1)
            self.genome.regeneration = clamp(self.genome.regeneration + 0.1, 0, 1)

    @property
    def reproduction_threshold(self):
        return 80 - self.eff_trait("fertility")*35

    def update(self, corpses, decomp_list, fertile_zones, all_creatures,
               sw, sh, season, particles, elog, grid=None):
        evts = []
        if self.stage == STAGE_EGG:
            self.move(sw, sh, 0.2*self.season_energy_mult(season))
            if self.energy <= 0: self.alive = False; evts.append(("egg_death",))
            return None, evts
        self.apply_adaptation()
        if self.diseased:
            self.disease_timer -= 1; self.energy -= 0.06
            if self.disease_timer <= 0: self.diseased = False; self.disease_immune = 200
            elif random.random() < 0.002: self.alive = False; evts.append(("disease_death",)); return None, evts

        # Fungi spore cooldown
        if self.spore_cooldown > 0: self.spore_cooldown -= 1
        perc = self.eff_trait("perception")
        intel = self.eff_trait("intelligence")
        agg = self.eff_trait("aggression")

        if self.state == S_SLEEP:
            self.update_sleep(particles)
            self.move(sw, sh, 0.15*self.season_energy_mult(season))
            return self._chk_death(evts), evts

        # --- SPORE (fungi spore release) ---
        if self.state == S_SPORE:
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = S_WANDER
            if self.state_timer % 10 == 0:
                particles.append(Particle(
                    self.x + random.uniform(-5, 5), self.y + random.uniform(-5, 5),
                    random.uniform(-1.5, 1.5), random.uniform(-1.5, 0.5),
                    random.randint(40, 80), (200, 160, 255), 2))

        if self.stage == STAGE_JUV and random.random() < 0.008:
            juvs = [o for o in decomp_list if o.stage==STAGE_JUV]
            self.play_behavior(juvs, particles)

        # --- PARASITE (high-aggression decomposers) ---
        if agg > 0.5 and self.state == S_PARASITE:
            self.parasite_timer -= 1
            if self.parasite_target and self.parasite_target.alive:
                d = dst(self.x, self.y, self.parasite_target.x, self.parasite_target.y)
                if d > perc:
                    self.parasite_target = None; self.state = S_WANDER
                else:
                    self.steer_to(self.parasite_target.x, self.parasite_target.y, 0.4)
                    if d < self.eff_trait("size") + self.parasite_target.eff_trait("size") + 3:
                        # Attach as parasite
                        drain = 0.15 * (1 - self.parasite_target.eff_trait("armor") * 0.5)
                        drain = max(0.02, drain)
                        self.parasite_target.parasite_host = self
                        self.parasite_target.parasite_energy_drain = drain
                        gain = drain * 0.8 * self.eff_trait("efficiency")
                        self.energy = min(self.max_energy, self.energy + gain)
                        self.exp_eat_meat += 1
                        self.vx *= 0.5; self.vy *= 0.5
                        if random.random() < 0.005 * (1 - self.parasite_target.eff_trait("armor")):
                            self.parasite_target.diseased = True
                            self.parasite_target.disease_timer = random.randint(80, 200)
            if self.parasite_timer <= 0:
                self.parasite_target = None; self.state = S_WANDER

        # --- DECOMPOSE ---
        elif self.state == S_DECOMPOSE or self.state == S_WANDER:
            best_c, best_d = None, float("inf")
            for c in corpses:
                d = dst(self.x,self.y,c.x,c.y)
                if d < perc and d < best_d: best_d, best_c = d, c

            # Fungi: absorb energy from fertile zones more efficiently
            for fz in fertile_zones:
                if dst(self.x, self.y, fz.x, fz.y) < fz.radius:
                    self.energy = min(self.max_energy, self.energy + 0.03 * fz.strength)

            # Parasitism: switch to parasite mode if aggressive and near a living creature
            if agg > 0.5 and not best_c and random.random() < 0.02:
                if grid:
                    targets = query_grid(grid, self.x, self.y, perc)
                else:
                    targets = all_creatures
                for t in targets:
                    if (t.alive and t.species_name != "decomposer" and t.stage != STAGE_EGG
                            and t.parasite_host is None and dst(self.x, self.y, t.x, t.y) < perc):
                        self.parasite_target = t; self.state = S_PARASITE
                        self.parasite_timer = random.randint(100, 300)
                        break

            if best_c:
                self.state = S_DECOMPOSE
                self.steer_to(best_c.x, best_c.y, 0.5)
                if best_d < self.eff_trait("size") + best_c.radius + 5:
                    gain = best_c.energy * 0.6 * self.eff_trait("efficiency")
                    self.energy = min(self.max_energy, self.energy + gain)
                    self.exp_eat_meat += 1
                    if random.random() < 0.3:
                        fertile_zones.append(FertileZone(best_c.x, best_c.y,
                                                          radius=random.uniform(40,80),
                                                          strength=random.uniform(1.2,2.0)))
                    best_c.energy = 0
                    for _ in range(4):
                        particles.append(Particle(best_c.x, best_c.y, random.uniform(-0.5,0.5),
                                                   random.uniform(-1,0), 20, (200,140,255), 2))
            else:
                self.state = S_WANDER; self.wander()

        if grid:
            near_decomp = [o for o in query_grid(grid, self.x, self.y, perc*0.6)
                           if o.species_name == "decomposer" and o.alive]
            self.flock(near_decomp)
            self.territorial_check(near_decomp, particles)
        else:
            self.flock(decomp_list)
            self.territorial_check(decomp_list, particles)

        # Mycelium network: fungi near each other share small energy
        if grid:
            near_fungi = [o for o in query_grid(grid, self.x, self.y, perc*0.5)
                          if o.species_name == "decomposer" and o.alive and o.id != self.id]
            if near_fungi:
                avg_e = sum(o.energy for o in near_fungi) / len(near_fungi)
                if self.energy < avg_e:
                    self.energy = min(self.max_energy, self.energy + 0.05 * (avg_e - self.energy))
                elif self.energy > avg_e * 1.5:
                    self.energy -= 0.02  # contribute to network

        self.move(sw, sh, self.season_energy_mult(season))

        r = self._chk_death(evts)
        if r is not None: return r, evts

        if self.stage != STAGE_ADULT: return None, evts
        cd = max(50, int(150-self.eff_trait("fertility")*100))
        if (self.energy > self.reproduction_threshold and self.repro_cd <= 0
                and self.state in (S_WANDER, S_DECOMPOSE)):
            mate = None
            if self.eff_trait("sociability") > 0.2:
                for o in decomp_list:
                    if o.id==self.id or not o.alive or o.stage != STAGE_ADULT: continue
                    d = dst(self.x,self.y,o.x,o.y)
                    if (d < self.eff_trait("perception")*0.4 and o.energy > o.reproduction_threshold*0.8
                            and o.repro_cd <= 0 and abs(o.genome.hue-self.genome.hue) < 60):
                        mate = o; break
            if mate:
                cg = Genome.crossover(self.genome, mate.genome)
                self.energy*=0.4; mate.energy*=0.4; mate.repro_cd=cd
                pids=(self.id, mate.id); mate.children_count+=1
            else:
                cg = self.genome.mutate(); self.energy*=0.5; pids=(self.id,)
            self.repro_cd=cd; self.children_count+=1
            cx=clamp(self.x+random.uniform(-10,10),10,sw-10); cy=clamp(self.y+random.uniform(-10,10),10,sh-10)
            lid = self.lineage_id or self.id
            # Fungi: spore reproduction (spread further than normal birth)
            if self.spore_cooldown <= 0 and self.eff_trait("sociability") > 0.3:
                cx = clamp(self.x + random.uniform(-80, 80), 10, sw-10)
                cy = clamp(self.y + random.uniform(-80, 80), 10, sh-10)
                self.spore_cooldown = 60
                self.state = S_SPORE; self.state_timer = 30
                for _ in range(4):
                    particles.append(Particle(self.x, self.y,
                                               random.uniform(-2, 2), random.uniform(-2, 1),
                                               random.randint(30, 60), (200, 160, 255), 2))
            cg._taxonomy = T_FUNGI
            child = Decomposer(cx, cy, genome=cg, parent_ids=pids, lineage_id=lid,
                               lineage_depth=self.lineage_depth+1, stage=STAGE_EGG)
            child.energy = 25
            child.taxonomy = T_FUNGI
            return child, evts
        return None, evts

    def _chk_death(self, evts):
        if self.age > self.eff_trait("lifespan"): self.alive = False; evts.append(("old_age","decomposer",self.id)); return "corpse"
        if self.energy <= 0: self.alive = False; evts.append(("starvation","decomposer",self.id)); return "corpse"
        return None

# ─── Simulation ───────────────────────────────────────────────────────────────
class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCR_W, SCR_H))
        pygame.display.set_caption("Artificial Life v5 — Taxonomy & Evolution")
        self.clock = pygame.time.Clock()
        self.ft = pygame.font.SysFont("consolas", 11)
        self.fs = pygame.font.SysFont("consolas", 13)
        self.fm = pygame.font.SysFont("consolas", 15)
        self.fl = pygame.font.SysFont("consolas", 19, bold=True)
        self.fT = pygame.font.SysFont("consolas", 22, bold=True)
        self.sim_srf = pygame.Surface((SW, SH))
        self.running = True; self.paused = False; self.show_grid = False
        self.speed_mult = 1; self.food_mode = 1; self.tick = 0; self.total_births = 0
        self.active_tab = 0
        self.tab_names = ["STATS","TRAITS","LINEAGES","SPECIES","EVENTS"]
        self.lin_mode = False; self.selected = None
        self.hist_prey=[]; self.hist_pred=[]; self.hist_decomp=[]; self.hist_plant=[]
        self.hist_max = 300
        self.lin_reg: Dict[int, Lineage] = {}
        self.elog = EventLog()
        self.particles: List[Particle] = []
        self.corpses: List[Corpse] = []
        self.diseases: List[DiseaseOutbreak] = []
        self.disasters: List[Disaster] = []
        self.fertile_zones: List[FertileZone] = []
        self.nests: List[Nest] = []
        self.season_idx = 0; self.season_tick = 0
        self._miles = {}
        # Species system
        self.species_records: Dict[int, SpeciesRecord] = {}
        self._next_sid = 0
        self._species_rebuild_cd = 0
        self.reset()

    @property
    def season(self): return SEASONS[self.season_idx % 4]

    def reset(self):
        rst_id(); self.tick=0; self.total_births=0
        self.prey_list=[]; self.pred_list=[]; self.decomp_list=[]; self.plants=[]
        self.lin_reg.clear(); self.selected=None
        self.particles.clear(); self.corpses.clear(); self.diseases.clear()
        self.disasters.clear(); self.fertile_zones.clear(); self.nests.clear()
        self.elog = EventLog(); self.season_idx=0; self.season_tick=0; self._miles.clear()
        self.hist_prey.clear(); self.hist_pred.clear(); self.hist_decomp.clear(); self.hist_plant.clear()
        self.species_records.clear(); self._next_sid = 0; self._species_rebuild_cd = 0
        m = 20
        for _ in range(INIT_PREY):
            p = Prey(random.uniform(m,SW-m), random.uniform(m,SH-m))
            p.lineage_id=p.id; self.lin_reg[p.id]=Lineage(p.id,p.genome.hue,"prey"); self.prey_list.append(p)
        for _ in range(INIT_PRED):
            p = Predator(random.uniform(m,SW-m), random.uniform(m,SH-m))
            p.lineage_id=p.id; self.lin_reg[p.id]=Lineage(p.id,p.genome.hue,"predator"); self.pred_list.append(p)
        for _ in range(INIT_DECOMP):
            p = Decomposer(random.uniform(m,SW-m), random.uniform(m,SH-m))
            p.lineage_id=p.id; self.lin_reg[p.id]=Lineage(p.id,p.genome.hue,"decomposer"); self.decomp_list.append(p)
        for _ in range(INIT_PLANT):
            self.plants.append(Plant(random.uniform(m,SW-m), random.uniform(m,SH-m)))
        self.elog.add(0, "v5: taxonomy (Mammal/Reptile/Fungi/Plant), enhanced plants, mycelium", HILITE, ">")

    def _reg_lin(self, c):
        lid=c.lineage_id
        if lid not in self.lin_reg: self.lin_reg[lid]=Lineage(lid,c.genome.hue,c.species)
        l=self.lin_reg[lid]; l.n+=1; l.births+=1; l.hue=c.genome.hue
        l.max_gen=max(l.max_gen,c.lineage_depth); l.rcol()

    def _spawn_plants(self):
        mult = S_FOOD[self.season]
        rates = [0.15, PLANT_RATE, 1.0]
        rate = rates[self.food_mode] * mult
        if random.random() < rate and len(self.plants) < MAX_PLANT:
            self.plants.append(Plant(random.uniform(10,SW-10), random.uniform(10,SH-10)))
        for fz in self.fertile_zones:
            if random.random() < 0.02 * fz.strength and len(self.plants) < MAX_PLANT:
                px = clamp(fz.x + random.gauss(0, fz.radius*0.5), 10, SW-10)
                py = clamp(fz.y + random.gauss(0, fz.radius*0.5), 10, SH-10)
                self.plants.append(Plant(px, py, energy=PLANT_E * fz.strength))
        if random.random() < 0.02 * mult and len(self.plants) < MAX_PLANT - 5:
            cx=random.uniform(50,SW-50); cy=random.uniform(50,SH-50)
            for _ in range(random.randint(3,8)):
                if len(self.plants) >= MAX_PLANT: break
                self.plants.append(Plant(clamp(cx+random.gauss(0,30),10,SW-10),
                                         clamp(cy+random.gauss(0,30),10,SH-10)))
        # Seeding: mature plants spread new seedlings nearby
        new_plants = []
        for p in self.plants:
            if p.energy <= 0: continue
            # Count neighbors for root network
            p_neighbors = sum(1 for o in self.plants
                             if o is not p and o.energy > 0
                             and dst(p.x, p.y, o.x, o.y) < 40)
            can_spread = p.update(self.season, p_neighbors)
            if can_spread and len(self.plants) + len(new_plants) < MAX_PLANT:
                sx = clamp(p.x + random.gauss(0, 25), 10, SW-10)
                sy = clamp(p.y + random.gauss(0, 25), 10, SH-10)
                new_plants.append(Plant(sx, sy, energy=PLANT_E * 0.5))
                p.energy -= PLANT_E * 0.3  # cost of seeding
        self.plants.extend(new_plants)

    # ── Species classification ──
    def _classify_species(self):
        all_c = [c for c in self.prey_list + self.pred_list + self.decomp_list if c.alive and c.stage != STAGE_EGG]
        if not all_c: return
        # Key traits for clustering: diet_pref, aggression, speed, size, sociability, hue
        key_traits = ["diet_pref", "aggression", "speed", "size", "sociability"]
        # Normalize and compute fingerprint
        def fingerprint(c):
            fp = []
            for tn in key_traits:
                val = getattr(c.genome, tn)
                lo, hi = Genome.RANGES[Genome.NAMES.index(tn)]
                fp.append((val - lo) / (hi - lo))
            # Include taxonomy as a dimension (mammal=0, reptile=1, fungi=2)
            tax_val = TAXONOMY.index(c.taxonomy) if c.taxonomy in TAXONOMY else 0
            fp.append(tax_val / 2.0)  # normalize to 0-1
            return fp

        def fp_dist(a, b):
            return sum((x-y)**2 for x,y in zip(a,b))**0.5

        # Simple greedy clustering
        THRESHOLD = 0.35
        clusters = []  # (sid, fp_center, members)
        unassigned = list(all_c)
        random.shuffle(unassigned)

        for c in unassigned:
            fp = fingerprint(c)
            best_idx, best_dist = -1, THRESHOLD
            for i, (sid, center, members) in enumerate(clusters):
                d = fp_dist(fp, center)
                if d < best_dist:
                    best_dist = d; best_idx = i
            if best_idx >= 0:
                clusters[best_idx][2].append(c)
            else:
                sid = self._next_sid; self._next_sid += 1
                avg_t = {tn: getattr(c.genome, tn) for tn in Genome.NAMES}
                rec = SpeciesRecord(sid, c.species_name, avg_t)
                rec.birth_tick = self.tick
                self.species_records[sid] = rec
                clusters.append((sid, fp, [c]))

        # Update records (build new list to avoid mutating while iterating)
        updated_clusters = []
        for sid, center, members in clusters:
            if sid in self.species_records:
                rec = self.species_records[sid]
                rec.pop = len(members)
                rec.peak = max(rec.peak, rec.pop)
                rec.alive = True
                rec.snapshot(self.tick, members)
                # Recompute center
                n = len(members)
                new_center = [0.0] * len(key_traits)
                for m in members:
                    fp = fingerprint(m)
                    for j in range(len(key_traits)):
                        new_center[j] += fp[j]
                for j in range(len(key_traits)):
                    new_center[j] /= n
                updated_clusters.append((sid, new_center, members))
                for m in members:
                    m.species_id = sid
                    lin = self.lin_reg.get(m.lineage_id)
                    if lin is not None:
                        lin.species_id = sid

        # Mark extinct species
        active_sids = {sid for sid, _, _ in clusters}
        for sid, rec in self.species_records.items():
            if sid not in active_sids:
                if rec.alive:
                    self.elog.add(self.tick, f"Species '{rec.name}' went extinct!", (255,80,80), "X")
                rec.alive = False; rec.pop = 0

    def trigger_disease(self):
        x=random.uniform(100,SW-100); y=random.uniform(100,SH-100)
        names=["Mild Cough","Red Fever","Shadow Blight","Gut Worms","Spore Sickness"]
        d=DiseaseOutbreak(self.tick,x,y,name=random.choice(names),
                         vir=random.uniform(0.1,0.5),leth=random.uniform(0.03,0.12),rad=random.uniform(60,140))
        self.diseases.append(d)
        self.elog.add(self.tick, f"Disease '{d.name}' erupted!", d.color, "+")
        for _ in range(15):
            self.particles.append(Particle(x+random.uniform(-20,20),y+random.uniform(-20,20),
                                           random.uniform(-0.5,0.5),random.uniform(-1,0),random.randint(30,60),d.color,3))

    def trigger_disaster(self, dt=None):
        if dt is None: dt = random.choice(["fire","flood","meteor"])
        x=random.uniform(100,SW-100); y=random.uniform(100,SH-100)
        cfg={"fire":(120,random.randint(200,400),(220,120,30)),
             "flood":(100,random.randint(250,500),(40,100,220)),
             "meteor":(150,random.randint(300,500),(255,220,150))}
        r,dur,c = cfg[dt]
        self.disasters.append(Disaster(self.tick,dt,x,y,r,dur,c))
        self.elog.add(self.tick, f"{dt.upper()} at ({int(x)},{int(y)})", c, "!")

    def trigger_bloom(self):
        x=random.uniform(100,SW-100); y=random.uniform(100,SH-100)
        rad=random.uniform(80,160); cnt=random.randint(20,50)
        for _ in range(cnt):
            if len(self.plants)>=MAX_PLANT: break
            self.plants.append(Plant(clamp(x+random.gauss(0,rad*0.4),10,SW-10),
                                     clamp(y+random.gauss(0,rad*0.4),10,SH-10)))
        self.disasters.append(Disaster(self.tick,"bloom",x,y,int(rad),120,(80,220,100)))
        self.elog.add(self.tick, f"PLANT BLOOM +{cnt} plants", (80,220,100), "*")

    def trigger_random_event(self):
        r=random.random()
        if r<0.3: self.trigger_disease()
        elif r<0.65: self.trigger_disaster()
        else: self.trigger_bloom()

    def _proc_diseases(self):
        for d in self.diseases[:]:
            d.dur -= 1
            if d.dur <= 0:
                d.active=False; self.diseases.remove(d)
                self.elog.add(self.tick, f"'{d.name}' ended ({d.dead} deaths)", (150,150,150), "-")
                continue
            all_c = self.prey_list + self.pred_list + self.decomp_list
            for c in all_c:
                if not c.alive or c.diseased or c.disease_immune>0: continue
                dd = dst(c.x,c.y,d.x,d.y)
                if dd < d.rad and random.random() < d.vir*(1.0-c.disease_resistance)*0.02:
                    # Fungi are more disease resistant (they ARE pathogens)
                    if c.taxonomy == T_FUNGI and random.random() < 0.5:
                        continue  # fungi often resist diseases
                    c.diseased=True; c.disease_timer=random.randint(100,400); d.infected+=1
                    self.particles.append(Particle(c.x,c.y,0,-0.5,20,d.color,2))

    def _proc_disasters(self):
        for d in self.disasters[:]:
            d.update()
            if not d.active:
                self.disasters.remove(d)
                if d.killed>0: self.elog.add(self.tick, f"{d.dt.upper()} ended — {d.killed} killed", d.col, "X")
                continue
            cr=d.crad()
            all_c = self.prey_list + self.pred_list + self.decomp_list
            if d.dt == "fire":
                for c in all_c:
                    if not c.alive: continue
                    dd=dst(c.x,c.y,d.x,d.y)
                    if dd<cr:
                        # Armor and heat resistance reduce fire damage
                        eff_armor = c.eff_trait("armor") + c.heat_resistance * 0.3
                        dmg = 0.5 * (1 - eff_armor*0.5)
                        c.energy-=max(0.1, dmg)
                        if c.energy<=0: c.alive=False; d.killed+=1
                # Fire burns plants (trees most vulnerable)
                for p in self.plants:
                    if p.energy <= 0: continue
                    dd=dst(p.x,p.y,d.x,d.y)
                    if dd<cr:
                        burn_chance = p.fire_vulnerability() * 0.3
                        if random.random() < burn_chance:
                            p.energy = 0
                            d.killed += 1
            elif d.dt == "flood":
                for c in all_c:
                    if not c.alive: continue
                    dd=dst(c.x,c.y,d.x,d.y)
                    if 0<dd<cr:
                        push=0.3*(1-dd/cr); a=ang(d.x,d.y,c.x,c.y)
                        c.vx+=math.cos(a)*push; c.vy+=math.sin(a)*push; c.energy-=0.1
                        if c.energy<=0: c.alive=False; d.killed+=1
            elif d.dt == "meteor":
                for c in all_c:
                    if not c.alive: continue
                    dd=dst(c.x,c.y,d.x,d.y)
                    if dd<cr*0.4:
                        # Armor and size give survival chance in meteor core
                        survival = (c.eff_trait("armor")*0.3 + c.eff_trait("size")/20.0) * 0.5
                        if random.random() < survival:
                            c.energy -= c.energy * 0.7  # heavy damage but survive
                        else:
                            c.alive=False; d.killed+=1
                    elif dd<cr:
                        push=2.0*(1-dd/cr); a=ang(d.x,d.y,c.x,c.y)
                        c.vx+=math.cos(a)*push; c.vy+=math.sin(a)*push; c.energy-=0.8

    def _update_season(self):
        self.season_tick += 1
        if self.season_tick >= SEASON_LEN:
            self.season_tick=0; old=self.season; self.season_idx=(self.season_idx+1)%4
            self.elog.add(self.tick, f"Season: {old} -> {self.season}", S_COL[self.season], "~")

    def _handle_evt(self, ev, ctx):
        if not ev: return
        t = ev[0]
        if t == "kill": self.elog.add(self.tick, f"Pred #{ev[1]} killed prey #{ev[2]}", PRED_C, "x")
        elif t == "ambush_kill": self.elog.add(self.tick, f"Ambush kill by #{ev[1]}", (255,150,50), "x")
        elif t == "pack_kill": self.elog.add(self.tick, f"Pack killed prey #{ev[2]}", (255,180,50), "X")
        elif t == "birth" and self.total_births % 15 == 0:
            sp = ev[1]; m = "+" if ev[2]=="sexual" else "~"
            self.elog.add(self.tick, f"Egg ({sp[:1]}) {m} lin#{ev[3]}", (180,255,180), m)
        elif t == "mob_formed": self.elog.add(self.tick, f"Prey mob! ({ev[1]})", (255,255,100), "!")
        elif t == "pack_formed": self.elog.add(self.tick, f"Predator pack! ({ev[1]})", (255,150,80), "!")
        elif t == "ambush_start": self.elog.add(self.tick, f"Pred #{ev[1]} ambushing", (255,150,50), "A")
        elif t == "predator_frenzy": self.elog.add(self.tick, f"Pred #{ev[1]} frenzy!", (255,200,50), "!")
        elif t == "klepto": self.elog.add(self.tick, f"Pred #{ev[1]} stole from #{ev[2]}", (255,220,100), "$")
        elif t == "migration": self.elog.add(self.tick, f"Migration! {ev[1]} prey moving", (150,200,255), "M")
        elif t == "starvation" and random.random() < 0.03:
            self.elog.add(self.tick, f"{ev[1].title()} #{ev[2]} starved", (180,140,100), "-")
        elif t == "disease_death" and random.random() < 0.05:
            self.elog.add(self.tick, f"Creature died of disease", (180,50,220), "-")
        elif t == "egg_death":
            pass  # too frequent to log
        elif t == "species_emerge":
            self.elog.add(self.tick, f"New species: {ev[1]}", (100,255,200), "S")

    def _check_miles(self):
        np=len(self.prey_list); npr=len(self.pred_list); nd=len(self.decomp_list)
        for th in [50,100,150,200,250]:
            k=f"prey_{th}"
            if np>=th and k not in self._miles: self._miles[k]=True; self.elog.add(self.tick,f"Prey reached {th}!",PREY_C,"P")
        for th in [10,25,50,75]:
            k=f"pred_{th}"
            if npr>=th and k not in self._miles: self._miles[k]=True; self.elog.add(self.tick,f"Predators reached {th}!",PRED_C,"R")
        for th in [20,40,60]:
            k=f"decomp_{th}"
            if nd>=th and k not in self._miles: self._miles[k]=True; self.elog.add(self.tick,f"Decomposers reached {th}!",DECOMP_C,"D")
        if np==0 and "pe" not in self._miles: self._miles["pe"]=True; self.elog.add(self.tick,"PREY EXTINCT!",(255,80,80),"!")
        elif np>0 and "pe" in self._miles: del self._miles["pe"]
        if npr==0 and "re" not in self._miles: self._miles["re"]=True; self.elog.add(self.tick,"PREDATORS EXTINCT!",(255,80,80),"!")
        elif npr>0 and "re" in self._miles: del self._miles["re"]
        ns = sum(1 for r in self.species_records.values() if r.alive)
        for th in [3, 5, 8, 12]:
            k = f"species_{th}"
            if ns >= th and k not in self._miles:
                self._miles[k] = True; self.elog.add(self.tick, f"{ns} species coexisting!", (100,255,200), "S")

    def update(self):
        if self.paused: return
        for _ in range(self.speed_mult):
            self.tick += 1; self._update_season(); self._spawn_plants()
            self._proc_diseases(); self._proc_disasters()
            self.corpses = [c for c in self.corpses if c.decay()]
            self.fertile_zones = [f for f in self.fertile_zones if f.update()]
            self.nests = [n for n in self.nests if n.update()]

            for c in self.prey_list + self.pred_list:
                if c.alive and c.stage==STAGE_ADULT and c.eff_trait("sociability") > 0.6 and random.random() < 0.0003:
                    if not any(dst(c.x,c.y,n.x,n.y) < 60 for n in self.nests):
                        self.nests.append(Nest(c.x, c.y, c))

            # Build spatial grid for performance
            all_alive = [c for c in self.prey_list + self.pred_list + self.decomp_list if c.alive]
            grid = build_grid(all_alive)

            new_prey = []
            for p in self.prey_list:
                if not p.alive: continue
                child, evs = p.update(self.plants, self.pred_list, self.prey_list, self.corpses,
                                       self.nests, self.fertile_zones, SW, SH, self.season,
                                       self.particles, self.elog, grid)
                for e in evs: self._handle_evt(e, "prey")
                if child: new_prey.append(child); self._reg_lin(child); self.total_births+=1

            new_pred = []
            for p in self.pred_list:
                if not p.alive: continue
                child, evs = p.update(self.prey_list, self.pred_list, self.corpses,
                                       self.nests, SW, SH, self.season, self.particles, self.elog, grid, self.plants)
                for e in evs: self._handle_evt(e, "predator")
                if child: new_pred.append(child); self._reg_lin(child); self.total_births+=1

            new_decomp = []
            for p in self.decomp_list:
                if not p.alive: continue
                child, evs = p.update(self.corpses, self.decomp_list, self.fertile_zones,
                                       all_alive, SW, SH, self.season, self.particles, self.elog, grid)
                if child: new_decomp.append(child); self._reg_lin(child); self.total_births+=1

            for c in self.prey_list + self.pred_list + self.decomp_list:
                if not c.alive: self.corpses.append(Corpse(c))

            self.plants = [p for p in self.plants if p.energy > 0]
            self.prey_list = [p for p in self.prey_list if p.alive] + new_prey
            self.pred_list = [p for p in self.pred_list if p.alive] + new_pred
            self.decomp_list = [p for p in self.decomp_list if p.alive] + new_decomp

            if len(self.prey_list) > MAX_PREY:
                random.shuffle(self.prey_list)
                for c in self.prey_list[MAX_PREY:]:
                    if c.alive:
                        c.alive = False
                        self.corpses.append(Corpse(c))
                self.prey_list = self.prey_list[:MAX_PREY]
            if len(self.pred_list) > MAX_PRED:
                random.shuffle(self.pred_list)
                for c in self.pred_list[MAX_PRED:]:
                    if c.alive:
                        c.alive = False
                        self.corpses.append(Corpse(c))
                self.pred_list = self.pred_list[:MAX_PRED]
            if len(self.decomp_list) > MAX_DECOMP:
                random.shuffle(self.decomp_list)
                for c in self.decomp_list[MAX_DECOMP:]:
                    if c.alive:
                        c.alive = False
                        self.corpses.append(Corpse(c))
                self.decomp_list = self.decomp_list[:MAX_DECOMP]

            self.particles = [p for p in self.particles if p.update()]
            # Cap particles to prevent performance degradation
            if len(self.particles) > MAX_PARTICLES:
                self.particles = self.particles[-MAX_PARTICLES:]

            ac = defaultdict(int)
            for c in self.prey_list+self.pred_list+self.decomp_list:
                if c.alive: ac[c.lineage_id] += 1
            for lid, l in self.lin_reg.items():
                l.n = ac.get(lid, 0); l.alive = l.n > 0

            # Lineage trait snapshots every 500 ticks
            if self.tick % 500 == 0:
                for lid, lin in self.lin_reg.items():
                    if not lin.alive: continue
                    members = [c for c in self.prey_list+self.pred_list+self.decomp_list
                               if c.alive and c.lineage_id == lid]
                    if members:
                        lin.snapshot_traits(self.tick, members)

            # Species classification every 300 ticks
            self._species_rebuild_cd += 1
            if self._species_rebuild_cd >= 300:
                self._species_rebuild_cd = 0
                old_sids = {sid for sid, r in self.species_records.items() if r.alive}
                self._classify_species()
                new_sids = {sid for sid, r in self.species_records.items() if r.alive}
                emerged = new_sids - old_sids
                for sid in emerged:
                    rec = self.species_records[sid]
                    self._handle_evt(("species_emerge", rec.name), "species")

            if self.tick % 10 == 0:
                self.hist_prey.append(len(self.prey_list))
                self.hist_pred.append(len(self.pred_list))
                self.hist_decomp.append(len(self.decomp_list))
                self.hist_plant.append(len(self.plants))
                for h in (self.hist_prey,self.hist_pred,self.hist_decomp,self.hist_plant):
                    if len(h) > self.hist_max: h.pop(0)

            if self.tick % 100 == 0: self._check_miles()
            if random.random() < 0.0003: self.trigger_random_event()

    # ── Drawing ──
    def draw_sim(self):
        self.sim_srf.fill(DARK_BG)
        sc = S_COL[self.season]
        tint = pygame.Surface((SW,SH), pygame.SRCALPHA); tint.fill((*sc, 8))
        self.sim_srf.blit(tint, (0,0))
        if self.show_grid:
            for gx in range(0,SW,CELL): pygame.draw.line(self.sim_srf, GRID_C, (gx,0), (gx,SH))
            for gy in range(0,SH,CELL): pygame.draw.line(self.sim_srf, GRID_C, (0,gy), (SW,gy))
        for d in self.disasters: d.draw(self.sim_srf)
        for d in self.diseases:
            r=int(d.rad); s=pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            pygame.draw.circle(s,(*d.color,15),(r,r),r); pygame.draw.circle(s,(*d.color,30),(r,r),r,1)
            self.sim_srf.blit(s, (int(d.x)-r, int(d.y)-r))
        for fz in self.fertile_zones:
            r=int(fz.radius); s=pygame.Surface((r*2,r*2), pygame.SRCALPHA)
            a=int(clamp(fz.strength/2, 0, 1)*25)
            pygame.draw.circle(s,(80,200,60,a),(r,r),r); pygame.draw.circle(s,(80,200,60,a+10),(r,r),r,1)
            self.sim_srf.blit(s, (int(fz.x)-r, int(fz.y)-r))
        for n in self.nests:
            r = int(12 * n.strength)
            nc = hsv2rgb(n.hue, 0.4, 0.5)
            pygame.draw.circle(self.sim_srf, nc, (int(n.x), int(n.y)), r, 2)
            if n.strength > 0.5:
                pygame.draw.circle(self.sim_srf, lerpc(nc, WHITE, 0.3), (int(n.x), int(n.y)), r-3, 1)
        for c in self.corpses:
            a=clamp(c.energy/(c.radius*10), 0.1, 0.6); col=hsv2rgb(c.hue, 0.3, 0.4*a)
            r=max(1, int(c.radius))
            pygame.draw.circle(self.sim_srf, col, (int(c.x), int(c.y)), r)
            pygame.draw.line(self.sim_srf, (100,60,60), (int(c.x-r),int(c.y-r)), (int(c.x+r),int(c.y+r)), 1)
            pygame.draw.line(self.sim_srf, (100,60,60), (int(c.x+r),int(c.y-r)), (int(c.x-r),int(c.y+r)), 1)
        for p in self.plants:
            if p.energy <= 0: continue
            er=clamp(p.energy/PLANT_E,0,1)
            if p.dormant:
                col=lerpc((40,40,50), (80,100,60), 0.3)  # brownish dormant
            elif p.toxicity:
                col=lerpc((20,80,40), (200,200,50), er*0.7)  # yellowish toxic plants
            else:
                col=lerpc((20,80,40), PLANT_C, er)
            pr = int(p.radius)
            ix, iy = int(p.x), int(p.y)
            # Draw based on plant type and growth stage
            if p.plant_type == "tree" and p.growth_stage >= 1:
                # Trees: circle with trunk
                pygame.draw.circle(self.sim_srf, col, (ix, iy), pr)
                if p.growth_stage >= 2:
                    pygame.draw.line(self.sim_srf, (100, 70, 40),
                                     (ix, iy + pr), (ix, iy + pr + 4), 2)
            elif p.plant_type == "bush":
                # Bushes: slightly larger with inner highlight
                pygame.draw.circle(self.sim_srf, col, (ix, iy), pr)
                if p.growth_stage >= 2 and not p.dormant:
                    pygame.draw.circle(self.sim_srf, lerpc(col, (255, 220, 150), 0.3),
                                       (ix, iy), max(1, pr - 2))
            else:
                # Grass: simple circle
                pygame.draw.circle(self.sim_srf, col, (ix, iy), pr)
            # Toxic plant indicator
            if p.toxicity and not p.dormant:
                pygame.draw.circle(self.sim_srf, (200, 200, 50), (ix + pr + 1, iy - pr), 1)
        for c in self.decomp_list: c.draw(self.sim_srf, self.lin_mode, self.lin_reg)
        for c in self.prey_list: c.draw(self.sim_srf, self.lin_mode, self.lin_reg)
        for c in self.pred_list: c.draw(self.sim_srf, self.lin_mode, self.lin_reg)
        for p in self.particles: p.draw(self.sim_srf)
        if self.selected and self.selected.alive:
            s=self.selected; r=int(s.eff_trait("size"))+6
            pygame.draw.circle(self.sim_srf, WHITE, (int(s.x),int(s.y)), r, 2)
            pygame.draw.circle(self.sim_srf, HILITE, (int(s.x),int(s.y)), r+3, 1)
        self.screen.blit(self.sim_srf, (0,0))

    def _graph(self, x0, y, gw, gh):
        gr=pygame.Rect(x0,y,gw,gh)
        pygame.draw.rect(self.screen,(12,12,18),gr); pygame.draw.rect(self.screen,DIV,gr,1)
        if len(self.hist_prey)>1:
            mv=max(max(self.hist_prey+self.hist_pred+self.hist_decomp+self.hist_plant),1)
            def pts(data,col):
                p=[]; n=len(data)
                for i,v in enumerate(data):
                    px=x0+int(i/max(n-1,1)*(gw-1)); py=y+gh-1-int(v/mv*(gh-4))-2; p.append((px,py))
                if len(p)>=2: pygame.draw.lines(self.screen,col,False,p,1)
            pts(self.hist_plant, PLANT_C); pts(self.hist_prey, PREY_C)
            pts(self.hist_pred, PRED_C); pts(self.hist_decomp, DECOMP_C)
        y+=gh+5
        for label,col,dx in [("Prey",PREY_C,0),("Pred",PRED_C,70),("Dec",DECOMP_C,130),("Plant",PLANT_C,190)]:
            pygame.draw.line(self.screen,col,(x0+dx,y+4),(x0+dx+12,y+4),2)
            self.screen.blit(self.ft.render(label,True,col),(x0+dx+16,y))
        y += 14
        # Taxonomy legend
        for tax_name in [T_MAMMAL, T_REPTILE, T_FUNGI]:
            tc = TAXON_COLORS[tax_name]
            tl = TAXON_LABELS[tax_name]
            pygame.draw.rect(self.screen, tc, (x0, y+2, 8, 8))
            self.screen.blit(self.ft.render(tl, True, tc), (x0+12, y))
        return y+16

    def _trait_bars(self, x0, y, creatures, label, bw):
        n=len(creatures)
        if n==0: self.screen.blit(self.fs.render(f"  {label} (extinct)",True,(180,60,60)),(x0,y)); return y+18
        self.screen.blit(self.fm.render(f"AVG {label}",True,HILITE),(x0,y)); y+=20
        stages = defaultdict(int)
        for c in creatures: stages[c.stage] += 1
        self.screen.blit(self.ft.render(f"E:{stages[STAGE_EGG]} J:{stages[STAGE_JUV]} A:{stages[STAGE_ADULT]} El:{stages[STAGE_ELDER]}",True,TEXT_C),(x0,y)); y+=14
        # Diet distribution
        diets = [0, 0, 0]  # herb, omni, carn
        for c in creatures:
            dp = c.eff_trait("diet_pref")
            if dp < 0.33: diets[0] += 1
            elif dp < 0.66: diets[1] += 1
            else: diets[2] += 1
        self.screen.blit(self.ft.render(f"Diet H:{diets[0]} O:{diets[1]} C:{diets[2]}",True,TEXT_C),(x0,y)); y+=14
        traits=[("Spd","speed",0.5,6),("Sz","size",3,14),("Prc","perception",20,220),
                ("Eff","efficiency",0.2,2.5),("Agg","aggression",0,1),("Soc","sociability",0,1),
                ("Fert","fertility",0.1,1),("Tox","toxicity",0,1),
                ("Arm","armor",0,1),("Cam","camouflage",0,1),
                ("Int","intelligence",0,1),("Reg","regeneration",0,1),("Diet","diet_pref",0,1)]
        for tl,tn,lo,hi in traits:
            avg=sum(c.eff_trait(tn) for c in creatures)/n
            ratio=clamp((avg-lo)/(hi-lo),0,1)
            self.screen.blit(self.ft.render(f"{tl:<4s}",True,TEXT_C),(x0,y))
            bx=x0+28
            pygame.draw.rect(self.screen,(40,40,55),(bx,y+1,bw,11))
            pygame.draw.rect(self.screen,lerpc((60,120,200),(255,200,60),ratio),(bx,y+1,int(ratio*bw),11))
            pygame.draw.rect(self.screen,DIV,(bx,y+1,bw,11),1)
            vs=f"{avg:.2f}" if hi<100 else f"{avg:.0f}"
            self.screen.blit(self.ft.render(vs,True,WHITE),(bx+bw+3,y)); y+=13
        return y

    def _trend_arrow(self, val):
        if val > 0.02: return "^"
        elif val < -0.02: return "v"
        return "="

    def _lin_tab(self, x0, y, pw):
        sl=sorted(self.lin_reg.values(), key=lambda l:(l.alive,l.n,l.births), reverse=True)
        self.screen.blit(self.fm.render("TOP LINEAGES",True,HILITE),(x0,y)); y+=20
        sp_cols = {"prey":PREY_C, "predator":PRED_C, "decomposer":DECOMP_C}
        for i in range(min(len(sl),8)):
            l=sl[i]
            pygame.draw.rect(self.screen, l.color, (x0,y+1,10,10))
            pygame.draw.rect(self.screen, WHITE, (x0,y+1,10,10), 1)
            sp=l.sp[0].upper()
            self.screen.blit(self.ft.render(sp,True,sp_cols.get(l.sp,TEXT_C)),(x0+13,y))
            st="" if l.alive else " [X]"
            # Show evolution trend for key traits
            trend = ""
            if len(l.trait_snapshots) >= 3:
                for tn in ["speed","aggression","diet_pref"]:
                    old = l.trait_snapshots[0][1].get(tn, 0)
                    new = l.trait_snapshots[-1][1].get(tn, 0)
                    if abs(new - old) > 0.05:
                        arrow = "^" if new > old else "v"
                        short = tn[:3]
                        trend += f" {short}{arrow}"
            self.screen.blit(self.ft.render(f"n={l.n:>3d} g={l.max_gen:>3d} b={l.births:>4d}{st}{trend}",True,TEXT_C if l.alive else (100,100,100)),(x0+24,y))
            y+=14
        y+=6; pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=8
        al=[l for l in self.lin_reg.values() if l.alive]
        self.screen.blit(self.fs.render(f"Total: {len(self.lin_reg)}  Alive: {len(al)}",True,TEXT_C),(x0,y)); y+=18
        ms="ON" if self.lin_mode else "OFF"; mc=HILITE if self.lin_mode else (120,120,130)
        self.screen.blit(self.fs.render(f"Lineage colors: {ms} [L]",True,mc),(x0,y)); y+=20
        if self.selected and self.selected.alive:
            pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=8
            s=self.selected
            self.screen.blit(self.fm.render("SELECTED",True,HILITE),(x0,y)); y+=18
            sp="P" if isinstance(s,Prey) else "R" if isinstance(s,Predator) else "D"
            tax_l = TAXON_LABELS.get(s.taxonomy, "?")
            self.screen.blit(self.ft.render(f"[{sp}] #{s.id}  Tax:{tax_l}  Stage: {s.stage_name}",True,TEXT_C),(x0,y)); y+=13
            self.screen.blit(self.ft.render(f"State: {s.state}  Age: {s.age}  Nrg: {s.energy:.0f}",True,TEXT_C),(x0,y)); y+=13
            self.screen.blit(self.ft.render(f"Ch:{s.children_count} K:{s.kills} Depth:{s.lineage_depth}",True,TEXT_C),(x0,y)); y+=13
            self.screen.blit(self.ft.render(f"Alpha:{s.is_alpha} Dom:{s.dominance_score:.1f} SpcID:{s.species_id}",True,TEXT_C),(x0,y)); y+=13
            # Show adapted traits
            ad = sum(1 for v in s.adapt.values() if abs(v) > 0.01)
            self.screen.blit(self.ft.render(f"Adapted traits: {ad}/16",True,(180,220,180)),(x0,y))
        return y

    def _species_tab(self, x0, y, pw):
        self.screen.blit(self.fm.render("SPECIES & EVOLUTION",True,HILITE),(x0,y)); y+=20
        alive_sp = [r for r in self.species_records.values() if r.alive]
        self.screen.blit(self.ft.render(f"Active species: {len(alive_sp)}  Total ever: {len(self.species_records)}",True,TEXT_C),(x0,y)); y+=18
        pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
        # Species list with trait trends
        sorted_sp = sorted(alive_sp, key=lambda r: r.pop, reverse=True)
        for i, sp in enumerate(sorted_sp[:10]):
            pygame.draw.rect(self.screen, sp.color, (x0, y+1, 10, 10))
            pygame.draw.rect(self.screen, WHITE, (x0, y+1, 10, 10), 1)
            self.screen.blit(self.ft.render(f"{sp.name}",True,WHITE),(x0+14,y))
            # Trend arrows for key traits
            trends = ""
            for tn in ["diet_pref","aggression","speed","armor","intelligence"]:
                t = sp.trait_trend(tn)
                if abs(t) > 0.01:
                    arrow = "^" if t > 0 else "v"
                    trends += f" {tn[:3]}{arrow}"
            col = TEXT_C if sp.pop > 5 else (120,120,130)
            self.screen.blit(self.ft.render(f"pop:{sp.pop:>3d} peak:{sp.peak}{trends}",True,col),(x0+14,y+13))
            # Mini trait bars for top 3
            if i < 3:
                by = y + 26
                for tl, tn, bw in [("D", "diet_pref", 60), ("A", "aggression", 40), ("I", "intelligence", 40)]:
                    avg = sp.avg_traits.get(tn, 0)
                    lo, hi = Genome.RANGES[Genome.NAMES.index(tn)]
                    ratio = clamp((avg-lo)/(hi-lo), 0, 1)
                    self.screen.blit(self.ft.render(tl, True, TEXT_C), (x0+14, by))
                    bx = x0+26
                    pygame.draw.rect(self.screen, (40,40,55), (bx, by+2, bw, 8))
                    pygame.draw.rect(self.screen, lerpc((60,120,200), sp.color, ratio), (bx, by+2, int(ratio*bw), 8))
                    by += 11
                y = by + 2
            else:
                y += 40
        if not alive_sp:
            self.screen.blit(self.ft.render("  Classifying... wait 300 ticks",True,(100,100,120)),(x0,y)); y+=18
        y+=6; pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=8
        # Diet spectrum overview
        self.screen.blit(self.fm.render("DIET SPECTRUM",True,HILITE),(x0,y)); y+=18
        all_c = self.prey_list + self.pred_list + self.decomp_list
        if all_c:
            herb = sum(1 for c in all_c if c.eff_trait("diet_pref") < 0.33)
            omni = sum(1 for c in all_c if 0.33 <= c.eff_trait("diet_pref") < 0.66)
            carn = sum(1 for c in all_c if c.eff_trait("diet_pref") >= 0.66)
            total = len(all_c)
            bw = pw - 60
            bx = x0 + 30
            # Draw spectrum bar
            pygame.draw.rect(self.screen, (40,40,55), (bx, y, bw, 16))
            if total > 0:
                hw = int(bw * herb / total)
                ow = int(bw * omni / total)
                cw = bw - hw - ow
                pygame.draw.rect(self.screen, (80,180,80), (bx, y, hw, 16))
                pygame.draw.rect(self.screen, (180,180,80), (bx+hw, y, ow, 16))
                pygame.draw.rect(self.screen, (200,80,80), (bx+hw+ow, y, cw, 16))
            pygame.draw.rect(self.screen, DIV, (bx, y, bw, 16), 1)
            y += 20
            self.screen.blit(self.ft.render(f"Herb:{herb} Omni:{omni} Carn:{carn}",True,TEXT_C),(x0,y)); y+=18
        # Trait evolution summary
        y+=4; pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=8
        self.screen.blit(self.fm.render("EVOLUTION TRENDS",True,HILITE),(x0,y)); y+=18
        # Show top species with most dramatic changes
        dramatic = []
        for sp in alive_sp:
            max_change = 0; max_trait = ""
            for tn in ["speed","size","aggression","diet_pref","armor","intelligence","toxicity","camouflage"]:
                t = sp.trait_trend(tn)
                if abs(t) > abs(max_change):
                    max_change = t; max_trait = tn
            if abs(max_change) > 0.01:
                dramatic.append((sp, max_trait, max_change))
        dramatic.sort(key=lambda x: abs(x[2]), reverse=True)
        for sp, tn, ch in dramatic[:6]:
            arrow = "^" if ch > 0 else "v"
            col = (100,255,100) if ch > 0 else (255,100,100)
            self.screen.blit(self.ft.render(f"{sp.name[:15]:<15s} {tn:<12s} {arrow}",True,col),(x0,y)); y+=13
        return y

    def _evt_tab(self, x0, y, pw):
        sc=S_COL[self.season]
        self.screen.blit(self.fm.render("SEASON",True,HILITE),(x0,y)); y+=20
        self.screen.blit(self.fl.render(self.season,True,sc),(x0,y))
        bx=x0+90; bw=pw-95
        pygame.draw.rect(self.screen,(40,40,55),(bx,y+4,bw,12))
        pygame.draw.rect(self.screen,sc,(bx,y+4,int(bw*self.season_tick/SEASON_LEN),12))
        pygame.draw.rect(self.screen,DIV,(bx,y+4,bw,12),1); y+=24
        self.screen.blit(self.ft.render(f"Food: x{S_FOOD[self.season]:.1f}  Energy: x{S_ENRG[self.season]:.1f}",True,TEXT_C),(x0,y)); y+=18
        pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=8
        self.screen.blit(self.fm.render("ACTIVE EFFECTS",True,HILITE),(x0,y)); y+=20
        if not self.diseases and not self.disasters:
            self.screen.blit(self.ft.render("  None",True,(100,100,120)),(x0,y)); y+=14
        for d in self.diseases:
            self.screen.blit(self.ft.render(f" {d.name} inf:{d.infected} dead:{d.dead}",True,d.color),(x0,y)); y+=14
        for d in self.disasters:
            self.screen.blit(self.ft.render(f" {d.dt.upper()} r={int(d.crad())} k={d.killed}",True,d.col),(x0,y)); y+=14
        y+=4; pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=8
        self.screen.blit(self.fm.render("INTERACTIONS",True,HILITE),(x0,y)); y+=20
        parasitized = sum(1 for c in self.prey_list+self.pred_list if c.parasite_host is not None)
        for note in ["Nests: "+str(len(self.nests))+" active",
                      "Fertile zones: "+str(len(self.fertile_zones)),
                      "Corpses: "+str(len(self.corpses)),
                      "Dominant preds: "+str(sum(1 for p in self.pred_list if p.is_alpha)),
                      "Migrating: "+str(sum(1 for p in self.prey_list if p.state==S_MIGRATE)),
                      "Parasitized: "+str(parasitized),
                      "Playing (juv): "+str(sum(1 for c in self.prey_list+self.pred_list+self.decomp_list if c.state==S_PLAY)),
                      "Sleeping: "+str(sum(1 for c in self.prey_list+self.pred_list+self.decomp_list if c.state==S_SLEEP))]:
            self.screen.blit(self.ft.render(note,True,TEXT_C),(x0,y)); y+=14
        y+=6; pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=8
        self.screen.blit(self.fm.render("TRIGGERS",True,HILITE),(x0,y)); y+=20
        for label,key in [("Random Event","E"),("Disease","D"),("Bloom","B")]:
            self.screen.blit(self.ft.render(f"[{key}] {label}",True,(160,160,180)),(x0,y)); y+=14
        y+=6; pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=8
        self.screen.blit(self.fm.render("EVENT LOG",True,HILITE),(x0,y)); y+=20
        for ev in self.elog.recent(40):
            age=self.tick-ev.tick; fade=clamp(1-age/5000,0.3,1)
            col=tuple(int(c*fade) for c in ev.color)
            line=f"{ev.icon} t{ev.tick:>6d} {ev.text}"
            if len(line)>50: line=line[:49]+"~"
            self.screen.blit(self.ft.render(line,True,col),(x0,y)); y+=13
            if y > SCR_H - 20: break
        return y

    def draw_panel(self):
        panel=pygame.Rect(SW,0,PW,SCR_H)
        pygame.draw.rect(self.screen,PANEL_BG,panel)
        pygame.draw.line(self.screen,DIV,(SW,0),(SW,SCR_H),2)
        x0=SW+10; pw=PW-20; y=6
        self.screen.blit(self.fT.render("ARTIFICIAL LIFE v5",True,HILITE),(x0,y)); y+=24
        sc=S_COL[self.season]
        self.screen.blit(self.ft.render(f"T:{self.tick:>6d} B:{self.total_births:>4d} {self.speed_mult}x {self.season}",True,TEXT_C),(x0,y)); y+=16
        tw=(pw-8)//5
        for i,name in enumerate(self.tab_names):
            tx=x0+i*(tw+2); bg=TAB_A if i==self.active_tab else TAB_I
            tc=HILITE if i==self.active_tab else (120,120,140)
            pygame.draw.rect(self.screen,bg,(tx,y,tw,20),border_radius=3)
            pygame.draw.rect(self.screen,DIV,(tx,y,tw,20),1,border_radius=3)
            self.screen.blit(self.ft.render(name,True,tc),(tx+4,y+4))
        y+=28; pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
        if self.active_tab==0: self._stats_tab(x0,y,pw)
        elif self.active_tab==1: self._traits_tab(x0,y,pw)
        elif self.active_tab==2: self._lin_tab(x0,y,pw)
        elif self.active_tab==3: self._species_tab(x0,y,pw)
        elif self.active_tab==4: self._evt_tab(x0,y,pw)

    def _stats_tab(self, x0, y, pw):
        np=len(self.prey_list); npr=len(self.pred_list); nd=len(self.decomp_list); npl=len(self.plants)
        self.screen.blit(self.fm.render("POPULATION",True,HILITE),(x0,y)); y+=22
        for label,count,col,rad in [("Prey",np,PREY_C,5),("Predators",npr,PRED_C,6),
                                     ("Decomps",nd,DECOMP_C,4),("Plants",npl,PLANT_C,3)]:
            pygame.draw.circle(self.screen,col,(x0+6,y+6),rad)
            self.screen.blit(self.fs.render(f"{label:<9s}{count}",True,col),(x0+18,y)); y+=16
        self.screen.blit(self.ft.render(f"Corpses: {len(self.corpses)}  Nests: {len(self.nests)}",True,(120,100,100)),(x0+18,y)); y+=18
        ns = sum(1 for r in self.species_records.values() if r.alive)
        self.screen.blit(self.ft.render(f"Active species: {ns}",True,(100,255,200)),(x0+18,y)); y+=16
        pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
        self.screen.blit(self.fm.render("LIFE STAGES",True,HILITE),(x0,y)); y+=18
        for sp_name, creatures in [("Prey", self.prey_list), ("Predator", self.pred_list), ("Decomp", self.decomp_list)]:
            stages = defaultdict(int)
            for c in creatures: stages[c.stage] += 1
            self.screen.blit(self.ft.render(f"{sp_name}: E{stages[STAGE_EGG]} J{stages[STAGE_JUV]} A{stages[STAGE_ADULT]} E{stages[STAGE_ELDER]}",True,TEXT_C),(x0,y)); y+=13
        y+=4
        pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
        # Taxonomy breakdown
        self.screen.blit(self.fm.render("TAXONOMY",True,HILITE),(x0,y)); y+=18
        all_creatures = self.prey_list + self.pred_list + self.decomp_list
        tax_counts = defaultdict(int)
        for c in all_creatures:
            if c.alive: tax_counts[c.taxonomy] += 1
        for tax_name in TAXONOMY:
            cnt = tax_counts.get(tax_name, 0)
            tc = TAXON_COLORS.get(tax_name, TEXT_C)
            tl = TAXON_LABELS.get(tax_name, tax_name)
            self.screen.blit(self.ft.render(f"{tl:<4s}{cnt:>4d}",True,tc),(x0,y)); y+=13
        # Plant type breakdown
        pt_counts = defaultdict(int)
        for p in self.plants:
            if p.energy > 0: pt_counts[p.plant_type] += 1
        pstr = "  ".join(f"{k}:{v}" for k,v in sorted(pt_counts.items()))
        self.screen.blit(self.ft.render(f"Plants: {pstr}",True,PLANT_C),(x0,y)); y+=16
        y+=2; pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
        self.screen.blit(self.fm.render("BEHAVIOR STATES",True,HILITE),(x0,y)); y+=18
        all_c = self.prey_list + self.pred_list + self.decomp_list
        sc = defaultdict(int)
        for c in all_c: sc[c.state] += 1
        slabels = {"wander":"Wander","flee":"Flee","hunt":"Hunt","eat":"Eat","sleep":"Sleep",
                   "ambush":"Ambush","mob":"Mob","court":"Court","scavenge":"Scav","frenzy":"Frenzy",
                   "pack":"Pack","parent":"Parent","play":"Play","migrate":"Migrate",
                   "territory":"Territory","decompose":"Decomp","parasite":"Parasite",
                   "hatch":"Hatch","bask":"Bask","spore":"Spore","forage":"Forage"}
        col_w = pw // 3
        row = 0
        for st, lbl in slabels.items():
            cnt = sc.get(st, 0)
            if cnt > 0:
                tx = x0 + (row % 3) * col_w; ty = y + (row // 3) * 13
                self.screen.blit(self.ft.render(f"{lbl:<8s}{cnt:>3d}", True, TEXT_C), (tx, ty))
                row += 1
        y += ((row // 3) + 1) * 13 + 6
        pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
        y = self._graph(x0, y, pw, 90); y+=4
        pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
        self.screen.blit(self.fm.render("CONTROLS",True,HILITE),(x0,y)); y+=18
        for line in ["SPC Pause F Food G Grid L Lineage",
                      "R Reset +/- Speed 1-5 Tabs",
                      "E Event D Disease B Bloom",
                      "CLICK Inspect ESC Quit"]:
            self.screen.blit(self.ft.render(line,True,(130,130,150)),(x0,y)); y+=13
        y+=6
        status="PAUSED" if self.paused else "RUNNING"
        scc=(255,200,60) if self.paused else (80,255,120)
        self.screen.blit(self.fm.render(status,True,scc),(x0,y))
        fl=["LOW","NORMAL","HIGH"]
        self.screen.blit(self.fs.render(f"Food:{fl[self.food_mode]}",True,TEXT_C),(x0+80,y+2))
        if self.selected and self.selected.alive:
            y+=22; pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
            s=self.selected; sp="PREY" if isinstance(s,Prey) else "PRED" if isinstance(s,Predator) else "DECOMP"
            self.screen.blit(self.fm.render(f"INSPECT {sp} #{s.id}",True,HILITE),(x0,y)); y+=16
            self.screen.blit(self.ft.render(f"Stage:{s.stage_name} State:{s.state}",True,TEXT_C),(x0,y)); y+=13
            self.screen.blit(self.ft.render(f"Age:{s.age} Nrg:{s.energy:.0f} Ch:{s.children_count} K:{s.kills}",True,TEXT_C),(x0,y)); y+=13
            dp = s.eff_trait("diet_pref")
            dname = "Herb" if dp < 0.33 else "Omni" if dp < 0.66 else "Carn"
            self.screen.blit(self.ft.render(f"Diet:{dname}({dp:.2f}) Arm:{s.eff_trait('armor'):.2f} Int:{s.eff_trait('intelligence'):.2f}",True,TEXT_C),(x0,y))

    def _traits_tab(self, x0, y, pw):
        bw = pw - 80
        y = self._trait_bars(x0, y, self.prey_list, "PREY", bw); y+=8
        pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
        y = self._trait_bars(x0, y, self.pred_list, "PRED", bw); y+=8
        pygame.draw.line(self.screen,DIV,(x0,y),(x0+pw,y)); y+=6
        y = self._trait_bars(x0, y, self.decomp_list, "DECOMP", bw)

    def draw(self):
        self.draw_sim(); self.draw_panel(); pygame.display.flip()

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: self.running = False
            elif ev.type == pygame.KEYDOWN:
                k = ev.key
                if k == pygame.K_ESCAPE: self.running = False
                elif k == pygame.K_SPACE: self.paused = not self.paused
                elif k == pygame.K_g: self.show_grid = not self.show_grid
                elif k == pygame.K_r: self.reset()
                elif k == pygame.K_f: self.food_mode = (self.food_mode + 1) % 3
                elif k == pygame.K_l: self.lin_mode = not self.lin_mode
                elif k == pygame.K_e: self.trigger_random_event()
                elif k == pygame.K_d: self.trigger_disease()
                elif k == pygame.K_b: self.trigger_bloom()
                elif k == pygame.K_1: self.active_tab = 0
                elif k == pygame.K_2: self.active_tab = 1
                elif k == pygame.K_3: self.active_tab = 2
                elif k == pygame.K_4: self.active_tab = 3
                elif k == pygame.K_5: self.active_tab = 4
                elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS): self.speed_mult = min(self.speed_mult+1, 10)
                elif k in (pygame.K_MINUS, pygame.K_KP_MINUS): self.speed_mult = max(self.speed_mult-1, 1)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                if mx < SW:
                    best, bd = None, 20
                    for c in self.prey_list + self.pred_list + self.decomp_list:
                        if not c.alive: continue
                        d = dst(mx, my, c.x, c.y)
                        if d < bd: bd, best = d, c
                    self.selected = best

    def run(self):
        while self.running:
            self.handle_events(); self.update(); self.draw(); self.clock.tick(FPS)
        pygame.quit(); sys.exit()

if __name__ == "__main__":
    sim = Simulation()
    sim.run()