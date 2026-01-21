#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, q;
    if (!(cin >> n >> q)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    // position of value -> index (set id)
    vector<int> posOfVal(n + 1);
    for (int i = 1; i <= n; ++i) {
        posOfVal[a[i]] = i;
    }

    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        queries[i] = {l, r};
    }

    int cnt = n;
    vector<pair<int,int>> ops;
    ops.reserve(2000000);

    vector<int> mark(n + 1, 0);
    int stamp = 0;

    vector<int> ans(q);

    for (int idx = 0; idx < q; ++idx) {
        int l = queries[idx].first;
        int r = queries[idx].second;
        int len = r - l + 1;

        if (len == 1) {
            ans[idx] = l; // S_l = {a_l}
            continue;
        }

        ++stamp;
        for (int i = l; i <= r; ++i) {
            mark[a[i]] = stamp;
        }

        vector<int> vals;
        vals.reserve(len);
        for (int v = 1; v <= n; ++v) {
            if (mark[v] == stamp) vals.push_back(v);
        }

        int cur = posOfVal[vals[0]];
        for (int i = 1; i < (int)vals.size(); ++i) {
            int nxt = posOfVal[vals[i]];
            ops.emplace_back(cur, nxt);
            ++cnt;
            cur = cnt;
        }
        ans[idx] = cur;
    }

    cout << cnt << '\n';
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';

    return 0;
}