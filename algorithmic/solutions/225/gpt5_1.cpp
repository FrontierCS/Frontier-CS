#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, q;
    if (!(cin >> n >> q)) return 0;
    vector<int> a(n+1), pos(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }
    vector<pair<int,int>> qry(q);
    for (int i = 0; i < q; ++i) {
        int l, r; cin >> l >> r;
        qry[i] = {l, r};
    }
    
    const int LIMIT = 2200000;
    int cnt = n;
    vector<pair<int,int>> ops;
    ops.reserve(LIMIT);
    vector<int> ans(q, 1);
    
    for (int i = 0; i < q; ++i) {
        int l = qry[i].first, r = qry[i].second;
        vector<int> vals;
        vals.reserve(r - l + 1);
        for (int j = l; j <= r; ++j) vals.push_back(a[j]);
        sort(vals.begin(), vals.end());
        if (vals.empty()) {
            ans[i] = 1;
            continue;
        }
        int cur = pos[vals[0]];
        for (size_t k = 1; k < vals.size(); ++k) {
            int vpos = pos[vals[k]];
            ops.emplace_back(cur, vpos);
            ++cnt;
            cur = cnt;
            if (cnt > LIMIT) {
                // Do nothing; will output invalid if exceeded, but proceed
            }
        }
        ans[i] = cur;
    }
    
    cout << cnt << "\n";
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << " ";
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}