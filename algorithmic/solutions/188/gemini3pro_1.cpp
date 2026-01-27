#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstdio>
#include <cstring>

using namespace std;

// Buffer for Fast I/O
const int BUFFER_SIZE = 1 << 18; // 256KB
char buffer[BUFFER_SIZE];
int buffer_pos = 0, buffer_len = 0;

inline int read_char() {
    if (buffer_pos >= buffer_len) {
        buffer_pos = 0;
        buffer_len = fread(buffer, 1, BUFFER_SIZE, stdin);
        if (buffer_len == 0) return EOF;
    }
    return (unsigned char)buffer[buffer_pos++];
}

inline void read_string(string &s) {
    s.clear();
    // Pre-allocate to avoid reallocations. 
    s.reserve(30000005); 
    int c = read_char();
    // Skip whitespace
    while (c <= 32) {
        if (c == EOF) return;
        c = read_char();
    }
    // Read valid characters
    while (c > 32) {
        s.push_back((char)c);
        c = read_char();
    }
}

// Map characters to 0-35
inline int get_idx(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= '0' && c <= '9') return c - '0' + 26;
    return -1;
}

// Global position lists for S2
// pos2[c] stores ordered indices of character c in S2
vector<int> pos2[36];
// Pointers to the current relevant index in pos2
int ptr2[36];

int main() {
    // Optimize standard streams
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s1, s2;
    read_string(s1);
    read_string(s2);

    int n = (int)s1.length();
    int m = (int)s2.length();

    // Build S2 position tables
    for (int i = 0; i < m; i++) {
        int idx = get_idx(s2[i]);
        if (idx != -1) {
            pos2[idx].push_back(i);
        }
    }

    // Prepare result string
    string z;
    z.reserve(min(n, m));

    int curr1 = 0;
    int curr2 = 0;
    
    // Initialize pointers
    memset(ptr2, 0, sizeof(ptr2));

    // Limit lookahead to balance speed and quality
    const int WINDOW_LIMIT = 500; 

    while (curr1 < n && curr2 < m) {
        long long best_cost = -1;
        int best_idx1 = -1;
        int best_idx2 = -1;
        
        long long r1 = n - curr1;
        long long r2 = m - curr2;
        
        // Scan a window in S1
        for (int k = 0; k < WINDOW_LIMIT; k++) {
            int idx1 = curr1 + k;
            if (idx1 >= n) break;
            
            // Pruning:
            // The cost of skipping 'k' characters in S1 is at least k * r2.
            // If this minimum cost exceeds the best cost found so far,
            // subsequent matches in this window will definitely be worse.
            if (best_cost != -1 && (long long)k * r2 >= best_cost) {
                break;
            }

            int char_code = get_idx(s1[idx1]);
            if (char_code == -1) continue; 
            
            // Fast forward the pointer in S2 to be >= curr2
            // Since curr2 only increases, ptr2 also only increases.
            // This is amortized O(M) over the whole execution.
            while (ptr2[char_code] < (int)pos2[char_code].size() && 
                   pos2[char_code][ptr2[char_code]] < curr2) {
                ptr2[char_code]++;
            }
            
            // Check if this character exists in S2 after curr2
            if (ptr2[char_code] < (int)pos2[char_code].size()) {
                int idx2 = pos2[char_code][ptr2[char_code]];
                
                // Heuristic Cost Function:
                // We want to minimize the loss of potential future matches.
                // Loss is proportional to skipped length weighted by remaining length of OTHER string.
                // (k) chars skipped in S1 consumes "space" relative to S2's scarcity (r2).
                // (idx2 - curr2) chars skipped in S2 consumes "space" relative to S1's scarcity (r1).
                long long cost = (long long)k * r2 + (long long)(idx2 - curr2) * r1;
                
                if (best_cost == -1 || cost < best_cost) {
                    best_cost = cost;
                    best_idx1 = idx1;
                    best_idx2 = idx2;
                }
            }
        }
        
        if (best_idx1 != -1) {
            // Found a match
            z.push_back(s1[best_idx1]);
            curr1 = best_idx1 + 1;
            curr2 = best_idx2 + 1;
        } else {
            // No match found in the entire window.
            // This implies the characters in S1[curr1 ... curr1+WINDOW_LIMIT-1]
            // do not appear in the remainder of S2.
            // We can safely skip this entire block to save time.
            curr1 += WINDOW_LIMIT;
        }
    }

    // Output result
    fwrite(z.c_str(), 1, z.length(), stdout);
    putchar('\n');

    return 0;
}