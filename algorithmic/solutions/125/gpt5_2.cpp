#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long N;
    if (!(cin >> N)) return 0;
    long long total = 2 * N;
    
    vector<long long> labels;
    labels.reserve(total);
    long long x;
    while (cin >> x) labels.push_back(x);
    
    vector<pair<int,int>> res;
    res.reserve(N);
    
    if ((long long)labels.size() >= total) {
        unordered_map<long long, int> first;
        first.reserve((size_t)total * 2);
        first.max_load_factor(0.7f);
        
        for (int i = 1; i <= total; ++i) {
            long long v = labels[i - 1];
            auto it = first.find(v);
            if (it == first.end()) {
                first.emplace(v, i);
            } else {
                res.emplace_back(it->second, i);
                first.erase(it);
            }
        }
        
        if (!first.empty() && (int)res.size() < N) {
            vector<int> unmatched;
            unmatched.reserve(first.size());
            for (auto &kv : first) unmatched.push_back(kv.second);
            sort(unmatched.begin(), unmatched.end());
            for (size_t i = 0; i + 1 < unmatched.size() && (int)res.size() < N; i += 2)
                res.emplace_back(unmatched[i], unmatched[i + 1]);
        }
        
        if ((int)res.size() < N) {
            vector<char> used(total + 1, false);
            for (auto &p : res) used[p.first] = used[p.second] = true;
            vector<int> remaining;
            remaining.reserve((size_t)total - 2 * res.size());
            for (int i = 1; i <= total; ++i) if (!used[i]) remaining.push_back(i);
            for (size_t i = 0; i + 1 < remaining.size() && (int)res.size() < N; i += 2)
                res.emplace_back(remaining[i], remaining[i + 1]);
        }
    } else {
        for (int i = 1; i <= total; i += 2) res.emplace_back(i, i + 1);
    }
    
    // Ensure exactly N pairs are printed (truncate if somehow more)
    for (int i = 0; i < (int)min<long long>(res.size(), N); ++i) {
        cout << res[i].first << " " << res[i].second << "\n";
    }
    // If still less than N (shouldn't happen), fill sequentially
    if ((int)res.size() < N) {
        vector<char> used(total + 1, false);
        for (auto &p : res) used[p.first] = used[p.second] = true;
        vector<int> remaining;
        for (int i = 1; i <= total; ++i) if (!used[i]) remaining.push_back(i);
        int idx = 0;
        for (int i = res.size(); i < N && idx + 1 < (int)remaining.size(); ++i) {
            cout << remaining[idx] << " " << remaining[idx + 1] << "\n";
            idx += 2;
        }
    }
    return 0;
}