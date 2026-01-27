#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstring>

using namespace std;

// Globals for convenience
string S1, S2;
int N, M;

// Output buffer
string transcript;

// --- Gap Solver (DP) ---

// Standard DP for small blocks
string solve_small_dp(int i1, int i2, int len1, int len2) {
    if (len1 == 0) return string(len2, 'I');
    if (len2 == 0) return string(len1, 'D');

    // Flattened DP table
    // Using unsigned short to save memory, assuming cost < 65535 for small blocks (4000x4000 max)
    vector<unsigned short> cost((len1 + 1) * (len2 + 1));
    auto idx = [&](int r, int c) { return r * (len2 + 1) + c; };

    for (int r = 0; r <= len1; ++r) cost[idx(r, 0)] = r;
    for (int c = 0; c <= len2; ++c) cost[idx(0, c)] = c;

    for (int r = 1; r <= len1; ++r) {
        for (int c = 1; c <= len2; ++c) {
            int match_cost = (S1[i1 + r - 1] == S2[i2 + c - 1]) ? 0 : 1;
            int c_sub = cost[idx(r - 1, c - 1)] + match_cost;
            int c_del = cost[idx(r - 1, c)] + 1;
            int c_ins = cost[idx(r, c - 1)] + 1;
            cost[idx(r, c)] = min({c_sub, c_del, c_ins});
        }
    }

    // Backtrack
    string res;
    res.reserve(len1 + len2);
    int r = len1, c = len2;
    while (r > 0 || c > 0) {
        if (r > 0 && c > 0) {
            int match_cost = (S1[i1 + r - 1] == S2[i2 + c - 1]) ? 0 : 1;
            if (cost[idx(r, c)] == cost[idx(r - 1, c - 1)] + match_cost) {
                res += 'M';
                r--; c--;
                continue;
            }
        }
        if (r > 0 && cost[idx(r, c)] == cost[idx(r - 1, c)] + 1) {
            res += 'D';
            r--;
        } else {
            res += 'I';
            c--;
        }
    }
    reverse(res.begin(), res.end());
    return res;
}

// Recursive fallback for larger blocks
// This effectively acts as a rudimentary Banded DP by forcing paths through midpoints
string solve_large_block(int i1, int i2, int len1, int len2) {
    // Threshold for switching to exact DP
    // 2500*2500 is roughly 6M operations, safe within recursion limit
    if ((long long)len1 * len2 <= 6000000LL) {
        return solve_small_dp(i1, i2, len1, len2);
    }
    
    // Divide and Conquer heuristic
    int mid1 = len1 / 2;
    int mid2 = len2 / 2;
    
    // Note: This geometric split assumes the optimal path goes roughly through the center.
    // Without anchors, this is a reasonable guess for approximate edit distance.
    return solve_large_block(i1, i2, mid1, mid2) + 
           solve_large_block(i1 + mid1, i2 + mid2, len1 - mid1, len2 - mid2);
}

