#include <bits/stdc++.h>
using namespace std;

vector<int> build(long long k) {
    if (k == 2) {
        return {0};
    }
    if (k == 3) {
        return {1, 0};
    }
    if (k % 2 == 0) {
        // k even, k >= 4
        vector<int> v = build(k / 2);
        int L = (int)v.size();
        v.push_back(L); // direct sum with [0]
        return v;
    } else {
        // k odd, k >= 5
        long long q = (k - 1) / 2;
        vector<int> v = build(q);
        int L = (int)v.size();
        vector<int> res;
        res.reserve(L + 2);
        for (int x : v) res.push_back(x + 1); // shift by 1
        res.push_back(L + 1);                 // element from first [0]
        res.push_back(0);                     // element from second [0]
        return res;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    if (!(cin >> q)) return 0;
    while (q--) {
        long long k;
        cin >> k;
        vector<int> perm = build(k);
        int n = (int)perm.size();
        cout << n << "\n";
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }
    return 0;
}