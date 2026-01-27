#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <cstring>

using namespace std;

// Character mapping: 'A'-'Z' -> 0-25, '0'-'9' -> 26-35
inline int get_char_index(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= '0' && c <= '9') return c - '0' + 26;
    return 0; // Fallback
}

inline char get_char_value(int i) {
    if (i >= 0 && i <= 25) return (char)('A' + i);
    if (i >= 26 && i <= 35) return (char)('0' + (i - 26));
    return ' ';
}

// Memory efficient structure to store positions of characters
// Uses a Compressed Sparse Row (CSR) style layout to store lists of indices
struct CharPositions {
    int* positions;      // Multiple lists flattened into one array
    int starts[37];      // Start index for each character type in 'positions'
    int counts[36];      // Number of occurrences of each character
    int total_len;

    CharPositions() : positions(nullptr), total_len(0) {
        memset(starts, 0, sizeof(starts));
        memset(counts, 0, sizeof(counts));
    }

    void build(string& s) {
        total_len = s.length();
        // Pass 1: Count frequencies of each character
        for (char c : s) {
            counts[get_char_index(c)]++;
        }
        
        // Compute start indices (Prefix Sum) to determine where each char's list begins
        int current_idx = 0;
        for (int i = 0; i < 36; ++i) {
            starts[i] = current_idx;
            current_idx += counts[i];
        }
        starts[36] = current_idx; // Sentinel

        // Allocate memory exactly needed for the flattened positions array
        positions = new int[total_len];

        // Pass 2: Fill positions array
        // Use a temporary array to track current filling index for each char
        int fill_ptr[36];
        for(int i=0; i<36; ++i) fill_ptr[i] = starts[i];

        for (int i = 0; i < total_len; ++i) {
            int char_code = get_char_index(s[i]);
            positions[fill_ptr[char_code]++] = i;
        }
    }
    
    // Clean up memory manually
    void cleanup() {
        if (positions) {
            delete[] positions;
            positions = nullptr;
        }
    }
};

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    CharPositions p1, p2;
    
    // Process S1 and immediately free its string memory to save space
    p1.build(s1);
    string().swap(s1); // Force release memory of s1

    // Process S2 and free its memory
    p2.build(s2);
    string().swap(s2); // Force release memory of s2

    // Current pointers (indices into the 'positions' subarrays) for each character type
    // idx[k] tracks the progress through the list of positions for character k
    int idx1[36] = {0};
    int idx2[36] = {0};

    // Last matched positions in the original strings (0-indexed)
    // -1 indicates no characters matched yet
    int cur1 = -1;
    int cur2 = -1;

    string Z;
    // Reserve memory to avoid reallocation overhead during loop
    Z.reserve(min(p1.total_len, p2.total_len) / 2 + 10000);

    // Greedy Construction Loop
    while (true) {
        int best_char = -1;
        long long best_metric = -1;
        int cand_u = -1;
        int cand_v = -1;

        // Evaluate all 36 possible characters to append next
        for (int k = 0; k < 36; ++k) {
            // -- Check occurrence in S1 --
            int start1 = p1.starts[k];
            int cnt1 = p1.counts[k];
            int& ptr1 = idx1[k]; // Reference allows verifying progress in next iterations
            
            // Advance pointer in the position list to find first occurrence strictly after cur1
            while (ptr1 < cnt1 && p1.positions[start1 + ptr1] <= cur1) {
                ptr1++;
            }
            if (ptr1 >= cnt1) continue; // Character k not found in remainder of S1

            int u = p1.positions[start1 + ptr1];

            // -- Check occurrence in S2 --
            int start2 = p2.starts[k];
            int cnt2 = p2.counts[k];
            int& ptr2 = idx2[k];
            
            while (ptr2 < cnt2 && p2.positions[start2 + ptr2] <= cur2) {
                ptr2++;
            }
            if (ptr2 >= cnt2) continue; // Character k not found in remainder of S2

            int v = p2.positions[start2 + ptr2];

            // -- Heuristic Selection --
            // We want to pick a character that appears 'soon' in both strings to maximize future possibilities.
            // Cost Metric: Sum of indices (equivalent to sum of relative jumps).
            // Lower sum is better.
            long long metric = (long long)u + v;

            if (best_char == -1 || metric < best_metric) {
                best_char = k;
                best_metric = metric;
                cand_u = u;
                cand_v = v;
            } 
            else if (metric == best_metric) {
                // Tie-breaker: Minimize the difference in relative jumps.
                // This keeps the consumption of S1 and S2 balanced.
                int jump1 = u - cur1;
                int jump2 = v - cur2;
                int best_jump1 = cand_u - cur1;
                int best_jump2 = cand_v - cur2;
                
                if (abs(jump1 - jump2) < abs(best_jump1 - best_jump2)) {
                    best_char = k;
                    cand_u = u;
                    cand_v = v;
                }
            }
        }

        // If a valid character was found, append it and advance positions
        if (best_char != -1) {
            Z += get_char_value(best_char);
            cur1 = cand_u;
            cur2 = cand_v;
        } else {
            break; // No common characters possible in remainder
        }
    }

    cout << Z << endl;

    // Clean up dynamic memory
    p1.cleanup();
    p2.cleanup();

    return 0;
}