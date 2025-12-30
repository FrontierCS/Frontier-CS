#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    int M = 2 * N;
    vector<long long> a(M + 1);
    for (int i = 1; i <= M; ++i) {
        if (!(cin >> a[i])) return 0;
    }

    unordered_map<long long, vector<int>> pos;
    pos.reserve(M * 2);
    pos.max_load_factor(0.7f);

    for (int i = 1; i <= M; ++i) {
        pos[a[i]].push_back(i);
    }

    vector<pair<int,int>> ans;
    ans.reserve(N);

    for (auto &kv : pos) {
        auto &v = kv.second;
        for (size_t i = 0; i + 1 < v.size(); i += 2) {
            ans.push_back({v[i], v[i + 1]});
        }
    }

    // Optional: sort for deterministic order
    sort(ans.begin(), ans.end(), [](const pair<int,int>& x, const pair<int,int>& y) {
        int ax = min(x.first, x.second);
        int ay = min(y.first, y.second);
        return ax < ay;
    });

    for (auto &p : ans) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}