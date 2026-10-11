import pygame
import random
import math
import sys
from collections import deque

# ================================
#  CONFIGURATION
# ================================
WIDTH, HEIGHT = 800, 600
BACKGROUND_TOP = (10, 10, 30)
BACKGROUND_BOTTOM = (20, 20, 40)

# Creature settings
INITIAL_CREATURES = 80
CREATURE_SIZE = 8
ENERGY_MAX = 200.0
ENERGY_SPENT_PER_STEP = 0.2
ENERGY_GAIN_FROM_FOOD = 25.0
ENERGY_GAIN_FROM_MEAT = 40.0
REPRODUCE_THRESHOLD = 150.0
REPRODUCE_COST = 80.0
SEXUAL_REPRODUCE_COST = 40.0
MUTATION_RATE = 0.15
MUTATION_AMOUNT = 0.25
SENSE_RANGE_MIN = 40
SENSE_RANGE_MAX = 120
SPEED_MIN = 1.0
SPEED_MAX = 3.0
METABOLISM_MIN = 0.5
METABOLISM_MAX = 2.0
MATE_RANGE_MIN = 30
MATE_RANGE_MAX = 100
BASE_SIZE_MIN = 0.5
BASE_SIZE_MAX = 2.0
AGGRESSION_MIN = 0.0
AGGRESSION_MAX = 1.0
HUNTING_SKILL_MIN = 0.0
HUNTING_SKILL_MAX = 1.0
EVASION_MIN = 0.0
EVASION_MAX = 1.0
SOCIABILITY_MIN = 0.0
SOCIABILITY_MAX = 1.0
FORAGING_EFF_MIN = 0.5
FORAGING_EFF_MAX = 2.0
MEMORY_CAPACITY_MIN = 0
MEMORY_CAPACITY_MAX = 30
MEMORY_DECAY_MIN = 0.0
MEMORY_DECAY_MAX = 0.05
MATURITY_AGE_MIN = 50
MATURITY_AGE_MAX = 200
DISEASE_RESISTANCE_MIN = 0.0
DISEASE_RESISTANCE_MAX = 1.0
REPRODUCTION_COOLDOWN = 50
ATTACK_RANGE_FACTOR = 0.3

# Disease settings
DISEASE_SPREAD_RADIUS_FACTOR = 0.2
DISEASE_INTENSITY_BASE = 0.1
DISEASE_OUTBREAK_CHANCE = 0.001
DISEASE_OUTBREAK_DURATION = 300

# Season settings
SEASON_LENGTH = 1000
SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
SEASON_COLORS = [(100, 255, 100), (255, 255, 100), (255, 150, 50), (150, 200, 255)]
SEASON_FOOD_MOD = [1.5, 1.8, 0.8, 0.4]
SEASON_ENERGY_MOD = [0.8, 0.9, 1.1, 1.3]

# Food settings
INITIAL_FOOD = 250
FOOD_SPAWN_RATE = 0.25
FOOD_RADIUS = 4

# Graph settings
GRAPH_HISTORY = 200
GRAPH_SIZE = (150, 80)
GRAPH_POS = (WIDTH - GRAPH_SIZE[0] - 10, HEIGHT - GRAPH_SIZE[1] - 10)

# ================================
#  DIET & FOOD DEFINITIONS
# ================================
DIET_NAMES = [
    "Herbivore",
    "Carnivore",
    "Omnivore",
    "Frugivore",
    "Insectivore",
    "Detritivore",
    "Sanguivore"
]

DIET_FOOD_MAP = {
    0: {"plant"},
    1: {"meat"},
    2: {"plant", "meat"},
    3: {"fruit"},
    4: {"insect"},
    5: {"detritus"},
    6: {"blood"}
}

FOOD_TYPES = {
    "plant":    (100, 200, 50),
    "meat":     (200, 50, 50),
    "fruit":    (255, 200, 50),
    "insect":   (160, 50, 200),
    "detritus": (140, 110, 60),
    "blood":    (200, 0, 0)
}

DIET_COLORS = [
    (50, 200, 50),   # Herbivore
    (200, 50, 50),   # Carnivore
    (200, 200, 50),  # Omnivore
    (255, 150, 0),   # Frugivore
    (160, 50, 200),  # Insectivore
    (140, 110, 60),  # Detritivore
    (200, 0, 0)      # Sanguivore
]

SEX_COLORS = [(255, 100, 100), (100, 100, 255)]  # female, male

