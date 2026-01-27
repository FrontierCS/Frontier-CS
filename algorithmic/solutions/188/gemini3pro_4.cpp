#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>

using namespace std;

// Fast I/O setup
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

const int MAX_CHAR = 36;
const int INF = 2000000000;

// We use global vectors to store positions of each character in both strings.
// This approach uses O(N+M) memory, which fits within 512MB for N, M <= 30,000,000.
// (30M integers is approx 120MB, we have two such sets plus overhead -> ~300MB safe).
vector<int> p1[MAX_CHAR];
vector<int> p2[MAX_CHAR];

// Pointers to the current index in the position vectors
int pt1[MAX_CHAR];
int pt2[MAX_CHAR];

// Cached values of the next valid occurrence index in the strings
// This minimizes random access to the large vectors during the inner loop
int curr_u[MAX_CHAR];
int curr_v[MAX_CHAR];

// Precomputed sizes of position vectors
int sz1[MAX_CHAR];
int sz2[MAX_CHAR];

// Helper to map characters '0'-'9' and 'A'-'Z' to 0-35
inline int get_id(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'A' + 10;
}

// Helper to map ID back to character
inline char get_char(int id) {
    if (id < 10) return id + '0';
    return id - 10 + 'A';
}

int main() {
    fast_io();

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    int n = s1.length();
    int m = s2.length();

    // Build adjacency lists for character positions
    for (int i = 0; i < n; i++) {
        p1[get_id(s1[i])].push_back(i);
    }
    for (int i = 0; i < m; i++) {
        p2[get_id(s2[i])].push_back(i);
    }

    // Initialize state
    for (int k = 0; k < MAX_CHAR; k++) {
        pt1[k] = 0;
        pt2[k] = 0;
        sz1[k] = p1[k].size();
        sz2[k] = p2[k].size();
        
        // Initialize current next valid positions
        if (sz1[k] > 0) curr_u[k] = p1[k][0];
        else curr_u[k] = INF;
        
        if (sz2[k] > 0) curr_v[k] = p2[k][0];
        else curr_v[k] = INF;
    }

    int i = -1; // Current index in s1
    int j = -1; // Current index in s2
    
    // Result string
    string res;
    // Heuristic reservation to prevent multiple reallocations
    res.reserve(min(n, m));

    // Greedy construction loop
    while (true) {
        int best_c = -1;
        long long min_cost = -1;
        int best_u = -1;
        int best_v = -1;

        // Iterate through all possible next characters
        for (int k = 0; k < MAX_CHAR; k++) {
            // Lazy update: if cached position is <= current index i, it's invalid.
            // Advance pointer to find next valid position > i.
            if (curr_u[k] <= i) {
                while (pt1[k] < sz1[k] && p1[k][pt1[k]] <= i) {
                    pt1[k]++;
                }
                if (pt1[k] < sz1[k]) curr_u[k] = p1[k][pt1[k]];
                else curr_u[k] = INF;
            }

            // Same for string s2
            if (curr_v[k] <= j) {
                while (pt2[k] < sz2[k] && p2[k][pt2[k]] <= j) {
                    pt2[k]++;
                }
                if (pt2[k] < sz2[k]) curr_v[k] = p2[k][pt2[k]];
                else curr_v[k] = INF;
            }
            
            // If character k exists in both strings after current positions
            if (curr_u[k] != INF && curr_v[k] != INF) {
                // Heuristic: Minimize the sum of skipped distance
                // Cost = (next_pos_s1 - current_s1) + (next_pos_s2 - current_s2)
                // Minimal possible cost is (i+1 - i) + (j+1 - j) = 2.
                long long cost = (long long)(curr_u[k] - i) + (curr_v[k] - j);
                
                // Optimization: If cost is 2, it's a perfect immediate match. Take it.
                if (cost == 2) {
                    best_c = k;
                    best_u = curr_u[k];
                    best_v = curr_v[k];
                    min_cost = 2;
                    break;
                }

                if (best_c == -1 || cost < min_cost) {
                    min_cost = cost;
                    best_c = k;
                    best_u = curr_u[k];
                    best_v = curr_v[k];
                } else if (cost == min_cost) {
                    // Tie-breaker: Keep indices balanced (minimize difference in advancement)
                    int diff_curr = abs((curr_u[k] - i) - (curr_v[k] - j));
                    int diff_best = abs((best_u - i) - (best_v - j));
                    if (diff_curr < diff_best) {
                         best_c = k;
                         best_u = curr_u[k];
                         best_v = curr_v[k];
                    }
                }
            }
        }

        // If no valid character found, we are done
        if (best_c == -1) break;

        // Append character and update positions
        res += get_char(best_c);
        i = best_u;
        j = best_v;
    }

    cout << res << endl;

    return 0;
}