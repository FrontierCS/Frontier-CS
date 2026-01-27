#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, q;
    if(!(cin >> n >> q)) return 0;
    vector<int> a(n+1);
    for (int i = 1; i <= n; ++i) cin >> a[i];
    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r; cin >> l >> r;
        queries[i] = {l, r};
    }
    
    int cnt = n;
    vector<pair<int,int>> ops;
    ops.reserve(2000000); // reserve to reduce reallocations (heuristic)
    vector<int> k(q);
    
    vector<pair<int,int>> elems; // (value, index)
    elems.reserve(n);
    
    for (int i = 0; i < q; ++i) {
        int l = queries[i].first, r = queries[i].second;
        elems.clear();
        for (int j = l; j <= r; ++j) elems.emplace_back(a[j], j);
        sort(elems.begin(), elems.end()); // sort by value ascending
        int cur = elems[0].second; // singleton set index
        for (size_t t = 1; t < elems.size(); ++t) {
            int nxt = elems[t].second;
            ops.emplace_back(cur, nxt);
            ++cnt;
            cur = cnt;
        }
        k[i] = cur;
    }
    
    cout << cnt << '\n';
    for (auto &op : ops) cout << op.first << ' ' << op.second << '\n';
    for (int i = 0; i < q; ++i) {
        if (i) cout << ' ';
        cout << k[i];
    }
    cout << '\n';
    return 0;
}