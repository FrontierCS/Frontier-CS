#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <random>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Map to store visited labels and their absolute distances
    map<int, long long> seen;
    long long current_dist = 0;
    int max_label = 0;
    int current_label = -1; // Initially unknown

    // Random number generator for walk steps
    mt19937_64 rng(1337);
    uniform_int_distribution<long long> dist(1, 1000000000);

    long long M = -1;
    int query_count = 0;

    // Phase 1: Birthday Attack to find a collision
    // We walk random steps until we encounter a vertex label we have seen before.
    // The difference in distances gives a multiple M of the cycle length n.
    while (query_count < 200000) {
        long long step = dist(rng);
        cout << "walk " << step << endl;
        int label;
        cin >> label;
        query_count++;
        current_dist += step;
        
        if (label > max_label) max_label = label;
        current_label = label;

        if (seen.count(label)) {
            M = current_dist - seen[label];
            break;
        }
        seen[label] = current_dist;
    }

    // If no collision found (highly unlikely given constraints), guess max_label
    if (M == -1) {
        cout << "guess " << max_label << endl;
        return 0;
    }

    // Phase 2: Check divisors of M
    // We know n is a divisor of M and n >= max_label (since labels are 1..n).
    // We check divisors in increasing order. The first divisor d such that
    // walking d returns to the current vertex must be n.
    vector<long long> candidates;
    for (long long i = 1; i * i <= M; ++i) {
        if (M % i == 0) {
            if (i >= max_label) candidates.push_back(i);
            if (i * i != M) {
                long long d = M / i;
                if (d >= max_label) candidates.push_back(d);
            }
        }
    }
    sort(candidates.begin(), candidates.end());

    for (long long d : candidates) {
        if (query_count >= 200000) break;

        cout << "walk " << d << endl;
        int label;
        cin >> label;
        query_count++;

        // If we return to the same label, we found the period
        if (label == current_label) {
            cout << "guess " << d << endl;
            return 0;
        }
        current_label = label;
    }

    // Fallback if loop finishes
    cout << "guess " << M << endl;

    return 0;
}