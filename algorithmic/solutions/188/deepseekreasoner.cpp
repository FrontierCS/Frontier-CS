#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// WINDOW size determines how far we look ahead for a better match.
// A larger window improves approximation quality but increases time per step.
// Given the constraints and optimization (break on low cost), 200 is a safe balance.
const int WINDOW = 200; 

// Position lists for characters in S2
// pos2[c] stores consecutive indices of character c in S2.
// idx2[c] stores the current tracking index within pos2[c] to avoid re-scanning.
vector<int> pos2[128]; 
int idx2[128]; 

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    int n = (int)s1.length();
    int m = (int)s2.length();

    // 1. Build position lists for S2 efficiently
    // Count frequencies first to reserve memory and avoid reallocations
    int counts[128] = {0};
    for (char c : s2) {
        counts[c]++;
    }
    for (int i = 0; i < 128; i++) {
        if (counts[i] > 0) {
            pos2[i].reserve(counts[i]);
        }
    }
    // Fill the position vectors
    for (int i = 0; i < m; i++) {
        pos2[s2[i]].push_back(i);
    }

    string z;
    z.reserve(min(n, m));

    int p1 = 0;
    int p2 = 0;

    // Greedy matching with local lookahead
    while (p1 < n && p2 < m) {
        int best_k = -1;
        int best_cost = 2147483647; // Initialize with a large value
        int best_target = -1;

        // Only scan up to WINDOW characters ahead in S1
        int limit = n - p1;
        if (limit > WINDOW) limit = WINDOW;

        for (int k = 0; k < limit; k++) {
            char c = s1[p1 + k];
            
            // Access the position vector for the current character
            int &c_idx = idx2[c];
            const vector<int> &p_vec = pos2[c];
            
            // Advance the pointer in the position list to find the first occurrence >= p2
            // Since p2 strictly increases, this linear scan is amortized O(1)
            while (c_idx < (int)p_vec.size() && p_vec[c_idx] < p2) {
                c_idx++;
            }

            // If this character does not appear in the remaining part of S2
            if (c_idx == (int)p_vec.size()) {
                continue;
            }

            int target_pos = p_vec[c_idx];
            
            // Heuristic Cost Calculation:
            // We want to minimize the number of characters skipped in both strings.
            // skipped in S1 = k
            // skipped in S2 = target_pos - p2
            int cost = k + (target_pos - p2);

            if (cost < best_cost) {
                best_cost = cost;
                best_k = k;
                best_target = target_pos;

                // Optimization: Cost 0 is a direct match (S1[p1] == S2[p2]), optimal.
                if (best_cost == 0) break;
                
                // Optimization: Cost <= 1 is very low (e.g. adjacent match), acceptable as locally optimal.
                // This significantly speeds up the search loop.
                if (best_cost <= 1) break;
            }
        }

        if (best_k != -1) {
            // Found a suitable match
            z += s1[p1 + best_k];
            // Advance pointers past the matched characters
            p1 += best_k + 1;
            p2 = best_target + 1;
        } else {
            // No match found in the window, simply advance S1 pointer
            p1++;
        }
    }

    cout << z << "\n";

    return 0;
}