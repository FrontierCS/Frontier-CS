#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long Nll;
    if (!(cin >> Nll)) return 0;
    long long N = Nll;
    
    vector<long long> rest;
    rest.reserve(2 * N);
    long long x;
    while (cin >> x) rest.push_back(x);
    
    vector<pair<int,int>> pairs;
    pairs.reserve(N);
    
    if ((long long)rest.size() >= 2 * N) {
        vector<long long> a(rest.begin(), rest.begin() + 2 * N);
        bool mappingOK = false;
        // Try partner mapping (a[i] is partner index)
        bool mappingCandidatesOk = true;
        for (long long i = 1; i <= 2 * N; i++) {
            long long val = a[i - 1];
            if (val < 1 || val > 2 * N) { mappingCandidatesOk = false; break; }
        }
        if (mappingCandidatesOk) {
            mappingOK = true;
            for (long long i = 1; i <= 2 * N; i++) {
                long long p = a[i - 1];
                if (p < 1 || p > 2 * N || a[p - 1] != i) { mappingOK = false; break; }
            }
            if (mappingOK) {
                vector<char> used(2 * N + 1, false);
                for (int i = 1; i <= (int)2 * N; i++) {
                    int p = (int)a[i - 1];
                    if (!used[i]) {
                        if (i == p) { mappingOK = false; break; }
                        pairs.emplace_back(i, p);
                        used[i] = used[p] = true;
                    }
                }
                if (!mappingOK || (int)pairs.size() != (int)N) {
                    pairs.clear();
                    mappingOK = false;
                }
            }
        }
        if (!mappingOK) {
            // Try generic label mapping: each label appears exactly twice
            unordered_map<long long, int> cnt;
            cnt.reserve(2 * N * 2);
            for (long long i = 0; i < 2 * N; i++) {
                cnt[a[i]]++;
            }
            bool all2 = ((long long)cnt.size() == N);
            if (all2) {
                for (auto &kv : cnt) {
                    if (kv.second != 2) { all2 = false; break; }
                }
            }
            if (all2) {
                unordered_map<long long, int> first;
                first.reserve(cnt.size() * 2);
                for (long long i = 0; i < 2 * N; i++) {
                    long long v = a[i];
                    auto it = first.find(v);
                    int idx = (int)(i + 1);
                    if (it == first.end()) {
                        first.emplace(v, idx);
                    } else {
                        int prev = it->second;
                        pairs.emplace_back(prev, idx);
                        first.erase(it);
                    }
                }
            } else {
                // Try types in range 1..N each appears twice
                bool inRange = true;
                vector<int> cnt2;
                cnt2.assign((size_t)(N + 1), 0);
                for (long long i = 0; i < 2 * N; i++) {
                    long long val = a[i];
                    if (val < 1 || val > N) { inRange = false; break; }
                    cnt2[(size_t)val]++;
                }
                if (inRange) {
                    bool ok = true;
                    for (long long t = 1; t <= N; t++) if (cnt2[t] != 2) { ok = false; break; }
                    if (ok) {
                        vector<int> first(N + 1, 0);
                        for (long long i = 0; i < 2 * N; i++) {
                            long long val = a[i];
                            int idx = (int)(i + 1);
                            if (first[val] == 0) { first[val] = idx; }
                            else { pairs.emplace_back(first[val], idx); first[val] = 0; }
                        }
                    }
                }
            }
        }
    }
    
    if ((int)pairs.size() != (int)N) {
        pairs.clear();
        for (int i = 1; i <= 2 * (int)N; i += 2) {
            pairs.emplace_back(i, i + 1);
        }
    }
    
    for (auto &p : pairs) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}