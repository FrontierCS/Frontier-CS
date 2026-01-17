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
        cin >> queries[i].first >> queries[i].second;
    }
    vector<vector<int>> built(n + 1, vector<int>(n + 1, 0));
    vector<pair<int, int>> all_merges;
    all_merges.reserve(2200000);
    int current_cnt = n;
    vector<int> k_for_query(q);
    for (int i = 0; i < q; ++i) {
        int l = queries[i].first;
        int r = queries[i].second;
        if (built[l][r] != 0) {
            k_for_query[i] = built[l][r];
            continue;
        }
        int curr = 0;
        bool first = true;
        for (int val = 1; val <= n; ++val) {
            int pid = pos[val];
            if (l <= pid && pid <= r) {
                if (first) {
                    curr = pid;
                    first = false;
                } else {
                    all_merges.emplace_back(curr, pid);
                    ++current_cnt;
                    curr = current_cnt;
                }
            }
        }
        built[l][r] = curr;
        k_for_query[i] = curr;
    }
    cout << current_cnt << '\n';
    for (auto& p : all_merges) {
        cout << p.first << ' ' << p.second << '\n';
    }
    for (int i = 0; i < q; ++i) {
        cout << k_for_query[i];
        if (i + 1 < q) cout << ' ';
        else cout << '\n';
    }
    return 0;
}