#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Helper function to map '0'-'9' and 'A'-'Z' to 0-35
inline int get_char_index(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'A' + 10;
}

// Helper function to map 0-35 back to characters
inline char get_char_from_index(int idx) {
    if (idx < 10) return idx + '0';
    return idx - 10 + 'A';
}

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    int n = (int)s1.length();
    int m = (int)s2.length();

    // Precompute positions of each character in S2 for O(1) lookups (amortized)
    // positions2[c] stores a sorted list of indices where char c appears in s2
    vector<vector<int>> positions2(36);
    for (int i = 0; i < m; ++i) {
        positions2[get_char_index(s2[i])].push_back(i);
    }
    
    // Add a sentinel value larger than any valid index to avoid boundary checks
    for(int i=0; i<36; ++i) {
        positions2[i].push_back(m + 1); 
    }

    // Pointers to the current relevant position in positions2 lists
    vector<int> ptr2(36, 0);

    string z;
    z.reserve(min(n, m));

    int cur1 = -1;
    int cur2 = -1;

    // Used to ensure we only check the first occurrence of each character type in the current S1 scan window
    vector<int> last_seen_in_step(36, 0);
    int step_counter = 0;

    // Greedy construction loop
    while (cur1 < n - 1 && cur2 < m - 1) {
        step_counter++;
        
        int best_char = -1;
        int best_pos1 = -1;
        int best_pos2 = -1;
        int min_cost = 2000000000; // Initialize with infinity

        // Scan S1 starting from the next character
        // We limit the scan based on the best cost found so far to maintain efficiency
        for (int i = cur1 + 1; i < n; ++i) {
            int dist1 = i - cur1;
            
            // Pruning: if the jump in S1 alone is >= min_cost, 
            // the total cost (dist1 + dist2) will definitely be >= min_cost (since dist2 >= 1).
            if (dist1 >= min_cost) break;

            int c_idx = get_char_index(s1[i]);

            // If we have already evaluated this character in the current scan, skip it.
            // We are interested in the earliest occurrence in S1 relative to cur1.
            if (last_seen_in_step[c_idx] == step_counter) continue;
            last_seen_in_step[c_idx] = step_counter;

            // Find the first occurrence of c in S2 after cur2
            // We use the maintained pointers ptr2 to find this efficiently (amortized O(1))
            int p2_idx = ptr2[c_idx];
            while (positions2[c_idx][p2_idx] <= cur2) {
                p2_idx++;
            }
            // Update pointer: since cur2 only increases, we never need to look back
            ptr2[c_idx] = p2_idx;

            int pos2 = positions2[c_idx][p2_idx];

            // If character not found in remaining S2
            if (pos2 >= m) continue;

            int dist2 = pos2 - cur2;
            
            // Heuristic cost: sum of jumps in both strings.
            // We want to minimize skipped characters.
            int cost = dist1 + dist2;

            if (cost < min_cost) {
                min_cost = cost;
                best_char = c_idx;
                best_pos1 = i;
                best_pos2 = pos2;
                
                // Optimization: Cost 2 corresponds to dist1=1 and dist2=1.
                // This is the optimal local move (matching immediate next chars).
                if (cost == 2) break;
            }
            else if (cost == min_cost) {
                // Tie-breaking: prefer balanced jumps to avoid exhausting one string too early
                int current_diff = abs((best_pos1 - cur1) - (best_pos2 - cur2));
                int new_diff = abs(dist1 - dist2);
                if (new_diff < current_diff) {
                    best_char = c_idx;
                    best_pos1 = i;
                    best_pos2 = pos2;
                }
            }
        }

        if (best_char != -1) {
            z += get_char_from_index(best_char);
            cur1 = best_pos1;
            cur2 = best_pos2;
        } else {
            // No common character found in the remainder
            break;
        }
    }

    cout << z << endl;

    return 0;
}