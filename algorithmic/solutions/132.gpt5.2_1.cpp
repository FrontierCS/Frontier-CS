#include <bits/stdc++.h>
using namespace std;

using u128 = unsigned __int128;

static inline u128 bit128(int i) { return (u128)1 << i; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int Q = 13;
    const int BL = 5;
    const int M = Q * BL; // 65 tests
    const int NPOS = 1000;

    struct Coeff { int a0, a1, a2; };
    vector<Coeff> coeffs(NPOS);

    // Choose 76 full groups of 13 (= 988) plus 12 extra = 1000.
    // Each group fixes (a1,a2) and enumerates all a0 in [0..12] for full coverage.
    // group g -> a1=g%13, a2=g/13.
    for (int idx = 0; idx < NPOS; idx++) {
        int g = idx / Q;
        int within = idx % Q;
        int a1, a2, a0;

        if (g < 76) {
            a0 = within;
            a1 = g % Q;
            a2 = g / Q;
        } else {
            // partial group g=76 (12 entries: a0=0..11)
            a0 = within;           // within in [0..11] because idx<1000 => idx-988 in [0..11]
            a1 = 76 % Q;           // 11
            a2 = 76 / Q;           // 5
        }
        coeffs[idx] = {a0, a1, a2};
    }

    vector<u128> colMask(NPOS, 0);
    vector<vector<int>> tests(M);

    auto eval = [&](const Coeff& c, int x) -> int {
        int v = (c.a0 + c.a1 * x + c.a2 * (x * x)) % Q;
        if (v < 0) v += Q;
        return v;
    };

    // Build masks and tests
    for (int idx = 0; idx < NPOS; idx++) {
        const auto &c = coeffs[idx];
        for (int b = 0; b < BL; b++) {
            int x = b; // evaluation points 0..4
            int y = eval(c, x);
            int row = b * Q + y;
            colMask[idx] |= bit128(row);
            tests[row].push_back(idx + 1); // positions are 1-based
        }
    }

    int sends = 0;
    int usedM = min(M, R);

    // Send all tests (non-adaptive, one hour)
    for (int row = 0; row < usedM; row++) {
        cout << "? " << tests[row].size();
        for (int p : tests[row]) cout << ' ' << p;
        cout << '\n';
        cout.flush();
        sends++;
    }

    // Wait and get results
    cout << "@\n";
    cout.flush();

    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; i++) cin >> ans[i];

    u128 resp = 0;
    for (int i = 0; i < L && i < 128; i++) {
        if (ans[i]) resp |= bit128(i);
    }

    vector<int> cand;
    cand.reserve(4);
    for (int i = 0; i < NPOS; i++) {
        if ( (colMask[i] & resp) == colMask[i] ) cand.push_back(i + 1);
    }

    auto finish = [&](int a, int b) {
        cout << "! " << a << ' ' << b << '\n';
        cout.flush();
        exit(0);
    };

    if (cand.size() == 1) finish(cand[0], cand[0]);
    if (cand.size() == 2) finish(cand[0], cand[1]);

    // Fallback: brute-force pair search (including i==j)
    for (int i = 0; i < NPOS; i++) {
        u128 mi = colMask[i];
        for (int j = i; j < NPOS; j++) {
            if ( (mi | colMask[j]) == resp ) finish(i + 1, j + 1);
        }
    }

    finish(1, 1);
    return 0;
}