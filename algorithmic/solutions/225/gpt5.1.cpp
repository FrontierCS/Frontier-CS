#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, q;
    if (!(cin >> n >> q)) return 0;
    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        queries[i] = {l, r};
    }

    // Operations: each is (u, v)
    vector<pair<int,int>> ops;
    ops.reserve(2200000);

    int cnt = n;

    // Map each distinct (l,r) to resulting set ID
    struct PairHash {
        size_t operator()(const pair<int,int>& p) const noexcept {
            return (uint64_t)p.first * 1000003ull ^ (uint64_t)p.second;
        }
    };
    unordered_map<pair<int,int>, int, PairHash> segID;
    segID.reserve(q * 2);

    vector<int> ans(q);

    for (int i = 0; i < q; ++i) {
        int l = queries[i].first;
        int r = queries[i].second;
        pair<int,int> key = {l, r};
        auto it = segID.find(key);
        if (it != segID.end()) {
            ans[i] = it->second;
            continue;
        }
        vector<int> vals;
        vals.reserve(r - l + 1);
        for (int j = l; j <= r; ++j) vals.push_back(a[j]);
        sort(vals.begin(), vals.end());
        int curID = pos[vals[0]];
        for (int j = 1; j < (int)vals.size(); ++j) {
            int u = curID;
            int v = pos[vals[j]];
            ops.push_back({u, v});
            ++cnt;
            curID = cnt;
        }
        segID[key] = curID;
        ans[i] = curID;
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