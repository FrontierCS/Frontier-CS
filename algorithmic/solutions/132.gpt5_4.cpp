#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int n = 1000;
    const int q = 5;     // alphabet size
    const int L = 15;    // length
    const int m = q * L; // number of queries/tests = 75
    const int minDist = 8; // pairwise Hamming distance > L/2 ensures 2-disjunctness

    // Generate q-ary codewords for items 1..1000 with pairwise distance >= minDist
    vector<array<uint8_t, L>> code(n + 1);
    std::mt19937_64 rng(123456789ULL);
    auto gen_word = [&]() {
        array<uint8_t, L> w{};
        for (int i = 0; i < L; ++i) w[i] = uint8_t(rng() % q);
        return w;
    };
    auto dist_ge = [&](const array<uint8_t, L>& a, const array<uint8_t, L>& b, int d) {
        int diff = 0;
        for (int i = 0; i < L; ++i) diff += (a[i] != b[i]);
        return diff >= d;
    };

    for (int idx = 1; idx <= n; ++idx) {
        while (true) {
            auto w = gen_word();
            bool ok = true;
            for (int j = 1; j < idx; ++j) {
                if (!dist_ge(w, code[j], minDist)) { ok = false; break; }
            }
            if (ok) { code[idx] = w; break; }
        }
    }

    // Send queries: for each (t, s) list all positions whose symbol at t equals s
    vector<vector<int>> tests(m);
    for (int t = 0; t < L; ++t) {
        for (int s = 0; s < q; ++s) {
            int j = t * q + s;
            tests[j].reserve(n / q + 5);
        }
    }
    for (int pos = 1; pos <= n; ++pos) {
        for (int t = 0; t < L; ++t) {
            int s = code[pos][t];
            int j = t * q + s;
            tests[j].push_back(pos);
        }
    }

    for (int j = 0; j < m; ++j) {
        cout << "? " << tests[j].size();
        for (int x : tests[j]) cout << " " << x;
        cout << "\n";
        cout.flush();
    }

    // Get results after one hour
    cout << "@\n";
    cout.flush();

    int Lret;
    if (!(cin >> Lret)) return 0; // in case of non-interactive environment
    vector<int> ans(Lret);
    for (int i = 0; i < Lret; ++i) cin >> ans[i];

    // Decode: items whose all designated tests are positive
    vector<int> cand;
    cand.reserve(2);
    for (int pos = 1; pos <= n; ++pos) {
        bool ok = true;
        for (int t = 0; t < L; ++t) {
            int s = code[pos][t];
            int j = t * q + s;
            if (j >= Lret || ans[j] == 0) { ok = false; break; }
        }
        if (ok) cand.push_back(pos);
    }

    int a = 1, b = 1;
    if (cand.size() == 1) {
        a = b = cand[0];
    } else if (cand.size() >= 2) {
        a = cand[0];
        b = cand[1];
    }

    cout << "! " << a << " " << b << "\n";
    cout.flush();

    return 0;
}