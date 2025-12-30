#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

// Interaction functions
long long walk(long long x) {
    std::cout << "walk " << x << std::endl;
    long long v;
    std::cin >> v;
    if (v == -1) exit(0);
    return v;
}

void guess(long long g) {
    std::cout << "guess " << g << std::endl;
    exit(0);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    long long s = walk(0);

    std::map<long long, long long> visited;
    visited[s] = 0;
    long long total_walk = 0;
    long long current_v = s;

    // Phase 1: Linear walk for small n
    const int LINEAR_STEPS = 1000;
    for (int i = 1; i <= LINEAR_STEPS; ++i) {
        current_v = walk(1);
        total_walk++;
        if (visited.count(current_v)) {
            guess(total_walk - visited.at(current_v));
        }
        visited[current_v] = total_walk;
    }

    // Phase 2: Randomized walk to find a collision
    const int RANDOM_STEPS = 45000;
    unsigned seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<long long> distrib(1, 1000000);
    
    long long D = -1;
    for (int i = 0; i < RANDOM_STEPS; ++i) {
        long long x = distrib(rng);
        current_v = walk(x);
        total_walk += x;
        if (visited.count(current_v)) {
            D = total_walk - visited.at(current_v);
            break;
        }
        visited[current_v] = total_walk;
    }
    
    if (D == -1) {
        // This case is extremely unlikely given n <= 10^9 and the number of queries made.
        // The number of visited vertices is ~46000, so a collision is expected if n < 46000^2.
        // If no collision is found, something is wrong, but we must provide a guess.
        guess(1); 
    }

    // Phase 3: Factorize D and check divisors
    std::vector<long long> divisors;
    for (long long i = 1; i * i <= D; ++i) {
        if (D % i == 0) {
            divisors.push_back(i);
            if (i * i != D) {
                divisors.push_back(D / i);
            }
        }
    }
    std::sort(divisors.begin(), divisors.end());

    current_v = walk(0);

    for (long long g : divisors) {
        if (g <= LINEAR_STEPS) continue;
        long long next_v = walk(g);
        if (next_v == current_v) {
            guess(g);
        }
        current_v = next_v;
    }

    return 0;
}