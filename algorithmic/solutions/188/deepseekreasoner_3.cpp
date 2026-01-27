/*
Solution for LCS Challenge (Approximation)

Approach:
This solution uses a greedy heuristic strategy known as "Best Next Match" or "Min-Distance Greedy".
Given current positions i in S1 and j in S2, we look at the next occurrence of every possible character c ('A'-'Z', '0'-'9').
Let the next occurrence of c in S1 be u and in S2 be v.
We choose the character c that minimizes (u + v). 
Minimizing the sum of indices is equivalent to minimizing the sum of skipped characters in both strings,
((u - i) + (v - j)), which heuristically preserves the most potential for future matches.
This is efficient and runs in O(N + M + K * |Z|) time where K=36 (alphabet size), effectively linear.

Memory management:
Since N, M <= 30,000,000, storing DP tables is impossible.
We store the positions of each character in CSR (Compressed Sparse Row) format using flat arrays to minimize overhead.
Total memory usage is approximately (N + M) * 4 bytes + Buffer, fitting well within 512MB.
*/

#include <iostream>
#include <vector>
#include <cstdio>
#include <cstring>
#include <algorithm>
#include <string>

using namespace std;

// Map characters to indices 0-35
// Digits '0'-'9' -> 0-9
// Letters 'A'-'Z' -> 10-35
inline int get_id(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'Z') return c - 'A' + 10;
    return -1;
}

// Map indices 0-35 back to characters
inline char get_char(int id) {
    if (id < 10) return id + '0';
    return id - 10 + 'A';
}

// Global data structures for positions
// We use integer arrays instead of vector<int> to ensure precise memory control
// and avoid re-allocation overheads near the memory limit.
int* flat_p1 = nullptr;
int start1[37]; 
int count1[36]; 

int* flat_p2 = nullptr;
int start2[37];
int count2[36];

// Input buffer size ~30MB
const size_t MAX_BUF = 30000010;
char* buf;

void build_index(int* &flat_p, int* start_arr, int* count_arr) {
    // 1. Count frequencies to determine allocation size
    memset(count_arr, 0, 36 * sizeof(int));
    int len = 0;
    for (int i = 0; buf[i]; ++i) {
        char c = buf[i];
        if (c == '\n' || c == '\r') {
            buf[i] = 0;
            break;
        }
        int id = get_id(c);
        if (id != -1) {
            count_arr[id]++;
            len++;
        }
    }
    
    // 2. Allocate flat position array
    flat_p = new int[len];
    
    // 3. Compute start indices (prefix sum) for CSR format
    start_arr[0] = 0;
    for (int c = 0; c < 36; ++c) {
        start_arr[c+1] = start_arr[c] + count_arr[c];
    }
    
    // 4. Fill array using temporary write pointers
    int fill_ptr[36];
    for(int c=0; c<36; ++c) fill_ptr[c] = start_arr[c];
    
    for (int i = 0; buf[i]; ++i) { 
        int id = get_id(buf[i]);
        if (id != -1) {
            flat_p[fill_ptr[id]++] = i;
        }
    }
}

int main() {
    // Allocate large buffer on heap to prevent stack overflow
    buf = new char[MAX_BUF];
    
    // Process S1
    if (!fgets(buf, MAX_BUF, stdin)) return 0;
    build_index(flat_p1, start1, count1);
    
    // Process S2
    if (!fgets(buf, MAX_BUF, stdin)) return 0;
    build_index(flat_p2, start2, count2);
    
    // Free input buffer to reclaim memory (~30MB)
    delete[] buf; 
    
    // Current pointers (offsets within each character's slice in flat_p)
    int ptr1[36] = {0};
    int ptr2[36] = {0};
    
    const int INF = 2000000000;
    // Current valid cached positions in S1 and S2 for each character
    int val1[36]; 
    int val2[36]; 
    
    // Initialize current valid positions
    for (int c = 0; c < 36; ++c) {
        if (ptr1[c] < count1[c]) val1[c] = flat_p1[start1[c] + ptr1[c]];
        else val1[c] = INF;
        
        if (ptr2[c] < count2[c]) val2[c] = flat_p2[start2[c] + ptr2[c]];
        else val2[c] = INF;
    }
    
    int curr_i = 0; // Current lower bound index in S1
    int curr_j = 0; // Current lower bound index in S2
    
    string Z;
    // Heuristically reserve memory
    Z.reserve(min(start1[36], start2[36]));
    
    // Greedy construction loop
    while (true) {
        int best_c = -1;
        int min_cost = INF;
        
        // Find character that minimizes sum of positions (approximating minimal skips)
        // Optimization: checking 36 characters is extremely fast (L1 cache)
        for (int c = 0; c < 36; ++c) {
            int v1 = val1[c];
            if (v1 == INF) continue;
            
            int v2 = val2[c];
            if (v2 == INF) continue;
            
            int combined = v1 + v2;
            
            if (combined < min_cost) {
                min_cost = combined;
                best_c = c;
            }
        }
        
        // No valid character found in both remaining substrings
        if (best_c == -1) break;
        
        // Append best character
        Z += get_char(best_c);
        
        // Update current bounds (move past the used characters)
        curr_i = val1[best_c] + 1;
        curr_j = val2[best_c] + 1;
        
        // Update cached positions for all characters to be valid (>= curr_i, curr_j)
        // Since indices only increase, we simply advance the pointers forward.
        // The total number of advancements over the whole execution is N + M.
        for (int c = 0; c < 36; ++c) {
            // Update S1 value if outdated
            if (val1[c] < curr_i) {
                int start = start1[c];
                int cnt = count1[c];
                int p = ptr1[c];
                
                // Advance pointer to find next valid occurrence
                while (p < cnt && flat_p1[start + p] < curr_i) {
                    p++;
                }
                
                ptr1[c] = p;
                if (p < cnt) val1[c] = flat_p1[start + p];
                else val1[c] = INF;
            }
            
            // Update S2 value if outdated
             if (val2[c] < curr_j) {
                int start = start2[c];
                int cnt = count2[c];
                int p = ptr2[c];
                
                while (p < cnt && flat_p2[start + p] < curr_j) {
                    p++;
                }
                
                ptr2[c] = p;
                if (p < cnt) val2[c] = flat_p2[start + p];
                else val2[c] = INF;
            }
        }
    }
    
    // Output result
    fwrite(Z.c_str(), 1, Z.size(), stdout);
    putchar('\n');
    
    return 0;
}