#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> a(2 * N + 1);
    for (int i = 1; i <= 2 * N; ++i) {
        if (!(cin >> a[i])) return 0;
    }
    
    unordered_map<long long, int> firstPos;
    firstPos.reserve(2 * N);
    vector<pair<int, int>> ans;
    ans.reserve(N);
    
    for (int i = 1; i <= 2 * N; ++i) {
        auto it = firstPos.find(a[i]);
        if (it == firstPos.end()) {
            firstPos.emplace(a[i], i);
        } else {
            ans.emplace_back(it->second, i);
            firstPos.erase(it);
        }
    }
    
    if ((int)ans.size() != N) {
        unordered_map<long long, vector<int>> pos;
        pos.reserve(2 * N);
        for (int i = 1; i <= 2 * N; ++i) pos[a[i]].push_back(i);
        ans.clear();
        for (auto &kv : pos) {
            auto &v = kv.second;
            for (size_t j = 0; j + 1 < v.size(); j += 2) {
                ans.emplace_back(v[j], v[j + 1]);
            }
        }
    }
    
    for (int i = 0; i < N && i < (int)ans.size(); ++i) {
        cout << ans[i].first << " " << ans[i].second << "\n";
    }
    return 0;
}