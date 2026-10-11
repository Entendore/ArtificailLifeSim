
import pygame
import random
import math
import uuid

# --- Configuration ---
WIDTH, HEIGHT = 1200, 800
FPS = 60
FOOD_COUNT = 80
INITIAL_BLOBS = 25
STARTING_ENERGY = 100
FOOD_ENERGY_VALUE = 60
REPRODUCTION_ENERGY_COST = 80 
MUTATION_RATE = 0.1

# Colors
COLOR_BG_TOP = (10, 20, 40)
COLOR_BG_BOT = (5, 5, 15)
COLOR_FOOD = (0, 255, 180)
COLOR_UI = (200, 200, 220)
COLOR_FERTILE = (0, 100, 50)

class Particle:
    """Simulates 'Marine Snow' or organic debris"""
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.size = random.uniform(1, 3)
        self.speed = random.uniform(0.2, 0.8)
        self.drift = random.uniform(-0.5, 0.5)

    def update(self):
        self.y += self.speed
        self.x += self.drift
        if self.y > HEIGHT: self.y = 0
        if self.x > WIDTH: self.x = 0
        if self.x < 0: self.x = WIDTH

    def draw(self, screen):
        pygame.draw.circle(screen, (100, 100, 150), (int(self.x), int(self.y)), int(self.size))

class DeathEffect:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.color = color
        self.particles = [ [random.uniform(-2, 2), random.uniform(-2, 2)] for _ in range(10)]
        self.life = 255

    def update(self):
        self.life -= 5
        for p in self.particles:
            p[0] += p[0] * 0.1
            p[1] += p[1] * 0.1

    def draw(self, screen):
        if self.life > 0:
            for p in self.particles:
                px, py = self.x + p[0]*10, self.y + p[1]*10
                pygame.draw.circle(screen, (*self.color, self.life), (int(px), int(py)), 1)

