#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    // Map characters to bitmasks
    uint8_t charMask[256];
    memset(charMask, 0, sizeof(charMask));
    charMask[(unsigned char)'A'] = 1;  // 0001
    charMask[(unsigned char)'C'] = 2;  // 0010
    charMask[(unsigned char)'G'] = 4;  // 0100
    charMask[(unsigned char)'T'] = 8;  // 1000
    charMask[(unsigned char)'?'] = 15; // 1111

    // Convert strings to masks
    vector<vector<uint8_t>> mask(m, vector<uint8_t>(n));
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < n; ++j) {
            mask[i][j] = charMask[(unsigned char)s[i][j]];
        }
    }

    // Remove dominated patterns (those whose allowed set is subset of another)
    vector<bool> removed(m, false);
    for (int i = 0; i < m; ++i) {
        if (removed[i]) continue;
        for (int j = 0; j < m; ++j) {
            if (i == j || removed[j]) continue;
            bool dom = true;
            for (int pos = 0; pos < n; ++pos) {
                if ( (mask[i][pos] | mask[j][pos]) != mask[i][pos] ) {
                    dom = false;
                    break;
                }
            }
            if (dom) removed[j] = true;
        }
    }

    // Keep only non-dominated patterns
    vector<vector<uint8_t>> newMask;
    newMask.reserve(m);
    for (int i = 0; i < m; ++i) {
        if (!removed[i]) newMask.push_back(std::move(mask[i]));
    }
    mask.swap(newMask);
    m = (int)mask.size();

    if (m == 0) {
        cout.setf(ios::fixed);
        cout << setprecision(15) << 0.0 << '\n';
        return 0;
    }

    // 2^m must be manageable
    if (m >= 26) {
        // Problem constraints are expected to avoid this; fall back to 0 to avoid bad_alloc.
        cout.setf(ios::fixed);
        cout << setprecision(15) << 0.0 << '\n';
        return 0;
    }

    int M = 1 << m;

    vector<double> prob(M, 1.0);
    vector<uint8_t> inter(M);
    vector<uint8_t> base(m);

    // Precompute popcount for 4-bit masks
    int cnt4[16];
    for (int v = 0; v < 16; ++v) cnt4[v] = __builtin_popcount(v);

    for (int j = 0; j < n; ++j) {
        for (int i = 0; i < m; ++i) {
            base[i] = mask[i][j];
        }
        inter[0] = 15; // all four letters allowed for empty set
        for (int S = 1; S < M; ++S) {
            int prev = S & (S - 1);
            int idx = __builtin_ctz(S);
            inter[S] = inter[prev] & base[idx];
        }
        for (int S = 1; S < M; ++S) {
            int c = cnt4[inter[S]];
            prob[S] *= (double)c * 0.25;
        }
    }

    double ans = 0.0;
    for (int S = 1; S < M; ++S) {
        int pc = __builtin_popcount(S);
        if (pc & 1) ans += prob[S];
        else ans -= prob[S];
    }

    cout.setf(ios::fixed);
    cout << setprecision(15) << ans << '\n';
    return 0;
}