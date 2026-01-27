#include <bits/stdc++.h>
using namespace std;

struct Bits {
    uint64_t lo = 0, hi = 0;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) {
        return 0;
    }

    const int N = 1000;
    int T = R; // number of robots/tests we will use

    // Generate random codewords for 1..N with T bits
    vector<Bits> code(N + 1);
    std::mt19937_64 rng(1234567890123456789ULL);
    for (int j = 0; j < T; ++j) {
        for (int i = 1; i <= N; ++i) {
            bool bit = (rng() & 1ULL);
            if (bit) {
                if (j < 64) code[i].lo |= (1ULL << j);
                else code[i].hi |= (1ULL << (j - 64));
            }
        }
    }

    // Send queries: for each bit j, send positions where bit j is 1
    for (int j = 0; j < T; ++j) {
        vector<int> pos;
        pos.reserve(N);
        for (int i = 1; i <= N; ++i) {
            if (j < 64) {
                if (code[i].lo & (1ULL << j)) pos.push_back(i);
            } else {
                if (code[i].hi & (1ULL << (j - 64))) pos.push_back(i);
            }
        }
        cout << "? " << pos.size();
        for (int x : pos) cout << ' ' << x;
        cout << '\n';
        cout.flush();
    }

    // Get responses
    cout << "@\n";
    cout.flush();

    int L;
    if (!(cin >> L)) return 0;
    vector<int> res(L);
    for (int i = 0; i < L; ++i) cin >> res[i];

    Bits y;
    for (int j = 0; j < L; ++j) {
        if (res[j]) {
            if (j < 64) y.lo |= (1ULL << j);
            else y.hi |= (1ULL << (j - 64));
        }
    }

    // Decode by finding pair (i,j) such that code[i] | code[j] == y
    vector<pair<int,int>> matches;

    // First check if y equals a single codeword
    for (int i = 1; i <= N; ++i) {
        if (code[i].lo == y.lo && code[i].hi == y.hi) {
            matches.emplace_back(i, i);
            break; // exact match implies both at same position
        }
    }

    if (matches.empty()) {
        for (int i = 1; i <= N; ++i) {
            for (int j = i; j <= N; ++j) {
                uint64_t or_lo = code[i].lo | code[j].lo;
                uint64_t or_hi = code[i].hi | code[j].hi;
                if (or_lo == y.lo && or_hi == y.hi) {
                    matches.emplace_back(i, j);
                    // It's exceedingly likely to be unique; but continue to be safe
                }
            }
        }
    }

    int a = 1, b = 1;
    if (!matches.empty()) {
        a = matches[0].first;
        b = matches[0].second;
    }

    cout << "! " << a << ' ' << b << '\n';
    cout.flush();

    return 0;
}