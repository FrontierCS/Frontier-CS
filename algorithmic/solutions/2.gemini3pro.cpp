#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Helper to interact with the judge
int query(const vector<int>& q) {
    cout << "0";
    for (int x : q) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Helper to output the answer
void guess(const vector<int>& p) {
    cout << "1";
    for (int x : p) cout << " " << x;
    cout << endl;
    exit(0);
}

int main() {
    // Optimize I/O operations, though for interactive problems flushing is key
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        guess({1});
        return 0;
    }

    vector<int> p(n + 1, 0);
    
    // We want to find one position with a known value to use as a pivot.
    // We look for pos[1] or pos[2].
    // Query strategy: q[i] = 1, others = 2.
    // If res == 2: p[i] == 1 (since pos[1]=i and pos[2]!=i).
    // If res == 0: p[i] == 2 (since pos[1]!=i and pos[2]=i).
    // If res == 1: neither (pos[1]!=i and pos[2]!=i).
    // We scan indices in random order to avoid worst-case inputs.
    vector<int> probe_order(n);
    iota(probe_order.begin(), probe_order.end(), 1);
    
    mt19937 rng(1337);
    shuffle(probe_order.begin(), probe_order.end(), rng);

    int base_idx = -1;
    int base_val = -1;

    // This loop takes at most N queries (guaranteed to find 0 or 2)
    for (int idx : probe_order) {
        vector<int> q(n);
        for (int i = 0; i < n; ++i) {
            if (i + 1 == idx) q[i] = 1;
            else q[i] = 2;
        }
        int res = query(q);
        if (res == 2) {
            base_idx = idx;
            base_val = 1;
            break;
        } else if (res == 0) {
            base_idx = idx;
            base_val = 2;
            break;
        }
    }

    // We record the found value
    p[base_idx] = base_val;
    
    // available indices for the remaining values
    vector<int> available;
    for (int i = 1; i <= n; ++i) {
        if (i != base_idx) available.push_back(i);
    }

    // values we still need to locate
    vector<int> to_find;
    for (int v = 1; v <= n; ++v) {
        if (v != base_val) to_find.push_back(v);
    }

    int found_count = 1; // currently we know 1 position

    // For each remaining value, binary search its position among available indices
    // This takes Sum(log2(k)) queries, which is ~ N log N but specifically log(N!) < 8600 for N=1000
    for (int val : to_find) {
        int l = 0;
        int r = available.size() - 1;
        
        while (l < r) {
            int mid = l + (r - l) / 2;
            
            // Construct query
            // Base: fill with base_val (known to be non-matching for unknown positions because base_val is unique at base_idx)
            // Known positions: fill with their correct values (contributes found_count matches)
            // Range [l, mid]: fill with target val (contributes +1 if pos[val] is here)
            
            vector<int> q(n);
            for(int i=1; i<=n; ++i) {
                if(p[i] != 0) {
                    q[i-1] = p[i];
                } else {
                    q[i-1] = base_val;
                }
            }
            
            // Overwrite probe range with candidate value
            for (int k = l; k <= mid; ++k) {
                int idx = available[k];
                q[idx-1] = val;
            }

            int res = query(q);
            
            // If val is in the probed range, we get one extra match
            if (res == found_count + 1) {
                r = mid;
            } else {
                l = mid + 1;
            }
        }
        
        // available[l] is the position of val
        int pos = available[l];
        p[pos] = val;
        found_count++;
        
        // Remove pos from available. erase is O(K), total loop is O(N^2) which is fine for N=1000
        available.erase(available.begin() + l);
    }

    // Output result
    vector<int> ans;
    for (int i = 1; i <= n; ++i) ans.push_back(p[i]);
    guess(ans);

    return 0;
}