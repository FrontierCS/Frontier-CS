#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Fast I/O to handle large input size constraints efficiently
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Helper to map characters '0'-'9' and 'A'-'Z' to integers 0-35
inline int get_id(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'A' + 10;
}

// Helper to map integers 0-35 back to characters
inline char get_char(int id) {
    if (id < 10) return id + '0';
    return id - 10 + 'A';
}

int main() {
    fast_io();

    string s1, s2;
    // Read input strings
    if (!(cin >> s1 >> s2)) return 0;

    int n = s1.length();
    int m = s2.length();

    // Store positions of each character type in sorted order for both strings
    // 36 vectors for 36 character types
    static vector<int> pos1[36], pos2[36];
    
    for (int i = 0; i < n; ++i) {
        pos1[get_id(s1[i])].push_back(i);
    }
    for (int i = 0; i < m; ++i) {
        pos2[get_id(s2[i])].push_back(i);
    }

    // Pointers to the current index in the position lists
    // This avoids rescanning the lists from the beginning
    vector<int> ptr1(36, 0), ptr2(36, 0);

    // List of currently active character candidates
    // Initially contains all characters present in both strings
    vector<int> candidates;
    candidates.reserve(36);
    for (int c = 0; c < 36; ++c) {
        if (!pos1[c].empty() && !pos2[c].empty()) {
            candidates.push_back(c);
        }
    }

    string z;
    z.reserve(min(n, m));

    int cur1 = 0; // Current search start index in S1
    int cur2 = 0; // Current search start index in S2
    
    // Greedy construction loop
    while (!candidates.empty()) {
        int best_char = -1;
        long long min_cost = -1;
        int best_p1 = -1;
        int best_p2 = -1;

        // Remaining characters in subsequences
        long long rem1 = n - cur1;
        long long rem2 = m - cur2;
        
        // If either string is exhausted, we cannot foster more matches
        if (rem1 <= 0 || rem2 <= 0) break;

        // Iterate efficiently through valid candidates
        for (int i = 0; i < candidates.size(); ) {
            int c = candidates[i];
            
            // Advance pointer in pos1[c] to find first occurrence >= cur1
            vector<int> &p_list1 = pos1[c];
            int &pt1 = ptr1[c];
            while (pt1 < p_list1.size() && p_list1[pt1] < cur1) {
                pt1++;
            }

            // Advance pointer in pos2[c] to find first occurrence >= cur2
            vector<int> &p_list2 = pos2[c];
            int &pt2 = ptr2[c];
            while (pt2 < p_list2.size() && p_list2[pt2] < cur2) {
                pt2++;
            }

            // If character c is exhausted in either string, remove from candidates
            if (pt1 >= p_list1.size() || pt2 >= p_list2.size()) {
                // Efficient removal: swap with back and pop
                candidates[i] = candidates.back();
                candidates.pop_back();
                // Do not increment i, re-evaluate this index
                continue;
            }

            // Indices of the found character
            int p1 = p_list1[pt1];
            int p2 = p_list2[pt2];

            // Heuristic scoring:
            // We want to minimize the "cost" of skipping characters.
            // Cost is weighted by the remaining length of the *other* string.
            // Logic: Skipping characters in S1 is more expensive if S1 is the bottleneck (short remaining),
            // but actually we map it as: Cost = skip1 * rem2 + skip2 * rem1.
            // If S1 is scarce (rem1 small), skipping in S2 (skip2) is penalized less (coeff rem1 is small),
            // whereas skipping in S1 (skip1) is penalized more (coeff rem2 is large).
            // This balances the consumption of the strings.
            long long skip1 = p1 - cur1;
            long long skip2 = p2 - cur2;
            
            long long cost = skip1 * rem2 + skip2 * rem1;

            // Greedy selection
            if (best_char == -1 || cost < min_cost) {
                min_cost = cost;
                best_char = c;
                best_p1 = p1;
                best_p2 = p2;
            } else if (cost == min_cost) {
                // Tie breaker: prefer earlier index in S1
                if (p1 < best_p1) {
                     best_char = c;
                     best_p1 = p1;
                     best_p2 = p2;
                }
            }
            
            i++;
        }

        if (best_char != -1) {
            z += get_char(best_char);
            cur1 = best_p1 + 1;
            cur2 = best_p2 + 1;
        } else {
            break; 
        }
    }

    cout << z << "\n";

    return 0;
}