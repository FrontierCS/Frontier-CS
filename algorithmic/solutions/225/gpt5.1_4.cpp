#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, q;
    if (!(cin >> n >> q)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    vector<int> pos(n + 1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    vector<int> L(q + 1), R(q + 1);
    for (int i = 1; i <= q; ++i) cin >> L[i] >> R[i];

    vector<pair<int,int>> ops;
    ops.reserve(2200000);

    vector<int> ans(q + 1);

    // Map identical intervals to same set id
    unordered_map<long long,int> mp;
    mp.reserve(q * 2);

    const int SHIFT = 12; // since n <= 2^12

    for (int i = 1; i <= q; ++i) {
        int l = L[i], r = R[i];
        long long key = ( (long long)l << SHIFT ) | r;
        auto it = mp.find(key);
        if (it != mp.end()) {
            ans[i] = it->second;
            continue;
        }

        int len = r - l + 1;
        if (len == 1) {
            int id = l; // S_l = {a_l}
            ans[i] = id;
            mp[key] = id;
            continue;
        }

        vector<int> vals;
        vals.reserve(len);
        for (int j = l; j <= r; ++j) vals.push_back(a[j]);
        sort(vals.begin(), vals.end(), greater<int>());

        int cur = pos[vals[0]]; // singleton set id

        for (int k = 1; k < len; ++k) {
            int leaf = pos[vals[k]];
            ops.emplace_back(leaf, cur);
            cur = n + (int)ops.size();
        }

        ans[i] = cur;
        mp[key] = cur;
    }

    int cntE = n + (int)ops.size();
    cout << cntE << '\n';
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    for (int i = 1; i <= q; ++i) {
        if (i > 1) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';

    return 0;
}