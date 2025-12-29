#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long N;
    if (!(cin >> N)) return 0;
    long long M = 2 * N;

    vector<long long> arr;
    arr.reserve(M);
    long long x;
    for (long long i = 0; i < M && (cin >> x); ++i) arr.push_back(x);

    if ((long long)arr.size() == M) {
        // Try to detect partner mapping
        bool is_partner_map = true;
        vector<int> cnt;
        if (M <= (long long)2e6) cnt.assign(M + 1, 0); // safe size
        else cnt.assign((size_t)M + 1, 0);
        for (long long i = 0; i < M; ++i) {
            if (arr[i] < 1 || arr[i] > M) {
                is_partner_map = false;
                break;
            }
            cnt[(size_t)arr[i]]++;
        }
        if (is_partner_map) {
            for (long long v = 1; v <= M; ++v) {
                if (cnt[(size_t)v] != 1) { is_partner_map = false; break; }
            }
        }
        if (is_partner_map) {
            vector<int> partner(M + 1);
            for (long long i = 0; i < M; ++i) partner[(size_t)(i + 1)] = (int)arr[i];
            for (long long i = 1; i <= M; ++i) {
                if (partner[(size_t)partner[(size_t)i]] != i || partner[(size_t)i] == i) {
                    is_partner_map = false; break;
                }
            }
            if (is_partner_map) {
                vector<char> used(M + 1, false);
                for (long long i = 1; i <= M; ++i) {
                    int j = partner[(size_t)i];
                    if (!used[(size_t)i] && !used[(size_t)j]) {
                        cout << i << " " << j << "\n";
                        used[(size_t)i] = used[(size_t)j] = true;
                    }
                }
                return 0;
            }
        }
        // Treat as types (each value appears exactly twice)
        unordered_map<long long, int> first;
        first.reserve((size_t)M * 2);
        first.max_load_factor(0.7f);
        vector<char> taken(M + 1, false);
        long long pair_count = 0;
        for (long long i = 0; i < M; ++i) {
            long long val = arr[(size_t)i];
            auto it = first.find(val);
            if (it == first.end()) {
                first.emplace(val, (int)(i + 1));
            } else {
                int j = it->second;
                cout << j << " " << (i + 1) << "\n";
                taken[(size_t)j] = true;
                taken[(size_t)(i + 1)] = true;
                first.erase(it);
                pair_count++;
            }
        }
        if (pair_count < N) {
            vector<int> rem;
            rem.reserve((size_t)(M - 2 * pair_count));
            for (long long i = 1; i <= M; ++i) if (!taken[(size_t)i]) rem.push_back((int)i);
            for (size_t i = 0; i + 1 < rem.size(); i += 2) {
                cout << rem[i] << " " << rem[i + 1] << "\n";
                pair_count++;
            }
        }
    } else {
        // Fallback: pair consecutive indices
        for (long long i = 1; i <= M; i += 2) {
            cout << i << " " << (i + 1) << "\n";
        }
    }

    return 0;
}