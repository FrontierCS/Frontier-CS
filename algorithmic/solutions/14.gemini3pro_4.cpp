#include <iostream>
#include <vector>
#include <map>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Function to interact with the judge
// Moves the token x steps and returns the new label
long long walk(long long x) {
    cout << "walk " << x << endl;
    long long label;
    cin >> label;
    return label;
}

// Function to make a guess
void guess(long long g) {
    cout << "guess " << g << endl;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Initialize random number generator with a time-based seed
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Map to store visited vertices: label -> total_distance_from_start
    map<long long, long long> visited;
    
    // Get the label of the starting vertex. walk(0) moves 0 steps but returns the label.
    long long current_label = walk(0);
    visited[current_label] = 0;
    
    long long current_dist = 0;
    long long cycle_multiple = -1;
    
    // We limit the number of random walks to ensure we have queries left for the reduction phase.
    // The total limit is 200,000.
    int limit = 199000;
    
    // Birthday Paradox Phase: Random walk to find a cycle multiple
    // With N up to 10^9, expected queries for collision is ~40,000.
    for (int i = 0; i < limit; ++i) {
        // Choose a random step size. 
        // Using a large range helps sampling the cycle uniformly.
        long long step = (rng() % 1000000000) + 1;
        
        long long label = walk(step);
        current_dist += step;
        current_label = label; // Update current label
        
        if (visited.count(label)) {
            // Collision detected!
            // The difference in distances is a multiple of the cycle length n.
            cycle_multiple = current_dist - visited[label];
            break;
        }
        visited[label] = current_dist;
    }
    
    if (cycle_multiple == -1) {
        // If no collision is found (highly unlikely for N <= 10^9 given the query limit),
        // we guess the number of unique vertices seen as a fallback.
        guess(visited.size()); 
        return 0;
    }
    
    // Reduction Phase: Determine the exact cycle length n from the multiple.
    // We find the smallest divisor d of cycle_multiple such that walking d returns to the same vertex.
    long long n = cycle_multiple;
    long long temp = n;
    vector<long long> factors;
    
    // Factorize the cycle multiple
    for (long long d = 2; d * d <= temp; ++d) {
        while (temp % d == 0) {
            factors.push_back(d);
            temp /= d;
        }
    }
    if (temp > 1) factors.push_back(temp);
    
    sort(factors.begin(), factors.end());
    
    // Try to remove each prime factor from n
    for (size_t i = 0; i < factors.size(); ) {
        long long p = factors[i];
        
        // If p is still a factor of current candidate n
        if (n % p == 0) {
            long long candidate = n / p;
            
            // Check if candidate is also a multiple of the cycle length
            // We do this by walking 'candidate' steps.
            // If the cycle length divides 'candidate', we should return to the same vertex label.
            long long next_label = walk(candidate);
            
            if (next_label == current_label) {
                // Success: n/p is a valid period. We update n.
                n = candidate;
                // Since next_label == current_label, our relative position on the cycle 
                // (modulo true n) is unchanged, so we can continue checking from here.
                // We consume one instance of factor p.
                i++; 
            } else {
                // Failure: n/p is NOT a multiple of the cycle length.
                // This means the factor p is necessary.
                // We moved to a new position, so we update current_label.
                current_label = next_label;
                
                // Since p is necessary, we cannot remove any instances of p from n.
                // Skip all remaining occurrences of p in the factors list.
                while (i < factors.size() && factors[i] == p) {
                    i++;
                }
            }
        } else {
            // p is no longer a factor of n (shouldn't happen with sorted logic but for safety)
            i++;
        }
    }
    
    guess(n);
    
    return 0;
}