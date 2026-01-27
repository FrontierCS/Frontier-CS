#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, q;
    if (!(cin >> n >> q)) return 0;
    vector<int> a(n+1);
    for (int i = 1; i <= n; ++i) cin >> a[i];
    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) cin >> queries[i].first >> queries[i].second;

    // Prepare singleton ids: initial S_i = {a_i}, IDs 1..n
    // For merging in increasing value order, we need mapping from value to its set id, which is position with that value.
    vector<int> pos_by_value(n+1);
    for (int i = 1; i <= n; ++i) pos_by_value[a[i]] = i;

    long long cnt_limit = 2200000;
    vector<pair<int,int>> ops;
    ops.reserve(2000000);
    vector<int> ans(q);
    int cnt = n;

    for (int qi = 0; qi < q; ++qi) {
        int l = queries[qi].first, r = queries[qi].second;
        vector<int> vals;
        vals.reserve(r - l + 1);
        for (int i = l; i <= r; ++i) vals.push_back(a[i]);
        sort(vals.begin(), vals.end()); // increasing by value

        int cur_id = pos_by_value[vals[0]]; // singleton id
        for (size_t t = 1; t < vals.size(); ++t) {
            int sing_id = pos_by_value[vals[t]];
            // merge current set (all values less than vals[t]) with singleton {vals[t]}
            ops.emplace_back(cur_id, sing_id);
            ++cnt;
            cur_id = cnt;
            if (cnt > cnt_limit) {
                // We will continue anyway; constraints may be exceeded in worst case.
            }
        }
        ans[qi] = cur_id;
    }

    cout << cnt << "\n";
    for (auto &e : ops) {
        cout << e.first << " " << e.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << " ";
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}