#include <bits/stdc++.h>
using namespace std;

int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    cin >> n;
    
    vector<int> ans(n + 1, -1);
    
    // Step 1: find candidate for 0 by comparing ORs with index 1
    int min_val = INT_MAX;
    vector<int> candidates;
    vector<int> or1(n + 1);
    for (int i = 2; i <= n; ++i) {
        or1[i] = query(1, i);
        if (or1[i] < min_val) {
            min_val = or1[i];
            candidates.clear();
            candidates.push_back(i);
        } else if (or1[i] == min_val) {
            candidates.push_back(i);
        }
    }
    // also consider index 1 itself
    // we don't know OR(1,1), but we can check if 1 could be 0 later.
    candidates.push_back(1);
    
    // Now try each candidate as zero
    int zero = -1;
    for (int cand : candidates) {
        // assume cand is zero
        vector<int> perm(n + 1, -1);
        perm[cand] = 0;
        bool ok = true;
        for (int i = 1; i <= n; ++i) {
            if (i == cand) continue;
            int val = query(cand, i);
            perm[i] = val;
        }
        // check permutation
        vector<bool> seen(n, false);
        for (int i = 1; i <= n; ++i) {
            if (perm[i] < 0 || perm[i] >= n) {
                ok = false;
                break;
            }
            if (seen[perm[i]]) {
                ok = false;
                break;
            }
            seen[perm[i]] = true;
        }
        if (ok) {
            zero = cand;
            ans = perm;
            break;
        }
        // if not ok, continue to next candidate
    }
    
    // Output answer
    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << ans[i] << " ";
    }
    cout << endl;
    
    return 0;
}