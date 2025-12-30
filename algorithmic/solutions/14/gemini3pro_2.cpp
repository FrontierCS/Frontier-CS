#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>

using namespace std;

int main() {
    // Optimize I/O operations for performance
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Initialize random number generator
    // Using 64-bit Mersenne Twister for high-quality random numbers
    random_device rd;
    mt19937_64 rng(rd());
    // Distribution for step sizes. We select large random steps (up to 10^9)
    // to ensure we sample the cycle uniformly, maximizing collision probability.
    uniform_int_distribution<long long> dist_gen(1, 1000000000);

    // Map to store visited vertices: label -> total distance from start
    map<long long, long long> visited;
    long long current_dist = 0;
    
    // Perform an initial "walk 0" to get the label of the starting vertex.
    // This allows us to establish a baseline at distance 0.
    cout << "walk 0" << endl;
    long long current_label;
    if (!(cin >> current_label)) return 0;
    visited[current_label] = 0;

    long long cycle_multiple = 0;
    int max_queries = 200000;
    int queries_spent = 1;

    // Phase 1: Birthday Paradox Attack
    // Walk random steps until we revisit a vertex (collision).
    // The expected number of queries for a collision is O(sqrt(n)).
    // For n=10^9, this is approx 32,000 queries, well within the 200,000 limit.
    while (queries_spent < max_queries) {
        long long step = dist_gen(rng);
        cout << "walk " << step << endl;
        queries_spent++;
        
        long long label;
        cin >> label;
        current_dist += step;

        if (visited.count(label)) {
            // Collision detected!
            // The difference in distances is a multiple of the cycle length n.
            long long prev_dist = visited[label];
            cycle_multiple = current_dist - prev_dist;
            current_label = label; // We are currently at this vertex
            break;
        } else {
            visited[label] = current_dist;
            current_label = label;
        }
    }

    if (cycle_multiple == 0) {
        // Fallback in the extremely unlikely case no collision is found
        cout << "guess " << visited.size() << endl;
        return 0;
    }

    // Phase 2: Determine n from the multiple M
    // We know n is a divisor of M = cycle_multiple.
    // Also, n must be at least the number of distinct vertices observed.
    long long M = cycle_multiple;
    vector<long long> divisors;
    for (long long i = 1; i * i <= M; ++i) {
        if (M % i == 0) {
            divisors.push_back(i);
            if (i * i != M) {
                divisors.push_back(M / i);
            }
        }
    }
    sort(divisors.begin(), divisors.end());

    long long min_n = visited.size();

    // Iterate through divisors in increasing order.
    // The smallest divisor d >= min_n such that walking d steps returns to the 
    // starting position (identity operation) is the cycle length n.
    for (long long d : divisors) {
        if (d < min_n) continue;
        if (d > 1000000000) break; // n is guaranteed to be <= 10^9
        
        if (queries_spent >= max_queries) break;

        // Check if 'd' is the cycle length by walking 'd' steps from current position
        cout << "walk " << d << endl;
        queries_spent++;
        
        long long next_label;
        cin >> next_label;
        
        // If we return to the same vertex label, then d is a multiple of n.
        // Since we check smallest valid divisors first, this d must be n.
        if (next_label == current_label) {
            cout << "guess " << d << endl;
            return 0;
        }
        
        // Update current_label for the next check, as we have moved 'd' steps
        current_label = next_label;
    }
    
    // Fallback guess (should be covered by the loop logic)
    cout << "guess " << M << endl;

    return 0;
}