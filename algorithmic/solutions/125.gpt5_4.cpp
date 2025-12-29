#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    int total = 2 * N;
    vector<long long> types;
    types.reserve(total);
    long long x;
    while ((int)types.size() < total && (cin >> x)) types.push_back(x);

    if ((int)types.size() == total) {
        unordered_map<long long, int> first;
        first.reserve(total * 2);
        vector<pair<int,int>> res;
        res.reserve(N);
        for (int i = 1; i <= total; ++i) {
            long long t = types[i - 1];
            auto it = first.find(t);
            if (it == first.end()) {
                first[t] = i;
            } else {
                res.emplace_back(it->second, i);
                first.erase(it);
            }
        }
        if ((int)res.size() < N) {
            vector<int> rem;
            rem.reserve(first.size());
            for (auto &p : first) rem.push_back(p.second);
            for (size_t i = 0; i + 1 < rem.size() && (int)res.size() < N; i += 2) {
                res.emplace_back(rem[i], rem[i + 1]);
            }
            vector<int> all(total);
            iota(all.begin(), all.end(), 1);
            vector<char> used(total + 1, false);
            for (auto &pr : res) used[pr.first] = used[pr.second] = true;
            vector<int> others;
            for (int i = 1; i <= total; ++i) if (!used[i]) others.push_back(i);
            for (size_t i = 0; i + 1 < others.size() && (int)res.size() < N; i += 2)
                res.emplace_back(others[i], others[i + 1]);
        }
        for (auto &p : res) cout << p.first << " " << p.second << "\n";
    } else {
        for (int i = 1; i <= total; i += 2) {
            cout << i << " " << i + 1 << "\n";
        }
    }
    return 0;
}