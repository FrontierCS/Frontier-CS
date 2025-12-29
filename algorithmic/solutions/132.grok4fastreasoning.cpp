#include <bits/stdc++.h>
using namespace std;

int main() {
    int R, H;
    cin >> R >> H;
    const int n = 1000;
    const int r = 40;
    mt19937_64 rng(42);
    vector<uint64_t> codes(n + 1, 0);
    bool good = false;
    while (!good) {
        set<uint64_t> sigs;
        bool ok = true;
        for (int i = 1; i <= n && ok; ++i) {
            codes[i] = rng() & ((1ULL << r) - 1);
            if (sigs.count(codes[i])) ok = false;
            else sigs.insert(codes[i]);
        }
        if (!ok) continue;
        for (int i = 1; i <= n && ok; ++i) {
            for (int j = i + 1; j <= n && ok; ++j) {
                uint64_t sor = codes[i] | codes[j];
                if (sigs.count(sor)) {
                    ok = false;
                    break;
                }
                sigs.insert(sor);
            }
        }
        if (ok) good = true;
    }
    vector<vector<int>> queries(r);
    for (int k = 0; k < r; ++k) {
        uint64_t mask = 1ULL << k;
        for (int j = 1; j <= n; ++j) {
            if (codes[j] & mask) {
                queries[k].push_back(j);
            }
        }
    }
    for (int k = 0; k < r; ++k) {
        cout << "? " << queries[k].size();
        for (int p : queries[k]) {
            cout << " " << p;
        }
        cout << endl;
        cout.flush();
    }
    cout << "@" << endl;
    cout.flush();
    int L;
    cin >> L;
    vector<int> responses(L);
    for (int i = 0; i < L; ++i) {
        cin >> responses[i];
    }
    uint64_t observed = 0;
    for (int k = 0; k < r; ++k) {
        if (responses[k]) observed |= (1ULL << k);
    }
    pair<int, int> ans = {-1, -1};
    int cnt = 0;
    for (int i = 1; i <= n; ++i) {
        for (int j = i; j <= n; ++j) {
            uint64_t sor = codes[i] | codes[j];
            if (sor == observed) {
                ++cnt;
                ans = {i, j};
            }
        }
    }
    cout << "! " << ans.first << " " << ans.second << endl;
    cout.flush();
    return 0;
}