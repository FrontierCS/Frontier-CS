#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    while (cin >> N) {
        vector<long long> vals;
        vals.reserve(2 * N);
        bool ok = true;
        for (int i = 0; i < 2 * N; ++i) {
            long long v;
            if (!(cin >> v)) {
                ok = false;
                break;
            }
            vals.push_back(v);
        }
        if (!ok) {
            // Fallback: pair consecutively if input incomplete
            for (int i = 1; i <= 2 * N; i += 2) {
                cout << i << " " << i + 1 << "\n";
            }
            break;
        } else {
            unordered_map<long long, int> first;
            first.reserve(2 * N * 2);
            vector<pair<int,int>> ans;
            ans.reserve(N);
            for (int i = 0; i < 2 * N; ++i) {
                long long v = vals[i];
                auto it = first.find(v);
                if (it == first.end()) {
                    first.emplace(v, i + 1);
                } else {
                    ans.emplace_back(it->second, i + 1);
                    first.erase(it);
                }
            }
            for (auto &p : ans) {
                cout << p.first << " " << p.second << "\n";
            }
        }
    }
    return 0;
}