class Biome:
    def __init__(self, type="fertile"):
        self.type = type
        self.x = random.randint(100, WIDTH-100)
        self.y = random.randint(100, HEIGHT-100)
        self.radius = random.randint(100, 250)

    def draw(self, screen):
        # Draw a soft, glowing aura
        color = COLOR_FERTILE if self.type == "fertile" else (40, 0, 60)
        for i in range(3):
            pygame.draw.circle(screen, (color[0]//4, color[1]//4, color[2]//4), (self.x, self.y), self.radius + (i*20), 0)
        pygame.draw.circle(screen, (color[0]//2, color[1]//2, color[2]//2), (self.x, self.y), self.radius, 0)

class Food:
    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(20, WIDTH-20)
        self.y = y if y else random.randint(20, HEIGHT-20)

    def draw(self, screen):
        pygame.draw.circle(screen, COLOR_FOOD, (int(self.x), int(self.y)), 3)

class Blob:
    def __init__(self, x, y, genes=None, family_id=None, energy=STARTING_ENERGY):
        self.x, self.y = x, y
        self.energy = energy
        self.age = 0
        self.gender = random.choice(["M", "F"])
        self.state = "forage"
        self.trail = []
        self.family_id = family_id if family_id else str(uuid.uuid4())[:8]
        self.family_color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        if genes: self.genes = self.crossover(genes)
        else: self.genes = {
            "speed": random.uniform(1, 4), "sense": random.uniform(50, 250), "size": random.uniform(8, 18),
            "aggression": random.uniform(0, 1), "metabolism": random.uniform(0.5, 1.5), "lifespan": random.uniform(1500, 4000),
            "camouflage": random.uniform(0, 1), "cunning": random.uniform(0, 1), "sociality": random.uniform(0, 1)
        }
        self.angle = random.uniform(0, math.pi * 2)
        self.color = self.calculate_final_color()
        self.shape_offsets = [random.uniform(0.7, 1.3) for _ in range(8)]

    def crossover(self, parents_genes):
        p1, p2 = parents_genes
        child_genes = {}
        for key in p1:
            child_genes[key] = random.choice([p1[key], p2[key]])
            if random.random() < MUTATION_RATE:
                child_genes[key] *= random.uniform(0.8, 1.2)
                if key == "aggression": child_genes[key] = max(0, min(1, child_genes[key]))
        return child_genes

    def calculate_final_color(self):
        r = int((self.family_color[0] + (self.genes["aggression"] * 255)) // 2)
        g = int((self.family_color[1] + (self.genes["sense"] * 0.5)) // 2)
        b = int((self.family_color[2] + (self.genes["size"] * 10)) // 2)
        camo = self.genes["camouflage"] * 0.6
        grey = 128
        r = int(r * (1-camo) + grey * camo)
        g = int(g * (1-camo) + grey * camo)
        b = int(b * (1-camo) + grey * camo)
        return (max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))

    def update(self, foods, blobs, biomes):
        self.age += 1
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10: self.trail.pop(0)
        
        # Energy cost influence from Biomes
        biome_mult = 1.0
        for b in biomes:
            if math.hypot(self.x - b.x, self.y - b.y) < b.radius:
                biome_mult = 0.7 if b.type == "fertile" else 1.5

        target = None
        closest_dist = self.genes["sense"]
        if self.energy < 70: self.state = "forage"
        elif self.energy > 150: self.state = "court"
        elif self.genes["aggression"] > 0.7: self.state = "hunt"
        else: self.state = "forage"

        if self.state == "forage":
            for f in foods:
                d = math.hypot(self.x - f.x, self.y - f.y)
                if d < closest_dist: closest_dist = d; target = f
        elif self.state == "court":
            for b in blobs:
                if b != self and b.gender != self.gender and b.energy > 100:
                    d = math.hypot(self.x - b.x, self.y - b.y)
                    if d < closest_dist: closest_dist = d; target = b
        elif self.state == "hunt":
            for b in blobs:
                if b != self and b.genes["size"] < self.genes["size"]:
                    d = math.hypot(self.x - b.x, self.y - b.y)
                    if d < closest_dist: closest_dist = d; target = b

        if target:
            t_angle = math.atan2(target.y - self.y, target.x - self.x)
            self.angle += (t_angle - self.angle) * 0.1
        else:
            self.angle += random.uniform(-0.2, 0.2)

        self.x += math.cos(self.angle) * self.genes["speed"]
        self.y += math.sin(self.angle) * self.genes["speed"]
        if self.x < 0 or self.x > WIDTH: self.angle = math.pi - self.angle
        if self.y < 0 or self.y > HEIGHT: self.angle = -self.angle

        cost = ((self.genes["speed"]**2 * 0.05) + (self.genes["sense"] * 0.002) + (self.genes["size"] * 0.02)) * self.genes["metabolism"]
        self.energy -= cost * biome_mult

    def eat(self, foods, blobs):
        for f in foods[:]:
            if math.hypot(self.x - f.x, self.y - f.y) < self.genes["size"] + 3:
                self.energy += FOOD_ENERGY_VALUE
                foods.remove(f)
        if self.genes["aggression"] > 0.6:
            for b in blobs[:]:
                if b != self and b.genes["size"] < self.genes["size"] * 0.8:
                    if math.hypot(self.x - b.x, self.y - b.y) < self.genes["size"]:
                        self.energy += b.energy * 0.5
                        blobs.remove(b)

    def attempt_mate(self, blobs):
        if self.energy > REPRODUCTION_ENERGY_COST:
            for b in blobs:
                if b != self and b.gender != self.gender and b.energy > REPRODUCTION_ENERGY_COST:
                    if math.hypot(self.x - b.x, self.y - b.y) < self.genes["size"] + b.genes["size"]:
                        self.energy -= REPRODUCTION_ENERGY_COST
                        b.energy -= REPRODUCTION_ENERGY_COST
                        return Blob(self.x, self.y, genes=[self.genes, b.genes], family_id=self.family_id, energy=STARTING_ENERGY)
        return None

    def draw(self, screen):
        # Draw body with the same geometry as before
        time_offset = pygame.time.get_ticks() * 0.005
        points = []
        for i in range(8):
            theta = (i / 8) * 2 * math.pi
            spike = 1.0 + (self.genes["aggression"] * 0.5 * math.sin(time_offset + i))
            r = self.genes["size"] * self.shape_offsets[i] * spike
            points.append((self.x + math.cos(theta + self.angle) * r, self.y + math.sin(theta + self.angle) * r))
        pygame.draw.polygon(screen, self.color, points)
        
        # Tendrils
        num_tendrils = 2 if self.genes["sense"] < 150 else 4
        for i in range(num_tendrils):
            t_angle = self.angle + (i * math.pi / 2)
            wiggle = math.sin(time_offset + i) * 5
            pygame.draw.line(screen, self.color, (self.x, self.y), (self.x + math.cos(t_angle)*self.genes["size"]*1.5 + wiggle, self.y + math.sin(t_angle)*self.genes["size"]*1.5 + wiggle), 2)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Bio-Ecosystem: Deep Sea")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 16)

    blobs = [Blob(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(INITIAL_BLOBS)]
    foods = [Food() for _ in range(FOOD_COUNT)]
    particles = [Particle() for _ in range(150)]
    biomes = [Biome("fertile") for _ in range(2)] + [Biome("dead") for _ in range(1)]
    deaths = []

    running = True
    while running:
        # --- Background Gradient ---
        screen.fill(COLOR_BG_BOT)
        pygame.draw.rect(screen, COLOR_BG_TOP, (0, 0, WIDTH, HEIGHT // 2)) # Simple simulated gradient

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        # Environmental updates
        for p in particles: 
            p.update()
            p.draw(screen)
            
        for b in biomes: b.draw(screen)

        if len(foods) < FOOD_COUNT:
            # Biome-based food spawning
            if random.random() < 0.3:
                target_biome = random.choice(biomes)
                if target_biome.type == "fertile":
                    foods.append(Food(target_biome.x + random.randint(-50, 50), target_biome.y + random.randint(-50, 50)))
                else:
                    foods.append(Food())
            else:
                foods.append(Food())

        new_blobs = []
        for b in blobs[:]:
            b.update(foods, blobs, biomes)
            b.eat(foods, blobs)
            child = b.attempt_mate(blobs)
            if child: new_blobs.append(child)
            if b.energy <= 0 or b.age > b.genes["lifespan"]:
                deaths.append(DeathEffect(b.x, b.y, b.color))
                blobs.remove(b)
            else:
                b.draw(screen)

        # Social Tethers (Visualizing family bonds)
        for b in blobs:
            if b.genes["sociality"] > 0.6:
                for other in blobs:
                    if b != other and b.family_id == other.family_id:
                        dist = math.hypot(b.x - other.x, b.y - other.y)
                        if dist < 100:
                            pygame.draw.line(screen, (*b.color, 50), (b.x, b.y), (other.x, other.y), 1)

        blobs.extend(new_blobs)
        for f in foods: f.draw(screen)
        for d in deaths[:]:
            d.update()
            d.draw(screen)
            if d.life <= 0: deaths.remove(d)

        # UI
        if blobs:
            lineage_counts = {}
            for b in blobs: lineage_counts[b.family_id] = lineage_counts.get(b.family_id, 0) + 1
            dominant_id = max(lineage_counts, key=lineage_counts.get)
            stats = [f"Pop: {len(blobs)}", f"Dominant Clan: {dominant_id}", f"Biomes: Fertile/Dead"]
            for i, txt in enumerate(stats):
                screen.blit(font.render(txt, True, COLOR_UI), (10, 10 + i*20))

        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main()