# ================================
#  CLASSES
# ================================
class Creature:
    _next_id = 1

    def __init__(self, x, y, genes=None, parent_id=None, generation=0):
        self.id = Creature._next_id
        Creature._next_id += 1

        self.x = x
        self.y = y
        self.energy = ENERGY_MAX * 0.5
        self.age = 0
        self.alive = True
        self.reproduction_cooldown = 0
        self.is_mating = False
        self.infected = False
        self.infection_timer = 0

        self.parent_id = parent_id
        self.generation = generation

        # ---- Genes (17 total) ----
        if genes is None:
            self.speed = random.uniform(SPEED_MIN, SPEED_MAX)
            self.sense_range = random.uniform(SENSE_RANGE_MIN, SENSE_RANGE_MAX)
            self.shape_type = random.randint(0, 2)
            self.diet_type = random.randint(0, len(DIET_NAMES) - 1)
            self.sex = random.randint(0, 1)
            self.metabolism = random.uniform(METABOLISM_MIN, METABOLISM_MAX)
            self.mate_range = random.uniform(MATE_RANGE_MIN, MATE_RANGE_MAX)
            self.base_size = random.uniform(BASE_SIZE_MIN, BASE_SIZE_MAX)
            self.aggression = random.uniform(AGGRESSION_MIN, AGGRESSION_MAX)
            self.hunting_skill = random.uniform(HUNTING_SKILL_MIN, HUNTING_SKILL_MAX)
            self.evasion = random.uniform(EVASION_MIN, EVASION_MAX)
            self.sociability = random.uniform(SOCIABILITY_MIN, SOCIABILITY_MAX)
            self.foraging_efficiency = random.uniform(FORAGING_EFF_MIN, FORAGING_EFF_MAX)
            self.memory_capacity = random.randint(MEMORY_CAPACITY_MIN, MEMORY_CAPACITY_MAX)
            self.memory_decay = random.uniform(MEMORY_DECAY_MIN, MEMORY_DECAY_MAX)
            self.maturity_age = random.randint(MATURITY_AGE_MIN, MATURITY_AGE_MAX)
            self.disease_resistance = random.uniform(DISEASE_RESISTANCE_MIN, DISEASE_RESISTANCE_MAX)
        else:
            (self.speed, self.sense_range, self.shape_type, self.diet_type,
             self.sex, self.metabolism, self.mate_range, self.base_size,
             self.aggression, self.hunting_skill, self.evasion, self.sociability,
             self.foraging_efficiency, self.memory_capacity, self.memory_decay,
             self.maturity_age, self.disease_resistance) = genes

            # Mutate
            if random.random() < MUTATION_RATE:
                self.speed += random.gauss(0, MUTATION_AMOUNT)
            if random.random() < MUTATION_RATE:
                self.sense_range += random.gauss(0, MUTATION_AMOUNT * 20)
            if random.random() < MUTATION_RATE:
                self.shape_type = (self.shape_type + random.choice([-1, 1])) % 3
            if random.random() < MUTATION_RATE:
                self.diet_type = (self.diet_type + random.choice([-1, 0, 1])) % len(DIET_NAMES)
            if random.random() < MUTATION_RATE:
                self.sex = 1 - self.sex
            if random.random() < MUTATION_RATE:
                self.metabolism += random.gauss(0, 0.1)
            if random.random() < MUTATION_RATE:
                self.mate_range += random.gauss(0, 5)
            if random.random() < MUTATION_RATE:
                self.base_size += random.gauss(0, 0.05)
            if random.random() < MUTATION_RATE:
                self.aggression += random.gauss(0, 0.05)
            if random.random() < MUTATION_RATE:
                self.hunting_skill += random.gauss(0, 0.05)
            if random.random() < MUTATION_RATE:
                self.evasion += random.gauss(0, 0.05)
            if random.random() < MUTATION_RATE:
                self.sociability += random.gauss(0, 0.05)
            if random.random() < MUTATION_RATE:
                self.foraging_efficiency += random.gauss(0, 0.05)
            if random.random() < MUTATION_RATE:
                self.memory_capacity += random.choice([-1, 1])
            if random.random() < MUTATION_RATE:
                self.memory_decay += random.gauss(0, 0.005)
            if random.random() < MUTATION_RATE:
                self.maturity_age += random.choice([-5, 5])
            if random.random() < MUTATION_RATE:
                self.disease_resistance += random.gauss(0, 0.05)

            # Clamp
            self.speed = max(SPEED_MIN, min(SPEED_MAX, self.speed))
            self.sense_range = max(SENSE_RANGE_MIN, min(SENSE_RANGE_MAX, self.sense_range))
            self.metabolism = max(METABOLISM_MIN, min(METABOLISM_MAX, self.metabolism))
            self.mate_range = max(MATE_RANGE_MIN, min(MATE_RANGE_MAX, self.mate_range))
            self.base_size = max(BASE_SIZE_MIN, min(BASE_SIZE_MAX, self.base_size))
            self.aggression = max(AGGRESSION_MIN, min(AGGRESSION_MAX, self.aggression))
            self.hunting_skill = max(HUNTING_SKILL_MIN, min(HUNTING_SKILL_MAX, self.hunting_skill))
            self.evasion = max(EVASION_MIN, min(EVASION_MAX, self.evasion))
            self.sociability = max(SOCIABILITY_MIN, min(SOCIABILITY_MAX, self.sociability))
            self.foraging_efficiency = max(FORAGING_EFF_MIN, min(FORAGING_EFF_MAX, self.foraging_efficiency))
            self.memory_capacity = max(MEMORY_CAPACITY_MIN, min(MEMORY_CAPACITY_MAX, self.memory_capacity))
            self.memory_decay = max(MEMORY_DECAY_MIN, min(MEMORY_DECAY_MAX, self.memory_decay))
            self.maturity_age = max(MATURITY_AGE_MIN, min(MATURITY_AGE_MAX, self.maturity_age))
            self.disease_resistance = max(DISEASE_RESISTANCE_MIN, min(DISEASE_RESISTANCE_MAX, self.disease_resistance))

        self.angle = random.uniform(0, 2 * math.pi)
        self.attack_range = self.sense_range * ATTACK_RANGE_FACTOR

        # Memory
        self.memory = []
        self.memory_timer = 0

        # Trail
        self.trail = deque(maxlen=20)
        self.trail.append((self.x, self.y))

        # Lineage colour
        if parent_id is not None:
            hue = (parent_id * 37 + 180) % 360
        else:
            hue = random.randint(0, 360)
        self.color = pygame.Color(0, 0, 0)
        self.color.hsva = (hue, 80, 90, 100)

        self.edible_foods = DIET_FOOD_MAP[self.diet_type]
        self.is_predator = self.diet_type in (1, 2)

    @property
    def is_mature(self):
        return self.age >= self.maturity_age

    # ---- Sensing ----
    def sense_food(self, food_list):
        nearest = None
        min_dist = self.sense_range
        for food in food_list:
            if food.food_type not in self.edible_foods:
                continue
            dx = food.x - self.x
            dy = food.y - self.y
            dist = math.hypot(dx, dy)
            if dist < min_dist:
                min_dist = dist
                nearest = food
        return nearest, min_dist

    def sense_prey(self, creature_list):
        if not self.is_predator:
            return None, self.sense_range
        nearest = None
        min_dist = self.sense_range
        for other in creature_list:
            if other.id == self.id or not other.alive:
                continue
            if other.diet_type in (1, 2):
                continue
            dx = other.x - self.x
            dy = other.y - self.y
            dist = math.hypot(dx, dy)
            if dist < min_dist:
                min_dist = dist
                nearest = other
        return nearest, min_dist

    def sense_predators(self, creature_list):
        if self.is_predator:
            return None, self.sense_range
        nearest = None
        min_dist = self.sense_range
        for other in creature_list:
            if other.id == self.id or not other.alive:
                continue
            if not other.is_predator:
                continue
            dx = other.x - self.x
            dy = other.y - self.y
            dist = math.hypot(dx, dy)
            if dist < min_dist:
                min_dist = dist
                nearest = other
        return nearest, min_dist

    def sense_infected_nearby(self, creature_list):
        radius = self.sense_range * DISEASE_SPREAD_RADIUS_FACTOR
        nearest = None
        min_dist = radius
        for other in creature_list:
            if other.id == self.id or not other.alive or not other.infected:
                continue
            dx = other.x - self.x
            dy = other.y - self.y
            dist = math.hypot(dx, dy)
            if dist < min_dist:
                min_dist = dist
                nearest = other
        return nearest, min_dist

    # ---- Memory ----
    def remember(self, x, y, food_type):
        if self.memory_capacity == 0:
            return
        for i, (mx, my, ft, _) in enumerate(self.memory):
            if abs(mx - x) < 5 and abs(my - y) < 5 and ft == food_type:
                self.memory[i] = (x, y, food_type, self.memory_timer)
                return
        if len(self.memory) >= self.memory_capacity:
            self.memory.sort(key=lambda t: t[3])
            self.memory.pop(0)
        self.memory.append((x, y, food_type, self.memory_timer))

    def forget_old_memories(self):
        self.memory_timer += 1
        new_mem = []
        for (x, y, ft, t) in self.memory:
            if self.memory_timer - t < 200:
                new_mem.append((x, y, ft, t))
        self.memory = new_mem

    def get_nearest_remembered(self):
        if not self.memory:
            return None, float('inf')
        nearest = None
        min_dist = float('inf')
        for (x, y, ft, _) in self.memory:
            dx = x - self.x
            dy = y - self.y
            dist = math.hypot(dx, dy)
            if dist < min_dist:
                min_dist = dist
                nearest = (x, y, ft)
        return nearest, min_dist

    # ---- Behavior ----
    def move_toward(self, tx, ty):
        target_angle = math.atan2(ty - self.y, tx - self.x)
        angle_diff = target_angle - self.angle
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        turn_factor = 0.05 + 0.15 * self.aggression
        self.angle += angle_diff * turn_factor

    def flee_from(self, fx, fy):
        target_angle = math.atan2(fy - self.y, fx - self.x)
        flee_angle = target_angle + math.pi
        angle_diff = flee_angle - self.angle
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        turn_factor = 0.1 + 0.2 * self.evasion
        self.angle += angle_diff * turn_factor

    def apply_social_forces(self, creature_list):
        if self.sociability < 0.01:
            return
        cohesion_x, cohesion_y = 0, 0
        sep_x, sep_y = 0, 0
        neighbors = 0
        for other in creature_list:
            if other.id == self.id or not other.alive:
                continue
            dx = other.x - self.x
            dy = other.y - self.y
            dist = math.hypot(dx, dy)
            if dist < self.sense_range * 0.5:
                neighbors += 1
                cohesion_x += other.x
                cohesion_y += other.y
                if dist < CREATURE_SIZE * 2 and dist > 0:
                    sep_strength = (CREATURE_SIZE * 2 - dist) / (CREATURE_SIZE * 2)
                    sep_x -= dx / dist * sep_strength * 10
                    sep_y -= dy / dist * sep_strength * 10
        if neighbors > 0:
            self.move_toward(cohesion_x / neighbors, cohesion_y / neighbors)
        if sep_x != 0 or sep_y != 0:
            sep_angle = math.atan2(sep_y, sep_x)
            angle_diff = sep_angle - self.angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            self.angle += angle_diff * 0.1 * self.sociability

    def attack_creature(self, prey, creature_list):
        if not prey.alive:
            return
        dx = prey.x - self.x
        dy = prey.y - self.y
        dist = math.hypot(dx, dy)
        if dist > self.attack_range:
            return
        capture_chance = self.hunting_skill / (self.hunting_skill + prey.evasion + 0.01)
        if random.random() < capture_chance:
            self.energy += ENERGY_GAIN_FROM_MEAT * self.foraging_efficiency
            prey.alive = False
            self.remember(prey.x, prey.y, "meat")

    # ---- Disease ----
    def try_infect(self, disease_intensity):
        if self.infected:
            return
        infect_chance = disease_intensity * (1 - self.disease_resistance) * 0.5
        if random.random() < infect_chance:
            self.infected = True
            self.infection_timer = 0

    # ---- Update ----
    def update(self, food_list, creature_list, season_idx, disease_intensity):
        if not self.alive:
            return

        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1

        # Disease infection from nearby infected creatures
        if not self.infected and disease_intensity > 0:
            near_infected, _ = self.sense_infected_nearby(creature_list)
            if near_infected is not None:
                self.try_infect(disease_intensity)

        # If infected, apply energy penalty
        if self.infected:
            self.infection_timer += 1
            penalty = DISEASE_INTENSITY_BASE * disease_intensity * (1 - self.disease_resistance * 0.5)
            self.energy -= penalty
            if self.energy <= 0:
                self.alive = False
                return

        # ---- Season effects ----
        food_mod = SEASON_FOOD_MOD[season_idx]
        energy_mod = SEASON_ENERGY_MOD[season_idx]

        # Sensing
        target_food, food_dist = self.sense_food(food_list)
        target_prey, prey_dist = self.sense_prey(creature_list)
        target_predator, pred_dist = self.sense_predators(creature_list)

        # Decision making
        if self.is_predator and target_prey is not None and prey_dist < self.attack_range:
            self.attack_creature(target_prey, creature_list)
            self.move_toward(target_prey.x, target_prey.y)
        elif target_food is not None and food_dist < self.sense_range:
            self.move_toward(target_food.x, target_food.y)
        elif target_predator is not None and pred_dist < self.sense_range:
            self.flee_from(target_predator.x, target_predator.y)
        else:
            mem_pos, mem_dist = self.get_nearest_remembered()
            if mem_pos is not None and mem_dist < self.sense_range * 1.5:
                self.move_toward(mem_pos[0], mem_pos[1])
            else:
                self.apply_social_forces(creature_list)
                self.angle += random.uniform(-0.1, 0.1)

        # Move
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

        # Wall bounce
        if self.x < 0:
            self.x = 0
            self.angle = math.pi - self.angle
        elif self.x > WIDTH:
            self.x = WIDTH
            self.angle = math.pi - self.angle
        if self.y < 0:
            self.y = 0
            self.angle = -self.angle
        elif self.y > HEIGHT:
            self.y = HEIGHT
            self.angle = -self.angle

        # Energy cost: base * metabolism * base_size * energy_mod * disease factor
        cost_multiplier = 0.8 if not self.is_mature else 1.0
        disease_cost_factor = 1.0
        if self.infected:
            disease_cost_factor = 1.0 + 0.5 * disease_intensity * (1 - self.disease_resistance * 0.5)
        self.energy -= ENERGY_SPENT_PER_STEP * self.metabolism * self.base_size * cost_multiplier * energy_mod * disease_cost_factor
        self.age += 1

        # Eat food (gain modified by season)
        if target_food is not None and food_dist < CREATURE_SIZE + FOOD_RADIUS:
            gain = ENERGY_GAIN_FROM_FOOD * self.foraging_efficiency * food_mod
            self.energy += gain
            self.remember(target_food.x, target_food.y, target_food.food_type)
            target_food.alive = False

        if self.energy <= 0:
            self.alive = False
            return

        # Trail update
        self.trail.append((self.x, self.y))

        # Reproduction
        if self.is_mature and self.energy >= REPRODUCE_THRESHOLD and self.reproduction_cooldown == 0 and not self.is_mating:
            mate = self.find_mate(creature_list)
            if mate is not None:
                self.reproduce_sexual(mate, creature_list)
            else:
                self.reproduce_asexual(creature_list)

    # ---- Mate finding ----
    def find_mate(self, creature_list):
        best_mate = None
        best_dist = self.mate_range
        for other in creature_list:
            if other.id == self.id or not other.alive or other.is_mating:
                continue
            if other.sex == self.sex:
                continue
            if not other.is_mature:
                continue
            if other.energy < REPRODUCE_THRESHOLD or other.reproduction_cooldown > 0:
                continue
            dx = other.x - self.x
            dy = other.y - self.y
            dist = math.hypot(dx, dy)
            if dist < best_dist:
                best_dist = dist
                best_mate = other
        return best_mate

    # ---- Reproduction ----
    def reproduce_asexual(self, creature_list):
        if self.energy < REPRODUCE_COST:
            return
        self.energy -= REPRODUCE_COST
        genes = (self.speed, self.sense_range, self.shape_type, self.diet_type,
                 self.sex, self.metabolism, self.mate_range, self.base_size,
                 self.aggression, self.hunting_skill, self.evasion, self.sociability,
                 self.foraging_efficiency, self.memory_capacity, self.memory_decay,
                 self.maturity_age, self.disease_resistance)
        child = Creature(
            self.x + random.uniform(-10, 10),
            self.y + random.uniform(-10, 10),
            genes=genes,
            parent_id=self.id,
            generation=self.generation + 1
        )
        child.energy = ENERGY_MAX * 0.3
        creature_list.append(child)
        self.reproduction_cooldown = REPRODUCTION_COOLDOWN

    def reproduce_sexual(self, mate, creature_list):
        if self.energy < SEXUAL_REPRODUCE_COST or mate.energy < SEXUAL_REPRODUCE_COST:
            return
        self.is_mating = True
        mate.is_mating = True

        genes = []
        for i in range(17):
            if random.random() < 0.5:
                genes.append(getattr(self, self._gene_names[i]))
            else:
                genes.append(getattr(mate, self._gene_names[i]))

        child = Creature(
            (self.x + mate.x) / 2 + random.uniform(-5, 5),
            (self.y + mate.y) / 2 + random.uniform(-5, 5),
            genes=genes,
            parent_id=self.id,
            generation=max(self.generation, mate.generation) + 1
        )
        child.energy = ENERGY_MAX * 0.3
        creature_list.append(child)

        self.energy -= SEXUAL_REPRODUCE_COST
        mate.energy -= SEXUAL_REPRODUCE_COST
        self.reproduction_cooldown = REPRODUCTION_COOLDOWN
        mate.reproduction_cooldown = REPRODUCTION_COOLDOWN
        self.is_mating = False
        mate.is_mating = False

    _gene_names = ["speed", "sense_range", "shape_type", "diet_type",
                   "sex", "metabolism", "mate_range", "base_size",
                   "aggression", "hunting_skill", "evasion", "sociability",
                   "foraging_efficiency", "memory_capacity", "memory_decay",
                   "maturity_age", "disease_resistance"]

    # ---- Drawing (FIXED) ----
    def draw(self, screen, selected=False):
        x, y = int(self.x), int(self.y)

        # ---- Glow ----
        energy_ratio = max(0, min(1, self.energy / ENERGY_MAX))
        glow_size = CREATURE_SIZE * self.base_size * (0.5 + 0.5 * energy_ratio) * 2 + 10
        if glow_size > 0:
            glow_surf = pygame.Surface((int(glow_size*2), int(glow_size*2)), pygame.SRCALPHA)
            alpha = int(30 + 40 * energy_ratio)
            # Extract RGB from self.color (ignore its alpha)
            if self.infected:
                col = (min(255, self.color.r + 50), self.color.g, self.color.b)
            else:
                col = (self.color.r, self.color.g, self.color.b)
            pygame.draw.circle(glow_surf, (*col, alpha),
                               (int(glow_size), int(glow_size)), int(glow_size))
            screen.blit(glow_surf, (x - int(glow_size), y - int(glow_size)))

        # ---- Trail ----
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                trail_alpha = int(20 * (i / len(self.trail)))
                if trail_alpha > 0:
                    start = self.trail[i-1]
                    end = self.trail[i]
                    pygame.draw.line(screen, (*self.color[:3], trail_alpha),
                                     (int(start[0]), int(start[1])),
                                     (int(end[0]), int(end[1])), 2)

        # ---- Body ----
        current_size = int(CREATURE_SIZE * self.base_size * (0.5 + 0.5 * energy_ratio))
        if current_size < 2:
            current_size = 2

        # Shape
        if self.shape_type == 0:
            pygame.draw.circle(screen, self.color, (x, y), current_size)
        elif self.shape_type == 1:
            rect = pygame.Rect(x - current_size, y - current_size,
                               2 * current_size, 2 * current_size)
            pygame.draw.rect(screen, self.color, rect)
        else:
            points = [
                (x, y - current_size),
                (x - current_size, y + current_size),
                (x + current_size, y + current_size)
            ]
            pygame.draw.polygon(screen, self.color, points)

        # Diet dot
        inner_r = max(2, current_size // 2)
        pygame.draw.circle(screen, DIET_COLORS[self.diet_type], (x, y), inner_r)

        # Sex dot
        sex_r = max(1, inner_r // 2)
        pygame.draw.circle(screen, SEX_COLORS[self.sex], (x, y), sex_r)

        # Maturity ring
        if self.is_mature:
            pygame.draw.circle(screen, (255, 255, 255), (x, y), current_size + 2, 1)

        # Predator ring
        if self.is_predator:
            pygame.draw.circle(screen, (255, 255, 255), (x, y), current_size + 2, 1)

        # Infection indicator (pulsing red ring)
        if self.infected:
            pulse = abs(math.sin(self.infection_timer * 0.1)) * 3
            pygame.draw.circle(screen, (255, 0, 0), (x, y), current_size + 4 + int(pulse), 2)

        # Selection
        if selected:
            pygame.draw.circle(screen, (255, 255, 255), (x, y), current_size + 4, 2)

# ================================
#  FOOD
# ================================
class Food:
    def __init__(self, x, y, food_type):
        self.x = x
        self.y = y
        self.food_type = food_type
        self.alive = True

    def draw(self, screen):
        glow_radius = FOOD_RADIUS * 2
        glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
        color = FOOD_TYPES[self.food_type]
        pygame.draw.circle(glow_surf, (*color, 30), (glow_radius, glow_radius), glow_radius)
        screen.blit(glow_surf, (int(self.x) - glow_radius, int(self.y) - glow_radius))
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), FOOD_RADIUS)