// Process a segment defined by (i1, len1) in S1 and (i2, len2) in S2
void solve_segment(int i1, int i2, int len1, int len2) {
    if (len1 == 0 && len2 == 0) return;
    
    // Trim Matching Prefix
    int match_pre = 0;
    while(match_pre < len1 && match_pre < len2 && S1[i1+match_pre] == S2[i2+match_pre]) {
        match_pre++;
    }
    if(match_pre > 0) {
        for(int k=0; k<match_pre; ++k) transcript += 'M';
        i1 += match_pre; i2 += match_pre;
        len1 -= match_pre; len2 -= match_pre;
    }
    if (len1 == 0 && len2 == 0) return;

    // Trim Matching Suffix
    int match_suf = 0;
    while(match_suf < len1 && match_suf < len2 && S1[i1+len1-1-match_suf] == S2[i2+len2-1-match_suf]) {
        match_suf++;
    }
    len1 -= match_suf; len2 -= match_suf;

    // Solve inner gap
    if (len1 > 0 || len2 > 0) {
        transcript += solve_large_block(i1, i2, len1, len2);
    }

    for(int k=0; k<match_suf; ++k) transcript += 'M';
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> S1 >> S2)) return 0;
    N = S1.length();
    M = S2.length();
    transcript.reserve(max(N, M) + N/10);

    // Corner cases
    if (N == 0) {
        for(int i=0; i<M; ++i) cout << 'I';
        cout << endl;
        return 0;
    }
    if (M == 0) {
        for(int i=0; i<N; ++i) cout << 'D';
        cout << endl;
        return 0;
    }

    // Parameters for Hashing
    const int K = 12; // K-mer size
    const int STRIDE = 32; // Index every 32nd position of S1
    const int MOD = 1000003;
    const long long BASE = 37;
    
    // Hash Table
    vector<vector<int>> htable(MOD);
    
    // 1. Build Index on S1
    // Compute polynomial rolling hash for substrings of S1
    for (int i = 0; i <= N - K; i += STRIDE) {
        long long h = 0;
        for (int j = 0; j < K; ++j) {
            h = (h * BASE + S1[i+j]) % MOD;
        }
        // Limit bucket size to prevent explosion on repetitive strings
        if (htable[h].size() < 15) {
            htable[h].push_back(i);
        }
    }

    // 2. Scan S2 and find Candidates
    vector<pair<int, int>> candidates; 
    candidates.reserve(100000);
    
    long long h = 0;
    long long power = 1;
    for(int i=0; i<K-1; ++i) power = (power * BASE) % MOD;

    if (M >= K) {
        // Initial hash window
        for (int j = 0; j < K; ++j) {
            h = (h * BASE + S2[j]) % MOD;
        }
        
        auto check_and_add = [&](int j_pos) {
             if (!htable[h].empty()) {
                for (int r1 : htable[h]) {
                    // Quick verification of first and last char to reduce false positives
                    if (S1[r1] == S2[j_pos] && S1[r1+K-1] == S2[j_pos+K-1]) {
                        candidates.push_back({r1, j_pos});
                    }
                }
            }
        };

        check_and_add(0);

        // Rolling hash
        for (int j = 1; j <= M - K; ++j) {
            long long rem = (S2[j-1] * power) % MOD;
            h = (h - rem);
            if (h < 0) h += MOD;
            h = (h * BASE + S2[j+K-1]) % MOD;
            
            check_and_add(j);
            
            // Safety break to prevent TLE on pathological inputs
            if (candidates.size() > 600000) break; 
        }
    }

    // 3. Filter Candidates using LIS on r2
    // We want a chain of matches (r1, r2) such that both r1 and r2 are increasing.
    // candidates are naturally sorted by r2 due to scan order? 
    // Wait, scan order is r2 (j), but inside bucket r1 is sorted.
    // However, we need to sort primarily by r1 to use LIS on r2.
    sort(candidates.begin(), candidates.end());
    
    if (candidates.empty()) {
        solve_segment(0, 0, N, M);
        cout << transcript << endl;
        return 0;
    }

    // LIS Algorithm
    vector<int> tails; 
    vector<int> tails_indices; 
    vector<int> parent(candidates.size(), -1); 

    for (int i = 0; i < candidates.size(); ++i) {
        int r2 = candidates[i].second;
        // Upper bound for non-decreasing? Strictly increasing is safer for anchors.
        auto it = lower_bound(tails.begin(), tails.end(), r2);
        int idx = distance(tails.begin(), it);
        
        if (it == tails.end()) {
            tails.push_back(r2);
            tails_indices.push_back(i);
        } else {
            *it = r2;
            tails_indices[idx] = i;
        }
        
        if (idx > 0) {
            parent[i] = tails_indices[idx - 1];
        }
    }

    // Reconstruct chain
    vector<int> chain_indices;
    if (!tails_indices.empty()) {
        int curr = tails_indices.back();
        while (curr != -1) {
            chain_indices.push_back(curr);
            curr = parent[curr];
        }
    }
    reverse(chain_indices.begin(), chain_indices.end());

    // 4. Process Segments
    int c1 = 0;
    int c2 = 0;
    
    for (int idx : chain_indices) {
        int s1 = candidates[idx].first;
        int s2 = candidates[idx].second;
        
        // Skip invalid ordering (should adhere to LIS, but check for safety)
        if (s1 < c1 || s2 < c2) continue;

        int gap1 = s1 - c1;
        int gap2 = s2 - c2;
        
        solve_segment(c1, c2, gap1, gap2);
        
        // After solving gap, we are at (s1, s2).
        // Since (s1, s2) is an anchor start, it is guaranteed to match.
        // We do NOT output M here manually. The next call to solve_segment
        // will see the match at the beginning and handle it via prefix trimming.
        c1 = s1;
        c2 = s2;
    }
    
    // Final segment
    solve_segment(c1, c2, N - c1, M - c2);

    cout << transcript << endl;

    return 0;
}