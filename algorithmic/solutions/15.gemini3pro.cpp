#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to apply operation
void apply_op(vector<int>& p, int x, int y) {
    int n = p.size();
    vector<int> new_p;
    new_p.reserve(n);
    // Suffix C
    for (int i = n - y; i < n; ++i) new_p.push_back(p[i]);
    // Middle B
    for (int i = x; i < n - y; ++i) new_p.push_back(p[i]);
    // Prefix A
    for (int i = 0; i < x; ++i) new_p.push_back(p[i]);
    p = new_p;
}

// Compute length of sorted suffix 1, 2, ..., k
// This means P ends with ..., 1, 2, ..., k
// P[n-k] == 1, ..., P[n-1] == k
int get_sorted_suffix_len(const vector<int>& p) {
    int n = p.size();
    for (int len = 0; len <= n; ++len) {
        if (len == n) return n;
        // Check if suffix of length len+1 is NOT 1..len+1
        // We check from back: P[n-1] should be len+1? No.
        // We want 1..k at the end.
        // So P[n-1] == k, P[n-2] == k-1 ...
        // We test if we can extend current length 'len' to 'len+1'.
        // Expected value at n-1-len is 1. (Since suffix is 1..len+1, 1 is at start of suffix)
        // Wait. Suffix 1..k means [1, 2, 3].
        // 1 is at n-3.
        // So if we have matched 'len' elements (1..len), next one to match is len+1?
        // No. If we have suffix length 'len', it means P[n-len]...P[n-1] are 1...len.
        // We want to check if P[n-1-len] is NOT len+1? No, we build 1, 2...
        // Actually, the standard sorting strategy for this problem (as derived) is to accumulate 1, 2, ...
        // But let's check what we are accumulating.
        // If we want [1, 2, 3, 4] at the end eventually, we build [1], then [1, 2]... NO.
        // [1, 2] is not a suffix of [1, 2, 3, 4] ending with 4.
        // We want suffix of the final array. Final array is 1...n.
        // So we want ..., n-1, n.
        // My previous logic was building 1..k. That is a prefix.
        // If I build a prefix 1..k at the END of the array, I can eventually rotate it to front?
        // Yes.
        // So let's stick to: find longest suffix that is 1, 2, ..., k.
        // e.g. [..., 1, 2, 3]. k=3.
        if (p[n - 1 - len] != len + 1) return len;
    }
    return n;
}

struct Move {
    int x, y;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    vector<Move> ops;
    
    // Safety break to respect operation limit
    int max_ops = 4 * n;
    
    while (ops.size() < max_ops) {
        int k = get_sorted_suffix_len(p);
        if (k == n) break;
        
        int target = k + 1;
        int pos = -1;
        for(int i=0; i<n; ++i) {
            if (p[i] == target) {
                pos = i;
                break;
            }
        }
        
        // Candidates for x and z (start of C, i.e., n-y)
        vector<int> splits;
        splits.push_back(0); 
        splits.push_back(pos); 
        splits.push_back(pos + 1);
        splits.push_back(n - k); // Start of S
        
        // Add neighbors
        if (pos > 0) splits.push_back(pos - 1);
        if (pos + 2 <= n) splits.push_back(pos + 2);
        if (n - k - 1 >= 0) splits.push_back(n - k - 1);
        if (n - k + 1 <= n) splits.push_back(n - k + 1);
        
        sort(splits.begin(), splits.end());
        splits.erase(unique(splits.begin(), splits.end()), splits.end());
        
        int best_len = -1;
        int best_dist = 1e9;
        Move best_move = {-1, -1};
        
        for (int x : splits) {
            for (int z : splits) {
                int y = n - z;
                if (x > 0 && y > 0 && x + y < n) {
                    // Simulate op
                    // Avoid full vector copy for performance if possible, but N=1000 is small enough
                    vector<int> temp; 
                    temp.reserve(n);
                    for(int i=z; i<n; ++i) temp.push_back(p[i]);
                    for(int i=x; i<z; ++i) temp.push_back(p[i]);
                    for(int i=0; i<x; ++i) temp.push_back(p[i]);
                    
                    int new_k = get_sorted_suffix_len(temp);
                    if (new_k > k) {
                        best_len = new_k;
                        best_move = {x, y};
                        goto apply;
                    }
                    
                    // Secondary criteria: keep S intact and minimize dist(target, S)
                    // Check if 1..k is present as a block
                    int idx1 = -1;
                    for(int i=0; i<n; ++i) if(temp[i] == 1) { idx1 = i; break; }
                    
                    bool intact = true;
                    if (idx1 == -1) intact = false;
                    else {
                        for(int j=0; j<k; ++j) {
                            if (temp[(idx1 + j) % n] != j + 1) { // Check cyclically
                                intact = false; break; 
                            }
                        }
                    }
                    
                    if (intact) {
                        int idx_t = -1;
                        for(int i=0; i<n; ++i) if(temp[i] == target) { idx_t = i; break; }
                        
                        // We want target to be at (idx1 - 1) cyclically
                        int dist;
                        int wanted_pos = (idx1 - 1 + n) % n;
                        if (wanted_pos >= idx_t) dist = wanted_pos - idx_t;
                        else dist = wanted_pos + n - idx_t;
                        
                        if (dist < best_dist) {
                            best_dist = dist;
                            best_move = {x, y};
                        }
                    }
                }
            }
        }
        
        apply:
        if (best_move.x != -1) {
            apply_op(p, best_move.x, best_move.y);
            ops.push_back(best_move);
        } else {
            // Random move to break stuck state
            apply_op(p, 1, 1);
            ops.push_back({1, 1});
        }
    }
    
    // Final check: if 1..N is rotated (e.g. N, 1, 2...N-1), fix it
    // get_sorted_suffix_len returns N only if 1..N matches exactly.
    // If we exited because k=N, we are done.
    // However, if we built 1..N at end, we are done.
    
    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.x << " " << op.y << endl;
    }

    return 0;
}