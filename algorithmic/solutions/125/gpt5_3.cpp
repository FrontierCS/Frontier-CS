#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;

    vector<long long> types;
    types.reserve(2 * N + 1);
    types.push_back(0);
    for (int i = 1; i <= 2 * N; ++i) {
        long long v;
        if (!(cin >> v)) {
            // Fallback if types are not provided: pair adjacent indices
            for (int j = 1; j <= N; ++j) {
                cout << 2 * j - 1 << " " << 2 * j;
                if (j < N) cout << '\n';
            }
            return 0;
        }
        types.push_back(v);
    }

    unordered_map<long long, int> first_pos;
    first_pos.reserve(2 * N);
    first_pos.max_load_factor(0.7);

    vector<pair<int, int>> ans;
    ans.reserve(N);

    for (int i = 1; i <= 2 * N; ++i) {
        long long v = types[i];
        auto it = first_pos.find(v);
        if (it == first_pos.end()) {
            first_pos.emplace(v, i);
        } else {
            ans.emplace_back(it->second, i);
            first_pos.erase(it);
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << ans[i].first << " " << ans[i].second;
        if (i + 1 < N) cout << '\n';
    }
    return 0;
}