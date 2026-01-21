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

    vector<int> L(q), R(q);
    for (int i = 0; i < q; ++i) {
        cin >> L[i] >> R[i];
    }

    // min/max arrays (not strictly necessary for correctness in this construction)
    // but we keep them for potential debugging or extension.
    vector<int> mn(1);
    vector<int> mx(1);
    mn.resize(n + 1);
    mx.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        mn[i] = mx[i] = a[i];
    }

    int cnt = n;
    vector<pair<int,int>> ops;

    // Deduplicate by (l,r) segments
    unordered_map<long long,int> segId;
    segId.reserve(q * 2);
    segId.max_load_factor(0.7);

    vector<int> ans(q);

    auto getKey = [&](int l, int r) -> long long {
        return ( (long long)l << 32 ) | (unsigned long long)r;
    };

    for (int i = 0; i < q; ++i) {
        int l = L[i], r = R[i];
        long long key = getKey(l, r);
        auto it = segId.find(key);
        if (it != segId.end()) {
            ans[i] = it->second;
            continue;
        }

        vector<int> vals;
        vals.reserve(r - l + 1);
        for (int j = l; j <= r; ++j) vals.push_back(a[j]);
        sort(vals.begin(), vals.end());

        int id;
        if ((int)vals.size() == 1) {
            id = pos[vals[0]];
        } else {
            int cur = pos[vals[0]];
            for (int k = 1; k < (int)vals.size(); ++k) {
                int v = vals[k];
                int nid = pos[v];
                ops.emplace_back(cur, nid);
                ++cnt;
                mn.push_back(min(mn[cur], mn[nid]));
                mx.push_back(max(mx[cur], mx[nid]));
                cur = cnt;
            }
            id = cnt;
        }

        segId[key] = id;
        ans[i] = id;
    }

    cout << cnt << '\n';
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';

    return 0;
}