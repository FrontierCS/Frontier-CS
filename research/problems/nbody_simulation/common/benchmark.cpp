// Benchmark harness for N-body simulation
// This file includes the submitted solution and baseline, then runs benchmarks

#include "world.h"
#include "timing.h"
#include <iostream>
#include <fstream>
#include <iomanip>
#include <cstring>
#include <cmath>
#include <algorithm>
#include <omp.h>

// Forward declaration for baseline factory
Simulator* createBaselineSimulator();

struct BenchmarkOptions {
  int numParticles = 10000;
  int numIterations = 5;
  float spaceSize = 100.0f;
  int numRuns = 1;  // Temporarily set to 1 for optimization testing
  bool checkCorrectness = true;
  std::string outputFile = "result.txt";
};

BenchmarkOptions parseOptions(int argc, char** argv) {
  BenchmarkOptions opts;
  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], "-n") == 0 && i + 1 < argc) {
      opts.numParticles = atoi(argv[++i]);
    } else if (strcmp(argv[i], "-i") == 0 && i + 1 < argc) {
      opts.numIterations = atoi(argv[++i]);
    } else if (strcmp(argv[i], "-s") == 0 && i + 1 < argc) {
      opts.spaceSize = (float)atof(argv[++i]);
    } else if (strcmp(argv[i], "-r") == 0 && i + 1 < argc) {
      opts.numRuns = atoi(argv[++i]);
    } else if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) {
      opts.outputFile = argv[++i];
    } else if (strcmp(argv[i], "--no-check") == 0) {
      opts.checkCorrectness = false;
    }
  }
  return opts;
}

bool checkForCorrectness(const World& refW, const World& w, float tolerance = 1e-2f) {
  if (w.particles.size() != refW.particles.size()) {
    std::cerr << "Mismatch: number of particles " << w.particles.size()
              << " does not match reference " << refW.particles.size() << std::endl;
    return false;
  }

  for (size_t i = 0; i < w.particles.size(); i++) {
    auto errorX = std::abs(w.particles[i].position.x - refW.particles[i].position.x);
    auto errorY = std::abs(w.particles[i].position.y - refW.particles[i].position.y);
    if (errorX > tolerance || errorY > tolerance) {
      std::cerr << "Mismatch at index " << i
                << ": result (" << w.particles[i].position.x << ", "
                << w.particles[i].position.y << ")"
                << " should be (" << refW.particles[i].position.x << ", "
                << refW.particles[i].position.y << ")" << std::endl;
      return false;
    }
  }
  return true;
}

double runSimulation(World& world, Simulator* sim, 
                     StepParameters params, int numIterations) {
  Timer timer;
  timer.reset();
  
  // Initialize simulator at the start of each run (clean state)
  sim->init(world.particles.size(), params);
  
  for (int iter = 0; iter < numIterations; iter++) {
    world.newParticles.resize(world.particles.size());
    sim->simulateStep(world.particles, world.newParticles, params);
    world.particles.swap(world.newParticles);
  }
  
  return timer.elapsed();
}

int main(int argc, char** argv) {
  BenchmarkOptions opts = parseOptions(argc, argv);
  
  // Note: Solutions can set their own thread count via omp_set_num_threads()
  std::cout << "Max OpenMP threads available: " << omp_get_max_threads() << std::endl;
  
  StepParameters params;
  params.cullRadius = opts.spaceSize / 4.0f;
  params.deltaTime = 0.2f;
  
  std::cout << "N-Body Simulation Benchmark" << std::endl;
  std::cout << "Particles: " << opts.numParticles << std::endl;
  std::cout << "Iterations: " << opts.numIterations << std::endl;
  std::cout << "Space size: " << opts.spaceSize << std::endl;
  std::cout << "Cull radius: " << params.cullRadius << std::endl;
  std::cout << std::endl;
  
  // Create simulators
  Simulator* baselineSim = createBaselineSimulator();
  Simulator* solutionSim = createSimulator();
  
  // Benchmark sequential baseline
  std::vector<double> seqTimes;
  for (int run = 0; run < opts.numRuns; run++) {
    World seqWorld;
    seqWorld.generateRandom(opts.numParticles, opts.spaceSize);
    double elapsed = runSimulation(seqWorld, baselineSim, params, opts.numIterations);
    seqTimes.push_back(elapsed);
    std::cout << "Sequential run " << (run + 1) << ": " << std::fixed 
              << std::setprecision(4) << elapsed << "s" << std::endl;
  }
  
  // Sort and get median
  std::sort(seqTimes.begin(), seqTimes.end());
  double seqMedian = seqTimes[opts.numRuns / 2];
  std::cout << "Sequential median: " << std::fixed << std::setprecision(4) 
            << seqMedian << "s" << std::endl << std::endl;
  
  // Benchmark submitted solution
  std::vector<double> parTimes;
  World finalWorld;
  for (int run = 0; run < opts.numRuns; run++) {
    World parWorld;
    parWorld.generateRandom(opts.numParticles, opts.spaceSize);
    double elapsed = runSimulation(parWorld, solutionSim, params, opts.numIterations);
    parTimes.push_back(elapsed);
    std::cout << "Solution run " << (run + 1) << ": " << std::fixed 
              << std::setprecision(4) << elapsed << "s" << std::endl;
    if (run == opts.numRuns - 1) {
      finalWorld = parWorld;
    }
  }
  
  std::sort(parTimes.begin(), parTimes.end());
  double parMedian = parTimes[opts.numRuns / 2];
  std::cout << "Solution median: " << std::fixed << std::setprecision(4) 
            << parMedian << "s" << std::endl << std::endl;
  
  // Check correctness
  bool correct = true;
  if (opts.checkCorrectness) {
    std::cout << "Checking correctness..." << std::endl;
    World refWorld;
    refWorld.generateRandom(opts.numParticles, opts.spaceSize);
    runSimulation(refWorld, baselineSim, params, opts.numIterations);
    
    World testWorld;
    testWorld.generateRandom(opts.numParticles, opts.spaceSize);
    runSimulation(testWorld, solutionSim, params, opts.numIterations);
    
    correct = checkForCorrectness(refWorld, testWorld);
    if (correct) {
      std::cout << "Correctness check: PASSED" << std::endl;
    } else {
      std::cout << "Correctness check: FAILED" << std::endl;
    }
  }
  
  // Calculate speedup
  double speedup = seqMedian / parMedian;
  std::cout << std::endl;
  std::cout << "Speedup: " << std::fixed << std::setprecision(3) << speedup << "x" << std::endl;
  
  // Write results
  std::ofstream outFile(opts.outputFile);
  if (outFile) {
    outFile << "sequential_time=" << std::fixed << std::setprecision(6) << seqMedian << std::endl;
    outFile << "parallel_time=" << std::fixed << std::setprecision(6) << parMedian << std::endl;
    outFile << "speedup=" << std::fixed << std::setprecision(6) << speedup << std::endl;
    outFile << "correct=" << (correct ? "true" : "false") << std::endl;
    outFile.close();
  }
  
  // Cleanup
  delete baselineSim;
  delete solutionSim;
  
  return correct ? 0 : 1;
}
