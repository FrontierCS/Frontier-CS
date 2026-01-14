#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, q;
    cin >> n >> q;
    
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
    }
    
    vector<int> pos(n + 1);
    for (int i = 1; i <= n; ++i) {
        pos[a[i]] = i;
    }
    
    vector<pair<int, int>> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        queries[i] = {l, r};
    }
    
    vector<pair<int, int>> merges;
    vector<int> k(q);
    int current_cnt = n;
    
    for (int qi = 0; qi < q; ++qi) {
        int l = queries[qi].first;
        int r = queries[qi].second;
        
        vector<int> positions;
        positions.reserve(r - l + 1);
        for (int j = 1; j <= n; ++j) {
            if (l <= pos[j] && pos[j] <= r) {
                positions.push_back(pos[j]);
            }
        }
        
        int m = positions.size();
        if (m == 0) {
            k[qi] = 1; // arbitrary, but shouldn't happen
            continue;
        }
        
        int curr = positions[0];
        for (int jj = 1; jj < m; ++jj) {
            int next_id = positions[jj];
            merges.emplace_back(curr, next_id);
            ++current_cnt;
            curr = current_cnt;
        }
        k[qi] = curr;
    }
    
    cout << current_cnt << '\n';
    for (auto [u, v] : merges) {
        cout << u << ' ' << v << '\n';
    }
    for (int i = 0; i < q; ++i) {
        cout << k[i];
        if (i + 1 < q) cout << ' ';
        else cout << '\n';
    }
    
    return 0;
}