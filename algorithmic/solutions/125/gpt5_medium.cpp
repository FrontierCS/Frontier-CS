#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> v;
    long long x;
    while (cin >> x) v.push_back(x);
    if (v.empty()) return 0;

    auto pair_by_labels = [&](const vector<long long>& labels, int offset) {
        // labels size is 2N, positions are 1..2N
        unordered_map<long long, int> firstPos;
        firstPos.reserve(labels.size() * 2);
        firstPos.max_load_factor(0.7);
        int L = (int)labels.size();
        for (int i = 0; i < L; ++i) {
            long long k = labels[i];
            auto it = firstPos.find(k);
            if (it == firstPos.end()) {
                firstPos.emplace(k, i + 1);
            } else {
                cout << it->second << " " << i + 1 << "\n";
                firstPos.erase(it);
            }
        }
    };

    // Case 1: v[0] is N and we have exactly 2N labels following
    if (v.size() >= 1) {
        long long N = v[0];
        if (N >= 0 && v.size() >= 1 + 2 * N) {
            vector<long long> labels;
            labels.reserve(2 * N);
            for (long long i = 0; i < 2 * N; ++i) labels.push_back(v[1 + i]);
            pair_by_labels(labels, 1);
            return 0;
        }
    }

    // Case 2: Maybe the entire input is 2N labels (no N given).
    {
        int L = (int)v.size();
        if (L % 2 == 0) {
            // Check if labels form pairs (each appears exactly twice)
            unordered_map<long long, int> cnt;
            cnt.reserve(L * 2);
            cnt.max_load_factor(0.7);
            bool ok = true;
            for (auto &val : v) cnt[val]++;
            for (auto &p : cnt) {
                if (p.second != 2) { ok = false; break; }
            }
            if (ok) {
                pair_by_labels(v, 0);
                return 0;
            }
        }
    }

    // Fallback: Only N is provided or unknown format. Output sequential pairs.
    // If first number is N, use it; otherwise infer N from size if even, else 0.
    long long N = v[0];
    if (N <= 0 || N > 1000000) {
        if (v.size() % 2 == 0) N = v.size() / 2;
        else N = 0;
    }
    for (long long i = 1; i <= N; ++i) {
        cout << 2 * i - 1 << " " << 2 * i << "\n";
    }
    return 0;
}