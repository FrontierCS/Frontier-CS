#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    static unsigned char charMap[256];
    memset(charMap, 0, sizeof(charMap));
    charMap[(unsigned char)'?'] = 0;
    charMap[(unsigned char)'A'] = 1;
    charMap[(unsigned char)'C'] = 2;
    charMap[(unsigned char)'G'] = 3;
    charMap[(unsigned char)'T'] = 4;

    // Convert to numeric codes: code[i][j] for pattern i, position j
    vector<vector<unsigned char>> code(m, vector<unsigned char>(n));
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < n; ++j) {
            code[i][j] = charMap[(unsigned char)s[i][j]];
        }
    }

    int TOT = 1 << m;
    vector<unsigned char> state(TOT);
    vector<unsigned char> conflict(TOT, 0);
    vector<int> fixedCount(TOT, 0);

    // Process each position independently
    for (int j = 0; j < n; ++j) {
        state[0] = 0; // empty subset: all '?' at this position
        for (int mask = 1; mask < TOT; ++mask) {
            int p = __builtin_ctz(mask);         // index of least significant set bit
            int prev = mask & (mask - 1);       // mask without p
            unsigned char prevState = state[prev];
            unsigned char cp = code[p][j];      // char code at pattern p, position j

            unsigned char newState;
            if (prevState == 5) {
                newState = 5;                   // already conflict
            } else if (cp == 0) {
                newState = prevState;           // '?' adds nothing
            } else if (prevState == 0 || prevState == cp) {
                newState = cp;                  // first fixed letter or same letter
            } else {
                newState = 5;                   // conflict between different letters
            }

            state[mask] = newState;
            if (newState == 5) {
                conflict[mask] = 1;
            } else if (newState != 0) {
                fixedCount[mask]++;             // this position is fixed for this subset
            }
        }
    }

    // Precompute powers of 1/4
    vector<long double> pow4(n + 1);
    pow4[0] = 1.0L;
    for (int k = 1; k <= n; ++k) pow4[k] = pow4[k - 1] * 0.25L;

    long double ans = 0.0L;
    for (int mask = 1; mask < TOT; ++mask) {
        if (conflict[mask]) continue;
        int k = fixedCount[mask];
        long double p = pow4[k];                // 4^{-k}
        int bits = __builtin_popcount(mask);
        if (bits & 1) ans += p;                 // odd size: +
        else ans -= p;                          // even size: -
    }

    if (ans < 0) ans = 0;
    if (ans > 1) ans = 1;

    cout.setf(ios::fixed);
    cout << setprecision(10) << (double)ans << '\n';
    return 0;
}