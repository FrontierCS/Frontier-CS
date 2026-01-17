#include <iostream>
#include <vector>
#include <cmath>
#include <map>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Interactive query function
// Given a vertex v and a positive integer x, returns the vertex reached after x steps.
long long query(int v, long long x) {
    cout << "? " << v << " " << x << endl;
    long long res;
    cin >> res;
    return res;
}

// Global history map to store results of queries from vertex 1
// Maps result vertex index -> list of steps x that reached it
map<long long, vector<long long>> history_map;

// Function to make a query and check for collisions
// Returns M > 0 if collision found (M is a multiple of L), 0 otherwise
long long make_query(long long x) {
    long long v = query(1, x);
    if (history_map.count(v)) {
        // Collision found
        // Return difference between current x and the previous x that reached v
        // This difference must be a multiple of the cycle length L
        return abs(history_map[v][0] - x);
    }
    history_map[v].push_back(x);
    return 0;
}

// Function to check if T is a valid period (i.e., multiple of cycle length)
bool check_period(long long T) {
    // We check if advancing T steps from a point lands on the same vertex.
    // We use start point as vertex 1, advanced by 1 step (to be on cycle/entering cycle).
    // Compare next(1, 1) with next(1, 1 + T).
    long long v1 = query(1, 1);
    long long v2 = query(1, 1 + T);
    return v1 == v2;
}

void process_graph() {
    history_map.clear();
    long long M = 0;

    // Multi-phase Baby-Step Giant-Step approach
    // Designed to minimize queries for smaller L, while guaranteeing solution for L <= 10^6
    // The phases progressively increase the step size B, effectively searching larger ranges.
    // Note: Baby steps from previous phases are reused implicitly as "smaller baby steps",
    // but we explicitly add new baby steps to cover the new B range.
    // Giant steps from previous phases remain in the map and can collide with new steps.

    // Phase 1: Small L
    // B = 23, target L up to ~550
    // Queries used: ~23 (babies) + ~23 (giants) = ~46
    long long B1 = 23;
    for (long long b = 1; b <= B1; ++b) {
        if ((M = make_query(b)) != 0) break;
    }
    if (M == 0) {
        for (long long g = B1; g <= 550; g += B1) {
            if ((M = make_query(g)) != 0) break;
        }
    }

    // Phase 2: Medium L
    // B = 200, target L up to ~40000
    // Additional queries: ~177 (babies) + ~200 (giants) = ~377
    if (M == 0) {
        long long B2 = 200;
        // Add baby steps
        for (long long b = B1 + 1; b <= B2; ++b) {
            if ((M = make_query(b)) != 0) break;
        }
        if (M == 0) {
            // Add giant steps
            for (long long g = B2; g <= 40500; g += B2) {
                if ((M = make_query(g)) != 0) break;
            }
        }
    }

    // Phase 3: Large L
    // B = 1000, target L up to 10^6
    // Additional queries: ~800 (babies) + ~1000 (giants) = ~1800
    if (M == 0) {
        long long B3 = 1000;
        for (long long b = 201; b <= B3; ++b) { // Start after B2
            if ((M = make_query(b)) != 0) break;
        }
        if (M == 0) {
            // Target slightly above 10^6 to be safe
            for (long long g = 1000; g <= 1005000; g += 1000) {
                if ((M = make_query(g)) != 0) break;
            }
        }
    }

    // M is a multiple of L. Find L by removing prime factors of M that are not needed.
    long long L = M;
    if (M > 0) {
        long long tempM = M;
        vector<long long> factors;
        for (long long i = 2; i * i <= tempM; ++i) {
            while (tempM % i == 0) {
                factors.push_back(i);
                tempM /= i;
            }
        }
        if (tempM > 1) factors.push_back(tempM);
        
        // Try to reduce L by dividing out prime factors
        for (long long p : factors) {
            while (L % p == 0) {
                long long candidate = L / p;
                if (check_period(candidate)) {
                    L = candidate;
                } else {
                    break;
                }
            }
        }
    }

    cout << "! " << L << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
}

int main() {
    int n;
    if (cin >> n) {
        for (int i = 0; i < n; ++i) {
            process_graph();
        }
    }
    return 0;
}