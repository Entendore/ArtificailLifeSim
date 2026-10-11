import pygame
import random
import math
import sys

# --- Constants ---
WIDTH, HEIGHT = 1200, 800
FPS = 60

MAX_PLANTS = 500
PLANT_SPAWN_RATE = 6
PLANT_ENERGY = 25

MAX_CREATURES = 300
REPRODUCE_THRESHOLD = 90
STARTING_ENERGY = 60
MATING_COOLDOWN = 600

# Colors
BG_COLOR = (15, 15, 20)
PLANT_COLOR = (40, 180, 40)
TEXT_COLOR = (200, 200, 200)
UI_BG = (0, 0, 0)

CATEGORY_COLORS = {
    "HERBIVORE": (50, 200, 50), "CARNIVORE": (200, 50, 50), "OMNIVORE": (150, 50, 200),
    "DETRITIVORE": (150, 100, 50), "SCAVENGER": (120, 120, 120), "PARASITE": (220, 220, 50)
}

DIET_MAP = {
    "Herbivore": "HERBIVORE", "Carnivore": "CARNIVORE", "Omnivore": "OMNIVORE",
    "Folivore": "HERBIVORE", "Frugivore": "HERBIVORE", "Granivore": "HERBIVORE",
    "Nectarivore": "HERBIVORE", "Algivore": "HERBIVORE", "Xylophage": "HERBIVORE",
    "Palynivore": "HERBIVORE", "Florivore": "HERBIVORE", "Sapivore": "HERBIVORE",
    "Rhizophage": "HERBIVORE", "Bambusivore": "HERBIVORE", "Lignivore": "HERBIVORE",
    "Insectivore": "CARNIVORE", "Piscivore": "CARNIVORE", "Molluscivore": "CARNIVORE",
    "Vermivore": "CARNIVORE", "Ophiophage": "CARNIVORE", "Ovivore": "CARNIVORE",
    "Myrmecophage": "CARNIVORE", "Termitivore": "CARNIVORE", "Carcinophage": "CARNIVORE",
    "Carcinivore": "CARNIVORE", "Cetivore": "CARNIVORE", "Planktivore": "CARNIVORE",
    "Zooplanktivore": "CARNIVORE", "Ichthyophage": "CARNIVORE", "Arachnivore": "CARNIVORE",
    "Avivore": "CARNIVORE", "Mammalivore": "CARNIVORE", "Herpetivore": "CARNIVORE",
    "Sanguivore": "CARNIVORE", "Hematophage": "CARNIVORE", "Detritivore": "DETRITIVORE",
    "Saprophage": "DETRITIVORE", "Necrophage": "SCAVENGER", "Coprophage": "DETRITIVORE",
    "Fungivore": "HERBIVORE", "Bacterivore": "DETRITIVORE", "Virovore": "PARASITE",
    "Keratophage": "CARNIVORE", "Predator": "CARNIVORE", "Scavenger": "SCAVENGER",
    "Parasite": "PARASITE", "Parasitoid": "PARASITE", "Filter feeder": "HERBIVORE",
    "Suspension feeder": "HERBIVORE", "Deposit feeder": "DETRITIVORE", "Grazer": "HERBIVORE",
    "Browser": "HERBIVORE", "Forager": "OMNIVORE", "Hunter": "CARNIVORE",
    "Ambush predator": "CARNIVORE", "Pursuit predator": "CARNIVORE",
    "Opportunistic feeder": "OMNIVORE", "Generalist feeder": "OMNIVORE",
    "Specialist feeder": "OMNIVORE", "Limnivore": "DETRITIVORE", "Benthivore": "DETRITIVORE",
    "Microphage": "HERBIVORE", "Macrophage": "CARNIVORE", "Cannibal": "CARNIVORE",
    "Autophage": "OMNIVORE", "Geophage": "DETRITIVORE", "Lithophage": "DETRITIVORE",
    "Mucophage": "DETRITIVORE", "Osteophage": "SCAVENGER", "Scale-eater": "CARNIVORE",
    "Fin-eater": "CARNIVORE", "Egg predator": "CARNIVORE", "Seed predator": "HERBIVORE",
    "Leaf miner": "HERBIVORE", "Gall feeder": "HERBIVORE", "Bore feeder": "HERBIVORE"
}

# --- Helper Functions ---
def clamp(val, min_val, max_val): return max(min_val, min(val, max_val))
def get_distance(x1, y1, x2, y2): return math.hypot(x2 - x1, y2 - y1)

def mutate(val, std_dev, min_val, max_val):
    return clamp(val + random.gauss(0, std_dev), min_val, max_val)

def crossover(val1, val2, std_dev, min_val, max_val):
    blend = random.uniform(0.3, 0.7)
    child_val = val1 * blend + val2 * (1 - blend)
    return mutate(child_val, std_dev, min_val, max_val)

# --- Classes ---
class Plant:
    def __init__(self, x, y):
        self.x, self.y, self.energy, self.radius = x, y, PLANT_ENERGY, 3
    def draw(self, screen): pygame.draw.circle(screen, PLANT_COLOR, (int(self.x), int(self.y)), self.radius)

