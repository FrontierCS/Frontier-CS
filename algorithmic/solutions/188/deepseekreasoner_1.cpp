#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Fast I/O configuration to handle large input within time limits
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Map characters '0'-'9' and 'A'-'Z' to integers 0-35
// This allows using arrays/vectors instead of maps for O(1) access
inline int get_id(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'A' + 10;
}

// Map integers 0-35 back to characters for output
inline char get_char(int id) {
    if (id < 10) return id + '0';
    return id - 10 + 'A';
}

// Global data structures for storing positions of each character
// occ[k] stores the indices of character k in increasing order
vector<int> occ1[36];
vector<int> occ2[36];

// Pointers to the current valid position index in each occ vector
// This avoids searching through the vectors repeatedly
int ptrs1[36];
int ptrs2[36];

int main() {
    fast_io();

    string s;

    // --- Process S1 ---
    if (!(cin >> s)) return 0;
    int n = s.length();
    
    // Count frequencies first to reserve exact memory for vectors.
    // This prevents memory fragmentation and reallocation overhead.
    vector<int> counts(36, 0);
    for (char c : s) counts[get_id(c)]++;
    for (int i = 0; i < 36; ++i) occ1[i].reserve(counts[i]);
    
    // Fill occurrences for S1
    for (int i = 0; i < n; ++i) occ1[get_id(s[i])].push_back(i);
    
    // Clear s to free approximately 30MB of memory before reading S2
    string().swap(s);

    // --- Process S2 ---
    if (!(cin >> s)) return 0;
    int m = s.length();
    
    fill(counts.begin(), counts.end(), 0);
    for (char c : s) counts[get_id(c)]++;
    for (int i = 0; i < 36; ++i) occ2[i].reserve(counts[i]);
    
    // Fill occurrences for S2
    for (int i = 0; i < m; ++i) occ2[get_id(s[i])].push_back(i);
    
    // Clear s again to free memory
    string().swap(s);

    // Current matched positions in S1 and S2 (initially -1)
    int idx1 = -1;
    int idx2 = -1;
    
    string res;
    // Heuristic: Reserve some memory for result to improve append speed
    // Can reserve smaller amount if memory is critical, but std::string growth is usually fine.
    
    // --- Greedy Matching Loop ---
    while (true) {
        int best_char = -1;
        long long min_cost = -1;
        int best_n1 = -1;
        int best_n2 = -1;

        // Calculate remaining characters in both strings
        long long rem1 = n - 1LL - idx1; 
        long long rem2 = m - 1LL - idx2;
        
        // If either string is exhausted, we stop
        if (rem1 <= 0 || rem2 <= 0) break;

        // Check all 36 possible characters for the next move
        for (int c = 0; c < 36; ++c) {
            // Find first occurrence of char c after idx1 in S1
            vector<int> &vec1 = occ1[c];
            int &p1 = ptrs1[c];
            int sz1 = (int)vec1.size();
            
            // Move pointer forward to find valid occurrence
            // Since idx1 only increases, p1 only moves forward. Total complexity O(N).
            while (p1 < sz1 && vec1[p1] <= idx1) {
                p1++;
            }
            if (p1 == sz1) continue; // Character exhausted in S1

            // Find first occurrence of char c after idx2 in S2
            vector<int> &vec2 = occ2[c];
            int &p2 = ptrs2[c];
            int sz2 = (int)vec2.size();
            
            while (p2 < sz2 && vec2[p2] <= idx2) {
                p2++;
            }
            if (p2 == sz2) continue; // Character exhausted in S2

            int n1 = vec1[p1];
            int n2 = vec2[p2];
            
            // --- Cost Calculation Heuristic ---
            // We want to pick a character that "consumes" the least percentage of remaining strings.
            // Metric to minimize: (jump1 / rem1) + (jump2 / rem2)
            // jump1 = n1 - idx1 (number of chars advanced in S1)
            // jump2 = n2 - idx2 (number of chars advanced in S2)
            // To compare two candidates without floating point division, we essentially minimize:
            // Cost = jump1 * rem2 + jump2 * rem1
            
            long long jump1 = n1 - idx1;
            long long jump2 = n2 - idx2;
            
            long long current_cost = jump1 * rem2 + jump2 * rem1;
            
            if (best_char == -1 || current_cost < min_cost) {
                min_cost = current_cost;
                best_char = c;
                best_n1 = n1;
                best_n2 = n2;
            }
        }

        if (best_char != -1) {
            res += get_char(best_char);
            idx1 = best_n1;
            idx2 = best_n2;
        } else {
            // No common character found in the remainders of S1 and S2
            break; 
        }
    }
    
    cout << res << "\n";

    return 0;
}