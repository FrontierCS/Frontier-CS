#include <iostream>
#include <vector>
#include <map>
#include <random>
#include <algorithm>
#include <chrono>
#include <cstdlib>

using namespace std;

// Helper function to issue a walk query
long long query_walk(long long x) {
    cout << "walk " << x << endl;
    long long label;
    cin >> label;
    return label;
}

// Helper function to issue a guess and exit
void query_guess(long long n) {
    cout << "guess " << n << endl;
    exit(0);
}

// Helper function to get prime factorization of a number
vector<long long> get_prime_factors(long long m) {
    vector<long long> factors;
    if (m % 2 == 0) {
        factors.push_back(2);
        while (m % 2 == 0) m /= 2;
    }
    for (long long i = 3; i * i <= m; i += 2) {
        if (m % i == 0) {
            factors.push_back(i);
            while (m % i == 0) m /= i;
        }
    }
    if (m > 1) {
        factors.push_back(m);
    }
    return factors;
}

int main() {
    // Interact with the judge.
    // We rely on the Birthday Paradox to find a collision in the cycle.
    // By storing visited (label -> distance) in a map and taking random steps,
    // we expect to find a collision in O(sqrt(n)) steps.
    
    // Start by getting the label of the initial vertex (walk 0 steps)
    long long current_label = query_walk(0);
    
    map<long long, long long> visited;
    visited[current_label] = 0;

    long long current_dist = 0;
    long long M = -1;

    // Use a random number generator with time-based seed
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    // Uniform distribution for step sizes in a large range to ensure good mixing
    uniform_int_distribution<long long> dist_gen(1, 1000000000); 

    // Limit queries to leave room for the reduction phase
    // Max allowable is 200,000.
    int max_walks = 199000; 

    for (int i = 0; i < max_walks; ++i) {
        long long step = dist_gen(rng);
        long long new_label = query_walk(step);
        current_dist += step;
        
        if (visited.count(new_label)) {
            // Collision detected
            // The distance between the two occurrences is a multiple of n
            M = current_dist - visited[new_label];
            current_label = new_label;
            break;
        } else {
            visited[new_label] = current_dist;
            current_label = new_label;
        }
    }

    if (M == -1) {
        // If no collision found (very unlikely given constraints and query limit), guess 1
        query_guess(1);
    }

    // Phase 2: Reduce the multiple M to the smallest period n
    // We check each prime factor of M to see if we can reduce M by that factor
    vector<long long> factors = get_prime_factors(M);
    
    for (long long p : factors) {
        while (M % p == 0) {
            long long candidate = M / p;
            // Check if walking 'candidate' steps lands us on a vertex with the same label
            long long next_label = query_walk(candidate);
            
            if (next_label == current_label) {
                // If the label is the same, then 'candidate' is a valid period (multiple of n)
                M = candidate;
                // Physically we moved, but since it's a period, logically we are at an equivalent position
                // current_label remains valid for the next check
            } else {
                // If label changed, 'candidate' is not a period.
                // We physically moved to a new position, so we must update current_label
                current_label = next_label;
                // We cannot divide M by p anymore
                break; 
            }
        }
    }

    query_guess(M);

    return 0;
}