class Corpse:
    def __init__(self, x, y, energy):
        self.x, self.y, self.energy, self.radius, self.decay = x, y, energy, 4, 1500
    def update(self):
        self.decay -= 1
        return self.decay <= 0 or self.energy <= 0
    def draw(self, screen):
        pygame.draw.circle(screen, (100, 70, 50), (int(self.x), int(self.y)), self.radius)
        pygame.draw.line(screen, (50, 30, 20), (self.x-2, self.y-2), (self.x+2, self.y+2), 1)
        pygame.draw.line(screen, (50, 30, 20), (self.x-2, self.y+2), (self.x+2, self.y-2), 1)

class WarningSignal:
    def __init__(self, x, y, species_id):
        self.x, self.y, self.species_id = x, y, species_id
        self.radius = 0
        self.max_radius = 80
        self.timer = 30
        
    def update(self):
        self.radius += 3
        self.timer -= 1
        return self.timer <= 0
        
    def draw(self, screen):
        alpha = int(255 * (self.timer / 30))
        color = (255, 100, 100, alpha)
        s = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (self.radius, self.radius), self.radius, 2)
        screen.blit(s, (int(self.x - self.radius), int(self.y - self.radius)))

class Species:
    def __init__(self, id, parent_id, traits, color):
        self.id, self.parent_id, self.color, self.population, self.age = id, parent_id, color, 0, 0
        self.avg_speed, self.avg_sense, self.avg_body = traits['speed'], traits['sense'], traits['body_size']
        self.avg_legs, self.avg_leg_len = traits['num_legs'], traits['leg_length']
        self.avg_armor, self.avg_aggression = traits.get('armor', 1.0), traits.get('aggression', 1.0)
        self.avg_mating_signal = traits.get('mating_signal', 0.5)
        self.avg_efficiency = traits.get('efficiency', 1.0)
        self.avg_agility = traits.get('agility', 1.0)
        self.avg_stealth = traits.get('stealth', 0.0)
        self.avg_toxicity = traits.get('toxicity', 0.0)
        # Behavior traits
        self.avg_social = traits.get('social_tendency', 0.5)
        self.avg_cooperation = traits.get('cooperation', 0.5)
        self.avg_parental = traits.get('parental_care', 0.5)
        self.avg_territorial = traits.get('territoriality', 0.5)

class SpeciesManager:
    def __init__(self):
        self.species, self.next_id, self.recent_events = {}, 0, []
        
    def create_species(self, parent_id, traits, color):
        new_id = self.next_id
        self.next_id += 1
        self.species[new_id] = Species(new_id, parent_id, traits, color)
        self.species[new_id].population += 1
        if parent_id != -1:
            event = f"Sp {new_id} branched from Sp {parent_id}"
            self.recent_events.append(event)
            if len(self.recent_events) > 5: self.recent_events.pop(0)
        return new_id
        
    def check_speciation(self, species_id, traits):
        sp = self.species[species_id]
        diff = ((traits['speed'] - sp.avg_speed) / 1.5)**2 + \
               ((traits['sense'] - sp.avg_sense) / 15)**2 + \
               ((traits['body_size'] - sp.avg_body) / 1.5)**2 + \
               ((traits['mating_signal'] - sp.avg_mating_signal) / 0.1)**2 + \
               ((traits['social_tendency'] - sp.avg_social) / 0.2)**2 + \
               ((traits['cooperation'] - sp.avg_cooperation) / 0.2)**2
               
        if diff > 3.5:
            new_color = (clamp(sp.color[0]+random.randint(-40,40),30,255), 
                         clamp(sp.color[1]+random.randint(-40,40),30,255), 
                         clamp(sp.color[2]+random.randint(-40,40),30,255))
            return self.create_species(species_id, traits, new_color)
        else:
            alpha = 0.05
            for key in ['speed', 'sense', 'body_size', 'leg_length', 'armor', 'aggression', 
                        'mating_signal', 'efficiency', 'agility', 'stealth', 'toxicity',
                        'social_tendency', 'cooperation', 'parental_care', 'territoriality']:
                attr = f"avg_{key.replace('_tendency', '').replace('_care', '')}"
                if attr == 'avg_social': attr = 'avg_social'
                if attr == 'avg_parental': attr = 'avg_parental'
                if hasattr(sp, attr):
                    setattr(sp, attr, getattr(sp, attr) * (1 - alpha) + traits[key] * alpha)
            sp.avg_legs = sp.avg_legs * (1 - alpha) + traits['num_legs'] * alpha
            return species_id
            
    def add_birth(self, species_id):
        if species_id in self.species: self.species[species_id].population += 1
    def add_death(self, species_id):
        if species_id in self.species: self.species[species_id].population -= 1
    def update_ages(self):
        for sp in self.species.values(): sp.age += 1

