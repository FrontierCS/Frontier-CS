#ifndef NBODY_WORLD_H
#define NBODY_WORLD_H

#include <cmath>
#include <memory>
#include <vector>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <cstdlib>

struct Vec2 {
  float x, y;
  Vec2(float vx = 0.0f, float vy = 0.0f) : x(vx), y(vy) {}
  static float dot(Vec2 v0, Vec2 v1) { return v0.x * v1.x + v0.y * v1.y; }
  float &operator[](int i) { return ((float *)this)[i]; }
  Vec2 operator*(float s) const { return Vec2(*this) *= s; }
  Vec2 operator*(Vec2 vin) const { return Vec2(*this) *= vin; }
  Vec2 operator+(Vec2 vin) const { return Vec2(*this) += vin; }
  Vec2 operator-(Vec2 vin) const { return Vec2(*this) -= vin; }
  Vec2 operator-() const { return Vec2(-x, -y); }
  Vec2 &operator+=(Vec2 vin) {
    x += vin.x;
    y += vin.y;
    return *this;
  }
  Vec2 &operator-=(Vec2 vin) {
    x -= vin.x;
    y -= vin.y;
    return *this;
  }
  Vec2 &operator=(float v) {
    x = y = v;
    return *this;
  }
  Vec2 &operator*=(float s) {
    x *= s;
    y *= s;
    return *this;
  }
  Vec2 &operator*=(Vec2 vin) {
    x *= vin.x;
    y *= vin.y;
    return *this;
  }
  float length2() const { return x * x + y * y; }
  float length() const { return std::sqrt(length2()); }
};

struct Particle {
  int id;
  float mass;
  Vec2 position;
  Vec2 velocity;
};

// Do not modify this function.
inline Vec2 computeForce(const Particle &target, const Particle &attractor,
                         float cullRadius) {
  auto dir = (attractor.position - target.position);
  auto dist = dir.length();
  if (dist < 1e-3f)
    return Vec2(0.0f, 0.0f);
  dir *= (1.0f / dist);
  if (dist > cullRadius)
    return Vec2(0.0f, 0.0f);
  if (dist < 1e-1f)
    dist = 1e-1f;
  const float G = 0.01f;
  Vec2 force = dir * target.mass * attractor.mass * (G / (dist * dist));
  if (dist > cullRadius * 0.75f) {
    float decay = 1.0f - (dist - cullRadius * 0.75f) / (cullRadius * 0.25f);
    force *= decay;
  }
  return force;
}

inline Particle updateParticle(const Particle &pi, Vec2 force,
                               float deltaTime) {
  Particle result = pi;
  result.velocity += force * (deltaTime / pi.mass);
  result.position += result.velocity * deltaTime;
  return result;
}

struct StepParameters {
  float deltaTime = 0.2f;
  float cullRadius = 1.0f;
};

// Random number generator for reproducible particle generation
class Random {
private:
  unsigned int seed;

public:
  Random(int seed) : seed(seed) {}
  int Next() {
    return (((seed = seed * 214013L + 2531011L) >> 16) & 0x7fff);
  }
  int Next(int min, int max) {
    unsigned int a = ((seed = seed * 214013L + 2531011L) & 0xFFFF0000);
    unsigned int b = ((seed = seed * 214013L + 2531011L) >> 16);
    unsigned int r = a + b;
    return min + r % (max - min);
  }
  float NextFloat() { return ((Next() << 15) + Next()) / ((float)(1 << 30)); }
  float NextFloat(float valMin, float valMax) {
    return valMin + (valMax - valMin) * NextFloat();
  }
  static int RandMax() { return 0x7fff; }
};

// World class to hold particles
class World {
public:
  std::vector<Particle> particles;
  std::vector<Particle> newParticles;

  void generateRandom(int numParticles, float spaceSize) {
    float maxVelocity = spaceSize * 0.5f;
    Random random(3366);
    particles.resize(numParticles);
    newParticles.clear();
    newParticles.resize(numParticles);

    for (int i = 0; i < numParticles; i++) {
      particles[i].mass = random.NextFloat(1.0f, 10.0f);
      particles[i].velocity.x = random.NextFloat(-maxVelocity, maxVelocity);
      particles[i].velocity.y = random.NextFloat(-maxVelocity, maxVelocity);
      particles[i].position.x = random.NextFloat(-spaceSize, spaceSize);
      particles[i].position.y = random.NextFloat(-spaceSize, spaceSize);
      particles[i].id = i;
    }
  }
};

// Simulator interface - LLM solutions should implement this class
// State can persist across simulateStep() calls
class Simulator {
public:
  virtual ~Simulator() = default;
  
  // Called once before simulation starts
  // Use this to set thread count, pre-allocate structures, etc.
  virtual void init(int numParticles, StepParameters params) {}
  
  // Called each simulation step
  // Must compute new particle positions/velocities and store in newParticles
  virtual void simulateStep(std::vector<Particle> &particles,
                            std::vector<Particle> &newParticles,
                            StepParameters params) = 0;
};

// Factory function - solutions must implement this
Simulator* createSimulator();

#endif
