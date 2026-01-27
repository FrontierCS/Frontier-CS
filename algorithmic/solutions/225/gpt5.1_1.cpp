#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, q;
    if (!(cin >> n >> q)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        queries[i] = {l, r};
    }

    vector<pair<int,int>> ops;
    ops.reserve(2200000); // upper bound

    vector<int> ans(q);

    int cnt = n;

    for (int qi = 0; qi < q; ++qi) {
        int l = queries[qi].first;
        int r = queries[qi].second;

        // Collect (value, index) pairs in [l, r]
        vector<pair<int,int>> vals;
        vals.reserve(r - l + 1);
        for (int i = l; i <= r; ++i) {
            vals.emplace_back(a[i], i);
        }
        sort(vals.begin(), vals.end()); // sort by value

        if ((int)vals.size() == 1) {
            ans[qi] = vals[0].second;
            continue;
        }

        int cur = vals[0].second;
        for (int i = 1; i < (int)vals.size(); ++i) {
            int idx = vals[i].second;
            ++cnt;
            ops.emplace_back(cur, idx);
            cur = cnt;
        }
        ans[qi] = cur;
    }

    cout << cnt << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";

    return 0;
}