class Creature:
    _id_counter = 0
    def __init__(self, x, y, genes, species_id, species_color, diet_specific, 
                 sex='A', rep_mode='ASEXUAL', parent_id=-1, generation=0):
        Creature._id_counter += 1
        self.id = Creature._id_counter
        self.parent_id = parent_id
        self.generation = generation
        
        self.x, self.y, self.energy, self.age = x, y, STARTING_ENERGY, 0
        self.max_age = random.randint(1800, 3000)
        
        # Core Genetics
        self.speed, self.sense, self.body_size = genes['speed'], genes['sense'], genes['body_size']
        self.num_legs, self.leg_length = genes['num_legs'], genes['leg_length']
        self.armor, self.aggression = genes.get('armor', 1.0), genes.get('aggression', 1.0)
        self.mating_signal = genes.get('mating_signal', 0.5)
        
        # Evolutionary Traits
        self.efficiency = genes.get('efficiency', 1.0)
        self.agility = genes.get('agility', 1.0)
        self.stealth = genes.get('stealth', 0.0)
        self.toxicity = genes.get('toxicity', 0.0)
        
        # Behavior Traits
        self.social_tendency = genes.get('social_tendency', 0.5)
        self.cooperation = genes.get('cooperation', 0.5)
        self.parental_care = genes.get('parental_care', 0.5)
        self.territoriality = genes.get('territoriality', 0.5)
        
        # Physics
        self.mass = self.body_size * (1 + self.num_legs * 0.1)
        self.effective_speed = self.speed / (1 + self.mass * 0.05)
        self.effective_turn = 0.2 * self.agility / (1 + self.mass * 0.02)
        self.metabolism_cost = (0.1 + self.mass * 0.01 + self.effective_speed * 0.02) / self.efficiency
        
        self.sex = sex
        self.reproduction_mode = rep_mode
        self.mating_cooldown = 0
        
        self.diet_specific, self.diet_category = diet_specific, DIET_MAP[diet_specific]
        self.species_id, self.species_color = species_id, species_color
        self.angle = random.uniform(0, 2 * math.pi)
        
        # Behavior State
        self.state = 'WANDER'  # WANDER, FLEE, HUNT, FLOCK, MATE_DISPLAY, AMBUSH, PARENT
        self.state_timer = 0
        self.flee_target = None
        self.hunt_target = None
        self.mate_display_timer = 0
        self.offspring = []
        self.territory_center = None
        self.ambush_timer = 0
        
        # Visual trails
        self.trail = []

    def get_predators_nearby(self, creatures):
        predators = []
        for c in creatures:
            if c is self: continue
            if c.diet_category in ["CARNIVORE", "OMNIVORE", "PARASITE"]:
                if c.species_id != self.species_id:  # Not cannibal
                    d = get_distance(self.x, self.y, c.x, c.y)
                    effective_sense = max(15, c.sense * (1 - self.stealth))
                    if d < effective_sense:
                        predators.append((c, d))
        return predators

    def get_prey_nearby(self, creatures):
        prey = []
        for c in creatures:
            if c is self or c.energy <= 0: continue
            if self.diet_specific == "Cannibal" and c.species_id != self.species_id: continue
            if c.diet_category in ["HERBIVORE", "OMNIVORE"] or (self.diet_specific == "Cannibal" and c.species_id == self.species_id):
                d = get_distance(self.x, self.y, c.x, c.y)
                if d < self.sense:
                    prey.append((c, d))
        return prey

    def get_flockmates(self, creatures):
        flockmates = []
        if self.social_tendency < 0.3: return flockmates
        for c in creatures:
            if c is self: continue
            if c.species_id == self.species_id:
                d = get_distance(self.x, self.y, c.x, c.y)
                if d < self.sense * 0.7:
                    flockmates.append((c, d))
        return flockmates

    def get_pack_hunters(self, creatures, target):
        pack = []
        if self.cooperation < 0.4: return pack
        for c in creatures:
            if c is self: continue
            if c.species_id == self.species_id and c.diet_category in ["CARNIVORE", "OMNIVORE"]:
                d_to_target = get_distance(c.x, c.y, target.x, target.y)
                if d_to_target < self.sense:
                    pack.append(c)
        return pack

    def update_behavior(self, plants, creatures, corpses, warning_signals):
        # Check for predators (fear response)
        if self.diet_category in ["HERBIVORE", "OMNIVORE", "DETRITIVORE", "SCAVENGER"]:
            predators = self.get_predators_nearby(creatures)
            if predators:
                closest_predator, pred_dist = min(predators, key=lambda x: x[1])
                if pred_dist < self.sense * 0.8:
                    self.state = 'FLEE'
                    self.flee_target = closest_predator
                    self.state_timer = 60
                    
                    # Emit warning signal
                    if random.random() < 0.3 and self.social_tendency > 0.5:
                        warning_signals.append(WarningSignal(self.x, self.y, self.species_id))
        
        # Check for warning signals
        for signal in warning_signals:
            if signal.species_id == self.species_id:
                d = get_distance(self.x, self.y, signal.x, signal.y)
                if d < signal.radius:
                    self.state = 'FLEE'
                    self.state_timer = 40
                    break

        # Hunting behavior (ambush vs pursuit)
        if self.diet_category in ["CARNIVORE", "OMNIVORE"]:
            prey_list = self.get_prey_nearby(creatures)
            if prey_list:
                closest_prey, prey_dist = min(prey_list, key=lambda x: x[1])
                
                # Ambush predator (high stealth, low speed)
                if self.stealth > 0.5 and self.effective_speed < 2.5:
                    if prey_dist < self.sense * 0.4:
                        self.state = 'AMBUSH'
                        self.hunt_target = closest_prey
                        self.ambush_timer = 120
                # Pursuit predator (high speed, high agility)
                elif self.effective_speed > 3.0 and self.agility > 1.2:
                    self.state = 'HUNT'
                    self.hunt_target = closest_prey
                    self.state_timer = 100

        # Flocking behavior
        if self.social_tendency > 0.5 and self.state not in ['FLEE', 'HUNT', 'AMBUSH']:
            flockmates = self.get_flockmates(creatures)
            if len(flockmates) >= 2:
                self.state = 'FLOCK'
                self.state_timer = 80

        # Parental care
        if self.parental_care > 0.5 and self.offspring:
            living_offspring = [o for o in self.offspring if o.energy > 0]
            if living_offspring:
                self.state = 'PARENT'
                self.state_timer = 100

        # Mating display
        if self.state == 'WANDER' and self.energy > REPRODUCE_THRESHOLD and self.mating_cooldown <= 0:
            if self.reproduction_mode in ['SEXUAL', 'BOTH']:
                if random.random() < 0.1:  # 10% chance to start display
                    self.state = 'MATE_DISPLAY'
                    self.mate_display_timer = 60

    def get_movement_target(self, plants, creatures, corpses):
        target_type, target_obj, target_dist = None, None, self.sense
        
        # State-based targeting
        if self.state == 'FLEE' and self.flee_target:
            # Move away from predator
            dx = self.x - self.flee_target.x
            dy = self.y - self.flee_target.y
            flee_angle = math.atan2(dy, dx)
            self.angle = flee_angle
            return None, None, None
            
        elif self.state == 'HUNT' and self.hunt_target:
            return 'creature', self.hunt_target, get_distance(self.x, self.y, self.hunt_target.x, self.hunt_target.y)
            
        elif self.state == 'AMBUSH' and self.hunt_target:
            # Stay still, wait for prey
            self.effective_speed = 0
            return 'creature', self.hunt_target, get_distance(self.x, self.y, self.hunt_target.x, self.hunt_target.y)
            
        elif self.state == 'FLOCK':
            # Move toward center of flock
            flockmates = self.get_flockmates(creatures)
            if flockmates:
                avg_x = sum(f[0].x for f in flockmates) / len(flockmates)
                avg_y = sum(f[0].y for f in flockmates) / len(flockmates)
                dx, dy = avg_x - self.x, avg_y - self.y
                target_angle = math.atan2(dy, dx)
                self.angle += (target_angle - self.angle) * 0.1
            return None, None, None
            
        elif self.state == 'PARENT' and self.offspring:
            # Stay near offspring
            living_offspring = [o for o in self.offspring if o.energy > 0]
            if living_offspring:
                closest_offspring = min(living_offspring, key=lambda o: get_distance(self.x, self.y, o.x, o.y))
                d = get_distance(self.x, self.y, closest_offspring.x, closest_offspring.y)
                if d > self.body_size * 3:
                    dx, dy = closest_offspring.x - self.x, closest_offspring.y - self.y
                    target_angle = math.atan2(dy, dx)
                    self.angle += (target_angle - self.angle) * 0.15
            return None, None, None
            
        elif self.state == 'MATE_DISPLAY':
            # Spin in circles
            self.angle += 0.3
            return None, None, None
        
        # Default foraging behavior
        if self.diet_category in ["HERBIVORE", "OMNIVORE"]:
            for p in plants:
                d = get_distance(self.x, self.y, p.x, p.y)
                if d < target_dist:
                    target_dist, target_obj, target_type = d, p, 'plant'
                    
        if self.diet_category in ["CARNIVORE", "OMNIVORE", "PARASITE"]:
            for c in creatures:
                if c is self or c.energy <= 0: continue
                if self.diet_specific == "Cannibal" and c.species_id != self.species_id: continue
                effective_sense = max(15, self.sense * (1 - c.stealth))
                d = get_distance(self.x, self.y, c.x, c.y)
                if d < effective_sense and d < target_dist:
                    target_dist, target_obj, target_type = d, c, 'creature'
                    
        if self.diet_category in ["DETRITIVORE", "SCAVENGER"]:
            for corpse in corpses:
                d = get_distance(self.x, self.y, corpse.x, corpse.y)
                if d < target_dist:
                    target_dist, target_obj, target_type = d, corpse, 'corpse'
                    
        return target_type, target_obj, target_dist

    def reproduce(self, mate, new_creatures, lineage_lines, species_manager):
        self.energy /= 2
        child_genes = {}
        
        trait_params = {
            'speed': (0.2, 0.5, 6.0), 'sense': (2.0, 10.0, 150.0), 
            'body_size': (0.2, 3.0, 10.0), 'leg_length': (0.3, 2.0, 12.0),
            'armor': (0.2, 0.1, 5.0), 'aggression': (0.2, 0.1, 5.0),
            'efficiency': (0.05, 0.5, 2.0), 'agility': (0.1, 0.5, 3.0),
            'stealth': (0.03, 0.0, 0.8), 'toxicity': (0.2, 0.0, 5.0),
            'social_tendency': (0.05, 0.0, 1.0), 'cooperation': (0.05, 0.0, 1.0),
            'parental_care': (0.05, 0.0, 1.0), 'territoriality': (0.05, 0.0, 1.0)
        }
        
        if mate:
            self.energy *= 0.8
            mate.energy /= 2
            mate.energy *= 0.8
            mate.mating_cooldown = MATING_COOLDOWN
            
            for gene, (std, min_v, max_v) in trait_params.items():
                val1, val2 = getattr(self, gene), getattr(mate, gene)
                child_genes[gene] = crossover(val1, val2, std, min_v, max_v)
                
            child_genes['num_legs'] = clamp(int(crossover(self.num_legs, mate.num_legs, 0.5, 2, 8)), 2, 8)
            child_genes['mating_signal'] = crossover(self.mating_signal, mate.mating_signal, 0.03, 0, 1)
            
            if self.reproduction_mode == 'SEXUAL' and mate.reproduction_mode == 'SEXUAL':
                child_sex, child_rep = random.choice(['M', 'F']), 'SEXUAL'
            else:
                child_sex, child_rep = random.choice(['M', 'F', 'H']), random.choice(['SEXUAL', 'BOTH'])
                
            lineage_lines.append({'start': (self.x, self.y), 'end': (mate.x, mate.y), 'timer': 30})
        else:
            for gene, (std, min_v, max_v) in trait_params.items():
                child_genes[gene] = mutate(getattr(self, gene), std, min_v, max_v)
                
            child_genes['num_legs'] = clamp(int(mutate(self.num_legs, 0.5, 2, 8)), 2, 8)
            child_genes['mating_signal'] = mutate(self.mating_signal, 0.03, 0, 1)
            child_sex, child_rep = self.sex, self.reproduction_mode

        new_species_id = species_manager.check_speciation(self.species_id, child_genes)
        new_species_color = species_manager.species[new_species_id].color
        
        child = Creature(self.x, self.y, child_genes, new_species_id, new_species_color, 
                         self.diet_specific if random.random() > 0.05 else random.choice(list(DIET_MAP.keys())),
                         sex=child_sex, rep_mode=child_rep, parent_id=self.id, generation=self.generation+1)
        new_creatures.append(child)
        species_manager.add_birth(new_species_id)
        
        # Track offspring for parental care
        if self.parental_care > 0.5:
            self.offspring.append(child)
            if len(self.offspring) > 3:
                self.offspring.pop(0)
        
        lineage_lines.append({'start': (self.x, self.y), 'end': (child.x, child.y), 'timer': 40})
        self.mating_cooldown = MATING_COOLDOWN

    def update(self, plants, creatures, corpses, new_creatures, dead_creatures, lineage_lines, species_manager, warning_signals):
        self.age += 1
        if self.mating_cooldown > 0: self.mating_cooldown -= 1
        
        # Update state timer
        if self.state_timer > 0:
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = 'WANDER'
                self.effective_speed = self.speed / (1 + self.mass * 0.05)  # Reset speed
        
        # Update behavior
        self.update_behavior(plants, creatures, corpses, warning_signals)
        
        # Metabolism
        behavior_cost = 0
        if self.state == 'FLEE': behavior_cost = 0.1
        elif self.state == 'HUNT': behavior_cost = 0.05
        elif self.state == 'MATE_DISPLAY': behavior_cost = 0.08
        
        self.energy -= self.metabolism_cost + behavior_cost

        if self.energy <= 0 or self.age > self.max_age:
            corpses.append(Corpse(self.x, self.y, 10 + self.mass * 2))
            dead_creatures.append(self)
            return

        # Reproduction
        if self.state == 'MATE_DISPLAY':
            self.mate_display_timer -= 1
            if self.mate_display_timer <= 0:
                if self.reproduction_mode in ['SEXUAL', 'BOTH']:
                    mate = self.find_mate(creatures)
                    if mate:
                        self.reproduce(mate, new_creatures, lineage_lines, species_manager)
                        self.state = 'WANDER'
                elif self.reproduction_mode == 'ASEXUAL':
                    self.reproduce(None, new_creatures, lineage_lines, species_manager)
                    self.state = 'WANDER'
        elif self.energy > REPRODUCE_THRESHOLD and self.mating_cooldown <= 0 and self.state == 'WANDER':
            if self.reproduction_mode == 'ASEXUAL':
                self.reproduce(None, new_creatures, lineage_lines, species_manager)

        # Movement
        target_type, target_obj, target_dist = self.get_movement_target(plants, creatures, corpses)

        if target_obj and self.state not in ['FLEE', 'AMBUSH', 'MATE_DISPLAY']:
            dx, dy = target_obj.x - self.x, target_obj.y - self.y
            target_angle = math.atan2(dy, dx)
            angle_diff = (target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            self.angle += angle_diff * min(0.5, self.effective_turn)
        elif self.state == 'WANDER':
            self.angle += random.uniform(-0.3, 0.3) * min(0.5, self.effective_turn)

        # Apply movement (unless ambushing)
        if self.state != 'AMBUSH':
            move_speed = self.effective_speed
            if self.state == 'FLEE': move_speed *= 1.3  # Flee faster
            
            self.x += math.cos(self.angle) * move_speed
            self.y += math.sin(self.angle) * move_speed
            self.x %= WIDTH
            self.y %= HEIGHT
            
            # Trail for fleeing creatures
            if self.state == 'FLEE':
                self.trail.append((self.x, self.y, 10))
                if len(self.trail) > 5:
                    self.trail.pop(0)

        # Eating/Attacking
        if target_type == 'plant' and target_dist < self.body_size + target_obj.radius:
            self.energy += target_obj.energy
            if target_obj in plants: plants.remove(target_obj)
            
        elif target_type == 'creature' and target_dist < self.body_size + target_obj.body_size:
            if self.diet_category == "PARASITE":
                drain = 3
                target_obj.energy -= drain
                self.energy += drain * 0.8
            else:
                damage = 10 * self.aggression
                
                # Pack hunting bonus
                if self.state == 'HUNT':
                    pack = self.get_pack_hunters(creatures, target_obj)
                    if len(pack) >= 2:
                        damage *= 1 + (len(pack) * 0.2)  # 20% bonus per pack member
                
                actual_damage = max(2, damage - target_obj.armor)
                target_obj.energy -= actual_damage
                self.energy += actual_damage * 0.5
                
                if target_obj.toxicity > 0:
                    self.energy -= target_obj.toxicity * 5
                    
                if target_obj.energy <= 0:
                    corpses.append(Corpse(target_obj.x, target_obj.y, 10 + target_obj.mass * 2))
                    if target_obj not in dead_creatures: dead_creatures.append(target_obj)
                    
        elif target_type == 'corpse' and target_dist < self.body_size + target_obj.radius:
            eat_amount = min(5, target_obj.energy)
            self.energy += eat_amount
            target_obj.energy -= eat_amount
            if target_obj.energy <= 0 and target_obj in corpses: corpses.remove(target_obj)

    def find_mate(self, creatures):
        if self.reproduction_mode == 'ASEXUAL' or self.sex == 'A': return None
        for c in creatures:
            if c is self or c.species_id != self.species_id: continue
            if c.mating_cooldown > 0 or c.energy < REPRODUCE_THRESHOLD * 0.8: continue
            if self.sex == 'M' and c.sex not in ['F', 'H']: continue
            if self.sex == 'F' and c.sex not in ['M', 'H']: continue
            if self.sex == 'H' and c.sex == 'A': continue
            if abs(self.mating_signal - c.mating_signal) > 0.15: continue
            if get_distance(self.x, self.y, c.x, c.y) < self.sense: return c
        return None

    def draw(self, screen):
        cat_color = CATEGORY_COLORS.get(self.diet_category, (200, 200, 200))
        
        stealth_factor = 1 - (self.stealth * 0.6)
        body_color = (int(cat_color[0] * stealth_factor), 
                      int(cat_color[1] * stealth_factor), 
                      int(cat_color[2] * stealth_factor))
        
        # Draw trail for fleeing creatures
        if self.state == 'FLEE':
            for i, (tx, ty, alpha) in enumerate(self.trail):
                trail_color = (255, 100, 100, int(alpha * 25))
                s = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(s, trail_color, (2, 2), 2)
                screen.blit(s, (int(tx - 2), int(ty - 2)))
        
        # Draw body
        points = []
        num_sides = max(3, self.num_legs)
        for i in range(num_sides):
            angle_offset = self.angle + (i * 2 * math.pi / num_sides)
            points.append((self.x + math.cos(angle_offset) * self.body_size, 
                           self.y + math.sin(angle_offset) * self.body_size))
        pygame.draw.polygon(screen, body_color, points)
        
        # Toxicity glow
        if self.toxicity > 1.0:
            pygame.draw.circle(screen, (255, 255, 0), (int(self.x), int(self.y)), int(self.body_size + 2), 1)
        
        # Mating display visual (spinning lines)
        if self.state == 'MATE_DISPLAY':
            for i in range(4):
                display_angle = self.angle + (i * math.pi / 2)
                end_x = self.x + math.cos(display_angle) * (self.body_size + 5)
                end_y = self.y + math.sin(display_angle) * (self.body_size + 5)
                pygame.draw.line(screen, (255, 200, 100), (int(self.x), int(self.y)), (int(end_x), int(end_y)), 2)
        
        # Draw legs
        for i in range(self.num_legs):
            angle_offset = self.angle + (i * 2 * math.pi / self.num_legs)
            walk_phase = (self.age * self.effective_speed * 0.2) + (i * math.pi / self.num_legs)
            leg_len = self.leg_length * (0.8 + 0.2 * math.sin(walk_phase))
            start_x = self.x + math.cos(angle_offset) * self.body_size * 0.85
            start_y = self.y + math.sin(angle_offset) * self.body_size * 0.85
            end_x = start_x + math.cos(angle_offset) * leg_len
            end_y = start_y + math.sin(angle_offset) * leg_len
            pygame.draw.line(screen, self.species_color, (int(start_x), int(start_y)), (int(end_x), int(end_y)), 2)
            
        # Sex indicator
        if self.sex == 'M': pygame.draw.circle(screen, (50, 150, 255), (int(self.x), int(self.y - self.body_size - 4)), 2)
        elif self.sex == 'F': pygame.draw.circle(screen, (255, 100, 150), (int(self.x), int(self.y - self.body_size - 4)), 2)
        elif self.sex == 'H': pygame.draw.circle(screen, (200, 100, 255), (int(self.x), int(self.y - self.body_size - 4)), 2)

# --- Main Simulation ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Artificial Life: Complex Behaviors")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 15)
    font_small = pygame.font.SysFont("monospace", 13)

    plants = [Plant(random.uniform(0, WIDTH), random.uniform(0, HEIGHT)) for _ in range(200)]
    corpses, lineage_lines, warning_signals = [], [], []
    species_manager = SpeciesManager()
    creatures = []

    initial_species_ids = []
    for _ in range(10):
        genes = {
            'speed': random.uniform(1.5, 3.5), 'sense': random.uniform(30, 80),
            'body_size': random.uniform(4, 7), 'num_legs': random.randint(3, 6),
            'leg_length': random.uniform(4, 8), 'armor': random.uniform(0.5, 3.0),
            'aggression': random.uniform(0.5, 3.0), 'mating_signal': random.uniform(0.2, 0.8),
            'efficiency': random.uniform(0.8, 1.5), 'agility': random.uniform(0.8, 1.5),
            'stealth': random.uniform(0.0, 0.4), 'toxicity': random.uniform(0.0, 1.0),
            'social_tendency': random.uniform(0.2, 0.8), 'cooperation': random.uniform(0.2, 0.8),
            'parental_care': random.uniform(0.2, 0.8), 'territoriality': random.uniform(0.2, 0.8)
        }
        color = (random.randint(80, 255), random.randint(80, 255), random.randint(80, 255))
        sp_id = species_manager.create_species(-1, genes, color)
        initial_species_ids.append(sp_id)

    for _ in range(120):
        sp_id = random.choice(initial_species_ids)
        sp = species_manager.species[sp_id]
        genes = {
            'speed': clamp(sp.avg_speed + random.uniform(-0.5, 0.5), 0.5, 6.0),
            'sense': clamp(sp.avg_sense + random.uniform(-10, 10), 10, 150),
            'body_size': clamp(sp.avg_body + random.uniform(-1, 1), 3, 10),
            'num_legs': clamp(int(sp.avg_legs + random.choice([-1, 0, 0, 1])), 2, 8),
            'leg_length': clamp(sp.avg_leg_len + random.uniform(-1, 1), 2, 12),
            'armor': clamp(sp.avg_armor + random.uniform(-0.5, 0.5), 0.1, 5.0),
            'aggression': clamp(sp.avg_aggression + random.uniform(-0.5, 0.5), 0.1, 5.0),
            'mating_signal': clamp(sp.avg_mating_signal + random.uniform(-0.1, 0.1), 0, 1),
            'efficiency': clamp(sp.avg_efficiency + random.uniform(-0.2, 0.2), 0.5, 2.0),
            'agility': clamp(sp.avg_agility + random.uniform(-0.3, 0.3), 0.5, 3.0),
            'stealth': clamp(sp.avg_stealth + random.uniform(-0.1, 0.1), 0.0, 0.8),
            'toxicity': clamp(sp.avg_toxicity + random.uniform(-0.3, 0.3), 0.0, 5.0),
            'social_tendency': clamp(sp.avg_social + random.uniform(-0.2, 0.2), 0.0, 1.0),
            'cooperation': clamp(sp.avg_cooperation + random.uniform(-0.2, 0.2), 0.0, 1.0),
            'parental_care': clamp(sp.avg_parental + random.uniform(-0.2, 0.2), 0.0, 1.0),
            'territoriality': clamp(sp.avg_territorial + random.uniform(-0.2, 0.2), 0.0, 1.0)
        }
        diet = random.choice(list(DIET_MAP.keys()))
        sex = random.choice(['M', 'F', 'A', 'H'])
        rep_mode = 'ASEXUAL' if sex == 'A' else random.choice(['SEXUAL', 'BOTH'])
        
        c = Creature(random.uniform(0, WIDTH), random.uniform(0, HEIGHT), genes, sp_id, sp.color, diet, sex, rep_mode)
        creatures.append(c)

    paused = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: paused = not paused
                if event.key == pygame.K_r: main()

        if not paused:
            if len(plants) < MAX_PLANTS:
                for _ in range(PLANT_SPAWN_RATE):
                    plants.append(Plant(random.uniform(0, WIDTH), random.uniform(0, HEIGHT)))

            for corpse in corpses[:]:
                if corpse.update(): corpses.remove(corpse)
                
            for signal in warning_signals[:]:
                if signal.update(): warning_signals.remove(signal)

            new_creatures, dead_creatures = [], []
            for creature in creatures:
                if creature.energy > 0:
                    creature.update(plants, creatures, corpses, new_creatures, dead_creatures, lineage_lines, species_manager, warning_signals)
            
            creatures.extend(new_creatures)
            for dead in dead_creatures:
                if dead in creatures:
                    creatures.remove(dead)
                    species_manager.add_death(dead.species_id)
                    
            species_manager.update_ages()
            
            for line in lineage_lines[:]:
                line['timer'] -= 1
                if line['timer'] <= 0: lineage_lines.remove(line)

            if len(creatures) == 0:
                for _ in range(30):
                    sp_id = random.choice(initial_species_ids)
                    sp = species_manager.species[sp_id]
                    genes = {'speed': sp.avg_speed, 'sense': sp.avg_sense, 'body_size': sp.avg_body, 'num_legs': int(sp.avg_legs), 'leg_length': sp.avg_leg_len, 'armor': sp.avg_armor, 'aggression': sp.avg_aggression, 'mating_signal': sp.avg_mating_signal, 'efficiency': sp.avg_efficiency, 'agility': sp.avg_agility, 'stealth': sp.avg_stealth, 'toxicity': sp.avg_toxicity, 'social_tendency': sp.avg_social, 'cooperation': sp.avg_cooperation, 'parental_care': sp.avg_parental, 'territoriality': sp.avg_territorial}
                    diet = random.choice(list(DIET_MAP.keys()))
                    sex = random.choice(['M', 'F', 'A', 'H'])
                    rep_mode = 'ASEXUAL' if sex == 'A' else random.choice(['SEXUAL', 'BOTH'])
                    c = Creature(random.uniform(0, WIDTH), random.uniform(0, HEIGHT), genes, sp_id, sp.color, diet, sex, rep_mode)
                    creatures.append(c)
                    species_manager.add_birth(sp_id)

        # --- Drawing ---
        screen.fill(BG_COLOR)
        for p in plants: p.draw(screen)
        for c in corpses: c.draw(screen)
        
        for signal in warning_signals: signal.draw(screen)

        for line in lineage_lines:
            alpha = min(255, line['timer'] * 8)
            color = (100, 200, 255, alpha)
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(s, color, line['start'], line['end'], 1)
            screen.blit(s, (0, 0))

        for c in creatures: c.draw(screen)

        # --- UI Overlay ---
        pygame.draw.rect(screen, UI_BG, (10, 10, 360, 210))
        pygame.draw.rect(screen, (80, 80, 80), (10, 10, 360, 210), 2)
        
        if creatures:
            avg_speed = sum(c.effective_speed for c in creatures) / len(creatures)
            avg_social = sum(c.social_tendency for c in creatures) / len(creatures)
            avg_coop = sum(c.cooperation for c in creatures) / len(creatures)
            avg_parental = sum(c.parental_care for c in creatures) / len(creatures)
            max_gen = max(c.generation for c in creatures)
            
            state_counts = {'WANDER':0, 'FLEE':0, 'HUNT':0, 'FLOCK':0, 'MATE_DISPLAY':0, 'AMBUSH':0, 'PARENT':0}
            for c in creatures:
                state_counts[c.state] += 1
        else:
            avg_speed = avg_social = avg_coop = avg_parental = max_gen = 0
            state_counts = {'WANDER':0, 'FLEE':0, 'HUNT':0, 'FLOCK':0, 'MATE_DISPLAY':0, 'AMBUSH':0, 'PARENT':0}

        stats = [
            f"Pop: {len(creatures)} | Plants: {len(plants)} | Corpses: {len(corpses)}",
            f"Avg Speed: {avg_speed:.2f} | Max Gen: {max_gen}",
            f"Avg Social: {avg_social:.2f} | Avg Cooperation: {avg_coop:.2f}",
            f"Avg Parental Care: {avg_parental:.2f}",
            f"Behaviors: W:{state_counts['WANDER']} F:{state_counts['FLEE']} H:{state_counts['HUNT']}",
            f"          Fl:{state_counts['FLOCK']} M:{state_counts['MATE_DISPLAY']} A:{state_counts['AMBUSH']} P:{state_counts['PARENT']}",
            f"Species: {len(species_manager.species)} | Warning Signals: {len(warning_signals)}",
            f"Controls: [SPACE] Pause | [R] Reset"
        ]
        
        for i, text in enumerate(stats):
            surf = font.render(text, True, TEXT_COLOR)
            screen.blit(surf, (20, 20 + i * 24))

        if paused:
            pause_surf = font.render("PAUSED", True, (255, 50, 50))
            screen.blit(pause_surf, (WIDTH//2 - 30, 20))

        # Right Panel
        panel_x, panel_y, panel_w, panel_h = WIDTH - 280, 10, 270, 380
        pygame.draw.rect(screen, UI_BG, (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(screen, (80, 80, 80), (panel_x, panel_y, panel_w, panel_h), 2)
        
        title_surf = font.render("SPECIES LEADERBOARD", True, (255, 200, 50))
        screen.blit(title_surf, (panel_x + 10, panel_y + 10))
        
        sorted_species = sorted(species_manager.species.values(), key=lambda s: s.population, reverse=True)
        y_offset = panel_y + 35
        for sp in sorted_species[:5]:
            if sp.population == 0 and sp.age > 2000: continue
            pygame.draw.rect(screen, sp.color, (panel_x + 10, y_offset, 15, 15))
            text = f"Sp {sp.id} | Pop {sp.population} | Age {sp.age//1000}k"
            color = TEXT_COLOR if sp.population > 0 else (100, 100, 100)
            surf = font_small.render(text, True, color)
            screen.blit(surf, (panel_x + 35, y_offset))
            y_offset += 22
            
        y_offset += 25
        event_title = font_small.render("LINEAGE EVENTS (Speciation):", True, (100, 200, 255))
        screen.blit(event_title, (panel_x + 10, y_offset))
        y_offset += 20
        for event in species_manager.recent_events:
            surf = font_small.render(event, True, (200, 200, 200))
            screen.blit(surf, (panel_x + 10, y_offset))
            y_offset += 18

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()