#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    
    vector<int> nums;
    int x;
    while (cin >> x) nums.push_back(x);
    
    vector<int> perm;
    // Try to find a window of size n that is a valid permutation of [1..n]
    if ((int)nums.size() >= n) {
        for (int i = 0; i + n <= (int)nums.size(); ++i) {
            vector<int> used(n + 1, 0);
            bool ok = true;
            for (int j = i; j < i + n; ++j) {
                int v = nums[j];
                if (v < 1 || v > n || used[v]) { ok = false; break; }
                used[v] = 1;
            }
            if (ok) {
                perm.assign(nums.begin() + i, nums.begin() + i + n);
                break;
            }
        }
    }
    
    if (perm.empty()) {
        // Fallback: if exactly n numbers were given and look reasonable
        if ((int)nums.size() >= n) {
            perm.assign(nums.begin(), nums.begin() + n);
        } else {
            // As a last resort, assume identity permutation
            perm.resize(n);
            iota(perm.begin(), perm.end(), 1);
        }
    }
    
    vector<int> pos(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        if (perm[i] >= 1 && perm[i] <= n) pos[perm[i]] = i + 1;
    }
    
    int v1 = n / 2;
    int v2 = n / 2 + 1;
    int i1 = pos[v1], i2 = pos[v2];
    
    if (i1 == 0 || i2 == 0) {
        vector<pair<int,int>> arr;
        arr.reserve(n);
        for (int i = 0; i < n; ++i) arr.push_back({perm[i], i + 1});
        sort(arr.begin(), arr.end());
        i1 = arr[n/2 - 1].second;
        i2 = arr[n/2].second;
    }
    
    if (i1 > i2) swap(i1, i2);
    cout << "1 " << i1 << " " << i2 << "\n";
    return 0;
}