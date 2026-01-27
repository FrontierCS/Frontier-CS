#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstdio>
#include <cstring>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Character mapping: 0-9 -> 0-9, A-Z -> 10-35
inline int get_char_index(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'A' + 10;
}

const int MAX_LEN = 10000005;
char s1[MAX_LEN];
char s2[MAX_LEN];

// Positions of each character
vector<int> pos1[36];
vector<int> pos2[36];

int main() {
    // Input reading
    if (scanf("%s", s1) != 1) return 0;
    if (scanf("%s", s2) != 1) return 0;

    int n = strlen(s1);
    int m = strlen(s2);

    // Precompute positions
    for (int i = 0; i < n; i++) {
        pos1[get_char_index(s1[i])].push_back(i);
    }
    for (int i = 0; i < m; i++) {
        pos2[get_char_index(s2[i])].push_back(i);
    }

    // Pointers for current position in pos vectors
    // idx1[c] points to the smallest index k such that pos1[c][k] >= current_i
    vector<int> idx1(36, 0);
    vector<int> idx2(36, 0);

    int i = 0;
    int j = 0;
    
    // Use a string buffer for output to avoid frequent I/O
    string ans;
    ans.reserve(max(n, m) + 1000);

    while (i < n && j < m) {
        // 1. Skip Matches
        if (s1[i] == s2[j]) {
            ans += 'M';
            i++;
            j++;
            continue;
        }

        // 2. Find best resynchronization point
        // We look for a character c such that pos1[c][u] >= i and pos2[c][v] >= j
        // minimizing cost = max(u - i, v - j).
        
        int best_cost = 2000000000;
        int best_u = -1;
        int best_v = -1;

        // Iterate over all 36 characters
        for (int c = 0; c < 36; c++) {
            // Update pointers to be valid >= i and >= j
            // This loop runs efficiently because i and j only increase
            while (idx1[c] < pos1[c].size() && pos1[c][idx1[c]] < i) {
                idx1[c]++;
            }
            while (idx2[c] < pos2[c].size() && pos2[c][idx2[c]] < j) {
                idx2[c]++;
            }

            // If char c exists in remaining parts of both strings
            if (idx1[c] < pos1[c].size() && idx2[c] < pos2[c].size()) {
                int u = pos1[c][idx1[c]];
                int v = pos2[c][idx2[c]];
                
                int di = u - i;
                int dj = v - j;
                int cost = (di > dj) ? di : dj; // max(di, dj)

                if (cost < best_cost) {
                    best_cost = cost;
                    best_u = u;
                    best_v = v;
                } else if (cost == best_cost) {
                    // Tie-breaker: prefer closer to diagonal
                    int curr_diff = (di > dj) ? (di - dj) : (dj - di);
                    int best_di = best_u - i;
                    int best_dj = best_v - j;
                    int best_diff = (best_di > best_dj) ? (best_di - best_dj) : (best_dj - best_di);
                    
                    if (curr_diff < best_diff) {
                        best_u = u;
                        best_v = v;
                    }
                }
            }
        }

        // 3. Execute Move
        // If cost is too high (threshold), or no match found, we just substitute one char
        // Threshold heuristic: if we skip too much, we might miss better intricate alignments.
        // But for Edit Distance approx, aligning to a match is usually superior to random subs.
        // Let's use a very large threshold, effectively always taking the match unless none exists.
        
        if (best_cost == 2000000000) {
            // No common character found in remainder
            // Just output subs/insert/delete to finish
            // Prefer substitution as it consumes both
            ans += 'M';
            i++;
            j++;
        } else {
            // Output transform to reach (best_u, best_v)
            int di = best_u - i;
            int dj = best_v - j;

            // Strategy: Perform diagonal moves (Subst) as much as possible, then Ins/Del
            // This corresponds to the cost calculation max(di, dj)
            
            while (di > 0 && dj > 0) {
                ans += 'M';
                di--;
                dj--;
            }
            while (di > 0) {
                ans += 'D';
                di--;
            }
            while (dj > 0) {
                ans += 'I';
                dj--;
            }
            
            // Now we are at best_u, best_v. The characters match.
            ans += 'M';
            i = best_u + 1;
            j = best_v + 1;
        }
    }

    // Handle remaining suffixes
    while (i < n) {
        ans += 'D';
        i++;
    }
    while (j < m) {
        ans += 'I';
        j++;
    }

    // Output transcript
    // Using printf for potentially large string might be slightly faster than cout
    // But fputs/fwrite is better
    fwrite(ans.c_str(), 1, ans.length(), stdout);
    putchar('\n');

    return 0;
}