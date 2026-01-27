/**
 * Approximate Edit Distance Solution
 * Approach:
 * 1. Find "anchors" (matching k-mers) between S1 and S2 using a sliding window.
 *    - To maintain efficiency, we scan S1 with a fixed 'STRIDE' (e.g., 32 chars).
 *    - We search for the corresponding substring in S2 within a predicted window.
 *    - The prediction adapts based on the remaining lengths of S1 and S2 to handle aspect ratio.
 * 2. This decomposes the large problem into many small sub-problems (blocks) between anchors.
 * 3. Solve each block:
 *    - If the block is small (<= MAX_GAP_DIM), use standard O(N*M) Dynamic Programming.
 *    - If the block is large (anchoring failed / large indel), use a linear heuristic (Diagonal fallback).
 * 
 * Complexity:
 * - Anchoring: O(N * WindowSize / Stride). With chosen constants, effective ops ~ 10^8.
 * - Gap Filling: O(Total Area of gaps). Because anchors are dense, gaps are small. Effective ops ~ 10^8.
 * - Overall Time: Well within 3.0s. Memory: ~50MB.
 */

#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cstdint>

using namespace std;

// Maximum dimension for full DP. Blocks larger than this use fallback.
const int MAX_GAP_DIM = 2500; 

// DP Tables for gap alignment
// cost table stores edit distance
// dir table stores backtrack direction: 0=Match, 1=Delete, 2=Insert
// Allocated statically to avoid reallocation overhead
int dp_cost[MAX_GAP_DIM + 5][MAX_GAP_DIM + 5];
uint8_t dp_dir[MAX_GAP_DIM + 5][MAX_GAP_DIM + 5]; 

string S1, S2;
int N, M;

// Function to align a sub-block S1[r1...r1+len1-1] vs S2[c1...c1+len2-1]
void append_alignment(string& transcript, int r1, int c1, int len1, int len2) {
    if (len1 == 0 && len2 == 0) return;
    
    // Fallback logic for unexpectedly large blocks (missed anchors)
    // Simply matches the minimum length along diagonal, then deletes/inserts rest.
    if (len1 > MAX_GAP_DIM || len2 > MAX_GAP_DIM) {
        int min_len = min(len1, len2);
        for (int i = 0; i < min_len; ++i) transcript += 'M';
        for (int i = min_len; i < len1; ++i) transcript += 'D';
        for (int i = min_len; i < len2; ++i) transcript += 'I';
        return;
    }

    // Initialize DP base cases
    // Cost of deletions (first col)
    for (int i = 0; i <= len1; ++i) {
        dp_cost[i][0] = i; 
        dp_dir[i][0] = 1; 
    }
    // Cost of insertions (first row)
    for (int j = 0; j <= len2; ++j) {
        dp_cost[0][j] = j; 
        dp_dir[0][j] = 2; 
    }

    // Pointers for fast character access
    const char* str1 = S1.c_str() + r1;
    const char* str2 = S2.c_str() + c1;

    // Standard DP loop
    for (int i = 1; i <= len1; ++i) {
        char c1_char = str1[i-1];
        for (int j = 1; j <= len2; ++j) {
            char c2_char = str2[j-1];
            
            // Calculate costs
            int costSub = dp_cost[i-1][j-1] + (c1_char == c2_char ? 0 : 1);
            int costDel = dp_cost[i-1][j] + 1;
            int costIns = dp_cost[i][j-1] + 1;
            
            // Choose minimum cost and record direction
            if (costSub <= costDel && costSub <= costIns) {
                dp_cost[i][j] = costSub;
                dp_dir[i][j] = 0; // Match/Sub
            } else if (costDel <= costIns) {
                dp_cost[i][j] = costDel;
                dp_dir[i][j] = 1; // Delete from S1
            } else {
                dp_cost[i][j] = costIns;
                dp_dir[i][j] = 2; // Insert from S2
            }
        }
    }

    // Backtrack to reconstruct the path
    string chunk;
    chunk.reserve(len1 + len2);
    int i = len1, j = len2;
    while(i > 0 || j > 0) {
        if (i > 0 && j > 0 && dp_dir[i][j] == 0) {
            chunk.push_back('M');
            i--; j--;
        } else if (i > 0 && (j == 0 || dp_dir[i][j] == 1)) {
            chunk.push_back('D');
            i--;
        } else {
            chunk.push_back('I');
            j--;
        }
    }
    
    // Append reversed chunk to the main transcript
    for(int k = (int)chunk.size()-1; k >= 0; k--) {
        transcript.push_back(chunk[k]);
    }
}

int main() {
    // Fast I/O
    ios::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> S1 >> S2)) return 0;
    N = S1.length();
    M = S2.length();

    // Handle trivial empty cases
    if (N == 0) { cout << string(M, 'I') << endl; return 0; }
    if (M == 0) { cout << string(N, 'D') << endl; return 0; }

    // Tuning constants
    int STRIDE = 32;       // Try to anchor every 32 chars in S1
    int SEARCH_WINDOW = 400; // Look +/- 400 chars in S2 for a match
    int K_MER = 8;         // Match length of 8 chars

    struct Pt { int r, c; };
    vector<Pt> anchors;
    // Pre-allocate to avoid resizing
    anchors.reserve(N / STRIDE + 1000);
    anchors.push_back({0, 0});

    int last_r = 0;
    int last_c = 0;

    // Scan S1 to find anchors
    for (int r = STRIDE; r < N - K_MER; r += STRIDE) {
        // Dynamic slope calculation: project roughly where 'r' should be in S2
        // relative to the remaining unaligned portions.
        double slope = (double)(M - last_c) / (double)(N - last_r);
        int center_c = last_c + (int)((r - last_r) * slope);
        
        // Define search range in S2
        int start_c = max(last_c + 1, center_c - SEARCH_WINDOW);
        int end_c = min(M - K_MER, center_c + SEARCH_WINDOW);

        // Ensure we advance in S2
        if (start_c <= last_c) start_c = last_c + 1; 

        if (start_c > end_c) continue;

        int found_c = -1;
        const char* p1 = S1.c_str() + r;
        
        // Linear scan in local window
        for (int c = start_c; c <= end_c; ++c) {
            const char* p2 = S2.c_str() + c;
            bool match = true;
            // Check k-mer match
            for (int k = 0; k < K_MER; ++k) {
                if (p1[k] != p2[k]) {
                    match = false;
                    break;
                }
            }
            if (match) {
                found_c = c;
                break; // Take the first valid match found
            }
        }

        if (found_c != -1) {
            // Check if the gap created is manageable by DP
            int dr = r - last_r;
            int dc = found_c - last_c;
            if (dr > MAX_GAP_DIM || dc > MAX_GAP_DIM) {
                // Gap too big, skip anchor to try and find a better synchronization later
                // or force fallback on a larger range eventually.
                continue; 
            }
            anchors.push_back({r, found_c});
            last_r = r;
            last_c = found_c;
        }
    }
    // Add the final endpoint
    anchors.push_back({N, M});

    // Build the result
    string transcript;
    transcript.reserve(N + M);

    for (size_t k = 0; k < anchors.size() - 1; ++k) {
        int r_len = anchors[k+1].r - anchors[k].r;
        int c_len = anchors[k+1].c - anchors[k].c;
        append_alignment(transcript, anchors[k].r, anchors[k].c, r_len, c_len);
    }
    
    cout << transcript << endl;

    return 0;
}