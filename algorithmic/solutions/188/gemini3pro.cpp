#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

// Problem: LCS Challenge (Approximation)
// Constraints: N, M <= 30,000,000. Time: 2.0s. Memory: 512MB.
// Strategy: A greedy heuristic that tries to minimize the "skip cost".
// At any mismatch (S1[p1] != S2[p2]), we consider two options:
// 1. Match S1[p1] with the next occurrence of that character in S2.
// 2. Match S2[p2] with the next occurrence of that character in S1.
// We choose the option that requires skipping fewer characters in the other string.
// This effectively approximates the Shortest Common Supersequence, which maximizes the LCS.

int main() {
    // Optimize standard I/O for large inputs
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    int n = (int)s1.length();
    int m = (int)s2.length();

    // Map each character to a list of its positions for fast lookups.
    // ASCII characters '0'-'9' and 'A'-'Z' fit within index 128.
    // Memory usage: roughly 4 bytes per character index -> 4 * (N + M) bytes ~ 240MB.
    vector<int> pos1[128];
    vector<int> pos2[128];

    // Build position tables
    for (int i = 0; i < n; i++) {
        pos1[(unsigned char)s1[i]].push_back(i);
    }
    for (int i = 0; i < m; i++) {
        pos2[(unsigned char)s2[i]].push_back(i);
    }

    // Pointers to the current valid index in the pos vectors to simulate a queue/stream
    vector<int> ptr1(128, 0);
    vector<int> ptr2(128, 0);

    string z;
    z.reserve(min(n, m)); // Optimization to reduce reallocations

    int p1 = 0;
    int p2 = 0;
    const int INF = 2000000000;

    // Linear scan O(N + M)
    while (p1 < n && p2 < m) {
        unsigned char c1 = (unsigned char)s1[p1];
        unsigned char c2 = (unsigned char)s2[p2];

        if (c1 == c2) {
            // Immediate match is always locally optimal for LCS construction
            z += (char)c1;
            p1++;
            p2++;
        } else {
            // Mismatch: Evaluate cost of matching c1 vs matching c2
            
            // Find next occurrence of c1 in S2 (>= p2)
            int next_c1_in_s2 = -1;
            while (ptr2[c1] < (int)pos2[c1].size() && pos2[c1][ptr2[c1]] < p2) {
                ptr2[c1]++;
            }
            if (ptr2[c1] < (int)pos2[c1].size()) {
                next_c1_in_s2 = pos2[c1][ptr2[c1]];
            }

            // Find next occurrence of c2 in S1 (>= p1)
            int next_c2_in_s1 = -1;
            while (ptr1[c2] < (int)pos1[c2].size() && pos1[c2][ptr1[c2]] < p1) {
                ptr1[c2]++;
            }
            if (ptr1[c2] < (int)pos1[c2].size()) {
                next_c2_in_s1 = pos1[c2][ptr1[c2]];
            }

            // Calculate skip costs
            // Cost is defined as the number of characters we must skip in the 'other' string to make the match.
            // Lower cost preserves more characters for future matches.
            int skip_cost_1 = (next_c1_in_s2 == -1) ? INF : (next_c1_in_s2 - p2);
            int skip_cost_2 = (next_c2_in_s1 == -1) ? INF : (next_c2_in_s1 - p1);

            if (skip_cost_1 == INF && skip_cost_2 == INF) {
                // Neither current character appears in the remainder of the other string.
                // Discard both.
                p1++;
                p2++;
            } else if (skip_cost_1 < skip_cost_2) {
                // Matching c1 (from S1) with S2 requires skipping fewer chars in S2
                z += (char)c1;
                p1++;
                p2 = next_c1_in_s2 + 1;
            } else {
                // Matching c2 (from S2) with S1 requires skipping fewer (or equal) chars in S1
                z += (char)c2;
                p1 = next_c2_in_s1 + 1;
                p2++;
            }
        }
    }

    cout << z << "\n";

    return 0;
}