# ================================
#  FAMILY TREE
# ================================
def build_tree(creatures):
    id_map = {c.id: c for c in creatures}
    children = {}
    roots = []
    for c in creatures:
        if c.parent_id is None or c.parent_id not in id_map:
            roots.append(c)
        else:
            children.setdefault(c.parent_id, []).append(c)
    return roots, children, id_map

def draw_tree(screen, creatures, selected_id=None):
    if not creatures:
        return
    roots, children, id_map = build_tree(creatures)
    if not roots:
        return

    positions = {}
    level_height = 50

    def get_width(node):
        if node.id not in children or not children[node.id]:
            return 1
        return sum(get_width(child) for child in children[node.id])

    def place(node, x, y, x_offset):
        positions[node.id] = (x, y)
        if node.id in children and children[node.id]:
            child_count = len(children[node.id])
            child_widths = [get_width(ch) for ch in children[node.id]]
            total_width = sum(child_widths)
            spacing = max(20, (total_width * 15) / child_count if child_count > 1 else 20)
            start_x = x - (total_width * spacing) / 2
            for child in children[node.id]:
                w = get_width(child)
                child_x = start_x + (w * spacing) / 2
                place(child, child_x, y + level_height, spacing)
                start_x += w * spacing

    total_roots = len(roots)
    root_spacing = max(150, 600 / total_roots if total_roots > 0 else 150)
    start_x = (WIDTH - (total_roots - 1) * root_spacing) / 2
    for i, root in enumerate(roots):
        place(root, start_x + i * root_spacing, 50, root_spacing)

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))

    # Edges
    for c in creatures:
        if c.parent_id is not None and c.parent_id in positions and c.id in positions:
            ppos = positions[c.parent_id]
            cpos = positions[c.id]
            pygame.draw.line(overlay, (150, 150, 150, 150),
                             (int(ppos[0]), int(ppos[1])),
                             (int(cpos[0]), int(cpos[1])), 2)

    # Nodes
    for c in creatures:
        if c.id not in positions:
            continue
        x, y = positions[c.id]
        size = 8
        pygame.draw.circle(overlay, c.color, (int(x), int(y)), size)
        pygame.draw.circle(overlay, DIET_COLORS[c.diet_type], (int(x), int(y)), size//2)
        if selected_id == c.id:
            pygame.draw.circle(overlay, (255, 255, 255), (int(x), int(y)), size+2, 2)

    screen.blit(overlay, (0, 0))
    font = pygame.font.Font(None, 20)
    info = font.render("Family Tree (T to toggle)", True, (200, 200, 200))
    screen.blit(info, (10, 10))

# ================================
#  POPULATION GRAPH
# ================================
def draw_graph(screen, history, color=(100, 200, 255)):
    if len(history) < 2:
        return
    rect = pygame.Rect(GRAPH_POS[0], GRAPH_POS[1], GRAPH_SIZE[0], GRAPH_SIZE[1])
    pygame.draw.rect(screen, (0, 0, 0, 120), rect)
    pygame.draw.rect(screen, (60, 60, 60), rect, 1)

    max_val = max(history) if history else 1
    if max_val == 0:
        max_val = 1
    points = []
    step = max(1, len(history) // GRAPH_SIZE[0])
    for i in range(0, len(history), step):
        x = GRAPH_POS[0] + (i / len(history)) * GRAPH_SIZE[0]
        y = GRAPH_POS[1] + GRAPH_SIZE[1] - (history[i] / max_val) * (GRAPH_SIZE[1] - 5)
        points.append((x, y))
    if len(points) > 1:
        pygame.draw.lines(screen, color, False, points, 2)
    font = pygame.font.Font(None, 16)
    label = font.render(f"Pop: {history[-1]}", True, (200, 200, 200))
    screen.blit(label, (GRAPH_POS[0] + 5, GRAPH_POS[1] + 5))

# ================================
#  ECOSYSTEM MAP
# ================================
def draw_ecosystem_map(screen, creatures, foods, disease_intensity):
    """Draw a heatmap overlay showing creature density, food distribution, and disease."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    grid_size = 20
    cols = WIDTH // grid_size
    rows = HEIGHT // grid_size

    density_grid = [[0]*cols for _ in range(rows)]
    diet_grid = [[[0]*len(DIET_NAMES) for _ in range(cols)] for _ in range(rows)]
    infected_grid = [[0]*cols for _ in range(rows)]

    for c in creatures:
        if not c.alive:
            continue
        gx = int(c.x // grid_size)
        gy = int(c.y // grid_size)
        if 0 <= gx < cols and 0 <= gy < rows:
            density_grid[gy][gx] += 1
            diet_grid[gy][gx][c.diet_type] += 1
            if c.infected:
                infected_grid[gy][gx] += 1

    max_density = max(max(row) for row in density_grid) if any(any(row) for row in density_grid) else 1
    for y in range(rows):
        for x in range(cols):
            val = density_grid[y][x]
            if val > 0:
                intensity = val / max_density
                r = int(255 * intensity)
                g = int(255 * (1 - intensity) * 0.5)
                b = int(255 * (1 - intensity))
                alpha = min(150, int(50 + 100 * intensity))
                pygame.draw.rect(overlay, (r, g, b, alpha),
                                 (x*grid_size, y*grid_size, grid_size, grid_size))

    for f in foods:
        if not f.alive:
            continue
        pygame.draw.circle(overlay, (50, 255, 50, 150), (int(f.x), int(f.y)), 2)

    for y in range(rows):
        for x in range(cols):
            diet_counts = diet_grid[y][x]
            if sum(diet_counts) > 3:
                max_idx = max(range(len(diet_counts)), key=lambda i: diet_counts[i])
                if diet_counts[max_idx] > 0:
                    color = DIET_COLORS[max_idx]
                    cx = x * grid_size + grid_size//2
                    cy = y * grid_size + grid_size//2
                    pygame.draw.circle(overlay, (*color, 100), (cx, cy), 6)

    if disease_intensity > 0.05:
        max_infected = max(max(row) for row in infected_grid) if any(any(row) for row in infected_grid) else 1
        for y in range(rows):
            for x in range(cols):
                val = infected_grid[y][x]
                if val > 0:
                    intensity = val / max_infected
                    alpha = int(50 * intensity * disease_intensity)
                    pygame.draw.rect(overlay, (200, 0, 200, alpha),
                                     (x*grid_size, y*grid_size, grid_size, grid_size))

    pygame.draw.rect(overlay, (200, 200, 200, 150), (0, 0, WIDTH, HEIGHT), 2)
    font = pygame.font.Font(None, 20)
    label = font.render("Ecosystem Map (M to toggle)", True, (200, 200, 200))
    overlay.blit(label, (10, 10))

    screen.blit(overlay, (0, 0))

# ================================
#  SIMULATION
# ================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Advanced ALife - Seasons, Diseases, Ecosystem Map")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    Creature._next_id = 1

    stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT),
              random.randint(1, 2)) for _ in range(100)]

    creatures = []
    for _ in range(INITIAL_CREATURES):
        x = random.randint(20, WIDTH - 20)
        y = random.randint(20, HEIGHT - 20)
        creatures.append(Creature(x, y, parent_id=None, generation=0))

    foods = []
    food_keys = list(FOOD_TYPES.keys())
    for _ in range(INITIAL_FOOD):
        ft = random.choice(food_keys)
        foods.append(Food(random.randint(0, WIDTH), random.randint(0, HEIGHT), ft))

    running = True
    paused = False
    step_count = 0
    show_tree = False
    show_graph = True
    show_map = False
    selected_id = None
    population_history = deque(maxlen=GRAPH_HISTORY)
    population_history.append(len(creatures))

    season_idx = 0
    disease_intensity = 0.0
    disease_outbreak_timer = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                if event.key == pygame.K_r:
                    Creature._next_id = 1
                    creatures.clear()
                    foods.clear()
                    for _ in range(INITIAL_CREATURES):
                        creatures.append(Creature(random.randint(20, WIDTH - 20),
                                                  random.randint(20, HEIGHT - 20)))
                    for _ in range(INITIAL_FOOD):
                        ft = random.choice(food_keys)
                        foods.append(Food(random.randint(0, WIDTH),
                                          random.randint(0, HEIGHT), ft))
                    selected_id = None
                    population_history.clear()
                    population_history.append(len(creatures))
                    disease_intensity = 0.0
                    disease_outbreak_timer = 0
                if event.key == pygame.K_t:
                    show_tree = not show_tree
                if event.key == pygame.K_g:
                    show_graph = not show_graph
                if event.key == pygame.K_m:
                    show_map = not show_map
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                closest = None
                min_d = 20
                for c in creatures:
                    if not c.alive:
                        continue
                    dx = c.x - mx
                    dy = c.y - my
                    d = math.hypot(dx, dy)
                    if d < min_d:
                        min_d = d
                        closest = c
                if closest is not None:
                    selected_id = closest.id
                else:
                    selected_id = None

        if paused:
            screen.fill(BACKGROUND_TOP)
            for f in foods:
                if f.alive:
                    f.draw(screen)
            for c in creatures:
                if c.alive:
                    c.draw(screen, selected=(c.id == selected_id))
            if show_tree:
                draw_tree(screen, creatures, selected_id)
            if show_graph:
                draw_graph(screen, population_history)
            if show_map:
                draw_ecosystem_map(screen, creatures, foods, disease_intensity)
            info = font.render("PAUSED - Press SPACE to resume", True, (200, 200, 200))
            screen.blit(info, (10, 10))
            pygame.display.flip()
            clock.tick(30)
            continue

        # ---- Update season ----
        season_idx = (step_count // SEASON_LENGTH) % 4
        season_name = SEASONS[season_idx]
        food_mod = SEASON_FOOD_MOD[season_idx]
        energy_mod = SEASON_ENERGY_MOD[season_idx]

        # ---- Update disease ----
        if random.random() < DISEASE_OUTBREAK_CHANCE and disease_intensity < 0.5:
            disease_intensity = 0.3 + random.random() * 0.5
            disease_outbreak_timer = DISEASE_OUTBREAK_DURATION
        if disease_outbreak_timer > 0:
            disease_outbreak_timer -= 1
            if disease_outbreak_timer == 0:
                disease_intensity = max(0, disease_intensity - 0.1)
        else:
            disease_intensity = max(0, disease_intensity - 0.001)

        # ---- Spawn food ----
        if random.random() < FOOD_SPAWN_RATE * food_mod:
            ft = random.choice(food_keys)
            foods.append(Food(random.randint(0, WIDTH), random.randint(0, HEIGHT), ft))

        # ---- Update creatures ----
        for c in creatures[:]:
            if c.alive:
                c.update(foods, creatures, season_idx, disease_intensity)

        creatures = [c for c in creatures if c.alive]
        foods = [f for f in foods if f.alive]

        population_history.append(len(creatures))

        # ---- Draw ----
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(BACKGROUND_TOP[0] + (BACKGROUND_BOTTOM[0] - BACKGROUND_TOP[0]) * ratio)
            g = int(BACKGROUND_TOP[1] + (BACKGROUND_BOTTOM[1] - BACKGROUND_TOP[1]) * ratio)
            b = int(BACKGROUND_TOP[2] + (BACKGROUND_BOTTOM[2] - BACKGROUND_TOP[2]) * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

        for (sx, sy, size) in stars:
            pygame.draw.circle(screen, (100, 100, 120), (sx, sy), size)

        for f in foods:
            f.draw(screen)

        for c in creatures:
            c.draw(screen, selected=(c.id == selected_id))

        if show_tree:
            draw_tree(screen, creatures, selected_id)
        if show_graph:
            draw_graph(screen, population_history)
        if show_map:
            draw_ecosystem_map(screen, creatures, foods, disease_intensity)

        # ---- HUD ----
        diet_counts = {name: 0 for name in DIET_NAMES}
        sex_counts = [0, 0]
        predator_count = 0
        prey_count = 0
        mature_count = 0
        infected_count = 0
        total_resistance = 0
        for c in creatures:
            diet_counts[DIET_NAMES[c.diet_type]] += 1
            sex_counts[c.sex] += 1
            if c.is_predator:
                predator_count += 1
            else:
                prey_count += 1
            if c.is_mature:
                mature_count += 1
            if c.infected:
                infected_count += 1
            total_resistance += c.disease_resistance
        avg_resistance = total_resistance / len(creatures) if creatures else 0

        lineage_ids = set()
        for c in creatures:
            if c.parent_id is not None:
                lineage_ids.add(c.parent_id)
            else:
                lineage_ids.add(c.id)
        lineage_count = len(lineage_ids)
        avg_gen = sum(c.generation for c in creatures) / len(creatures) if creatures else 0

        season_color = SEASON_COLORS[season_idx]
        season_text = f"Season: {SEASONS[season_idx]}"

        info_lines = [
            f"Creatures: {len(creatures)}  |  Food: {len(foods)}  |  Step: {step_count}",
            f"Lineages: {lineage_count}  |  Avg Gen: {avg_gen:.1f}  |  ♀: {sex_counts[0]}  ♂: {sex_counts[1]}",
            f"Predators: {predator_count}  |  Prey: {prey_count}  |  Mature: {mature_count}",
            f"Disease: {disease_intensity:.2f}  |  Infected: {infected_count}  |  Avg Resist: {avg_resistance:.2f}",
            f"Selected ID: {selected_id if selected_id else 'none'}",
            f"Diets: " + ", ".join([f"{d}: {c}" for d, c in diet_counts.items() if c > 0]),
            "SPACE:pause  R:reset  T:tree  G:graph  M:map  Click:select"
        ]

        y_offset = 10
        for i, line in enumerate(info_lines):
            text_surf = font.render(line, True, (220, 220, 220))
            screen.blit(text_surf, (10, y_offset))
            y_offset += 22

        season_surf = font.render(season_text, True, season_color)
        screen.blit(season_surf, (WIDTH - 150, 10))

        pygame.display.flip()
        clock.tick(60)
        step_count += 1

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()