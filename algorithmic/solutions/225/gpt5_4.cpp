#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, q;
    if (!(cin >> n >> q)) return 0;
    vector<int> a(n+1);
    for (int i = 1; i <= n; ++i) cin >> a[i];
    vector<pair<int,int>> ops;
    ops.reserve(2200000);
    vector<int> k(q);
    vector<int> pos(n+1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;
    long long cnt = n;
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        vector<int> vals;
        vals.reserve(r-l+1);
        for (int j = l; j <= r; ++j) vals.push_back(a[j]);
        sort(vals.begin(), vals.end());
        if (vals.empty()) {
            k[i] = 1; // shouldn't happen as l<=r, but default
        } else {
            long long cur = pos[vals[0]];
            for (size_t t = 1; t < vals.size(); ++t) {
                int v = pos[vals[t]];
                ops.emplace_back((int)cur, v);
                ++cnt;
                cur = cnt;
            }
            k[i] = (int)cur;
        }
    }
    cout << cnt << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << " ";
        cout << k[i];
    }
    cout << "\n";
    return 0;
}