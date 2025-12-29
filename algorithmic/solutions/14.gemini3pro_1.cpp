#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <random>
#include <algorithm>

using namespace std;

// Function to perform walk query
// Moves the token x steps and returns the label of the new vertex.
string query_walk(long long x) {
    cout << "walk " << x << endl;
    string label;
    cin >> label;
    return label;
}

// Function to guess the answer
// Ends the interaction.
void guess(long long n) {
    cout << "guess " << n << endl;
    exit(0);
}

int main() {
    // We use a map to store the visited vertices and their accumulated distance from the start.
    // Key: Vertex Label (string), Value: Total distance (long long)
    map<string, long long> visited;

    // Initialize random number generator
    random_device rd;
    mt19937_64 rng(rd());
    // We use a uniform distribution for step sizes. Large range helps avoid small cycle resonance.
    uniform_int_distribution<long long> dist(1, 1000000000); 

    long long current_dist = 0;
    
    // Get the label of the starting vertex. 'walk 0' is valid and returns current label.
    // This serves as our anchor point at distance 0.
    string start_label = query_walk(0);
    visited[start_label] = 0;

    long long period = -1;
    string collision_vertex_label = start_label; // Initially we are at the start vertex

    // Phase 1: Random walk to find a collision (Birthday Attack)
    // We keep walking random steps until we land on a previously visited vertex.
    // The difference in accumulated distances will be a multiple of n.
    // By the birthday paradox, we expect a collision after approx sqrt(n) steps.
    // For n = 10^9, sqrt(n) approx 31622, which fits well within the 200,000 query limit
    // and scores reasonably well. For small n, collision is very fast (high score).
    int limit = 200000;
    
    for (int i = 0; i < limit; ++i) {
        long long step = dist(rng);
        string label = query_walk(step);
        current_dist += step;

        if (visited.count(label)) {
            // Collision found
            long long prev_dist = visited[label];
            period = current_dist - prev_dist;
            collision_vertex_label = label;
            break; // We found a multiple of n
        } else {
            visited[label] = current_dist;
        }
    }

    if (period == -1) {
        // This case is statistically impossible given the constraints and limits,
        // unless n is much larger than 10^9.
        guess(1);
    }

    // Phase 2: Reduce the found multiple (period) to find the minimal n
    // We know n divides 'period'. We want to remove extra factors.
    // n is the smallest positive integer d such that walk(d) is the identity operation.
    long long candidate = period;
    long long temp = period;
    
    // Find prime factors of the period
    vector<long long> prime_factors;
    for (long long d = 2; d * d <= temp; ++d) {
        if (temp % d == 0) {
            prime_factors.push_back(d);
            while (temp % d == 0) temp /= d;
        }
    }
    if (temp > 1) {
        prime_factors.push_back(temp);
    }

    // Try to divide out prime factors.
    // We check if candidate/p is still a multiple of n by walking it.
    // If walk(candidate/p) returns to the current vertex, then candidate/p is a multiple of n.
    // Otherwise, we must walk the remainder to return to the original spot.
    for (long long p : prime_factors) {
        while (candidate % p == 0) {
            long long test_val = candidate / p;
            string lbl = query_walk(test_val);
            if (lbl == collision_vertex_label) {
                // Success: walking test_val brought us back to the same vertex.
                // Thus, n must divide test_val.
                candidate = test_val;
            } else {
                // Failure: n does not divide test_val.
                // We are now at some vertex v != collision_vertex_label.
                // We need to return to collision_vertex_label to continue testing.
                // Since 'candidate' is a known multiple of n, walking 'candidate' would bring us back.
                // We have already walked 'test_val', so we walk 'candidate - test_val'.
                long long fix_step = candidate - test_val;
                string lbl_back = query_walk(fix_step);
                // We are now back at collision_vertex_label.
                break; // This prime factor cannot be removed further.
            }
        }
    }

    guess(candidate);

    return 0;
}