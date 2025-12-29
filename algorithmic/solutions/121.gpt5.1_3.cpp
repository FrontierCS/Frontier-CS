#include <bits/stdc++.h>
using namespace std;

int cid[256];

bool generalizes(const string &a, const string &b) {
    int n = (int)a.size();
    for (int i = 0; i < n; ++i) {
        if (a[i] != '?' && a[i] != b[i]) return false;
    }
    return true;
}

long double solve_dp(int n, int m, const vector<string> &pat) {
    using ld = long double;
    unsigned long long B = 1ULL << m;
    vector<ld> dp(B), nx(B);

    unsigned long long allMask = (m == 64 ? ~0ULL : ((1ULL << m) - 1ULL));
    dp[allMask] = 1.0L;

    vector<array<unsigned long long, 4>> masks(n);
    for (int j = 0; j < n; ++j)
        for (int l = 0; l < 4; ++l)
            masks[j][l] = 0ULL;

    for (int i = 0; i < m; ++i) {
        const string &s = pat[i];
        unsigned long long bit = 1ULL << i;
        for (int j = 0; j < n; ++j) {
            char c = s[j];
            if (c == '?') {
                for (int l = 0; l < 4; ++l) masks[j][l] |= bit;
            } else {
                int l = cid[(unsigned char)c];
                masks[j][l] |= bit;
            }
        }
    }

    for (int j = 0; j < n; ++j) {
        fill(nx.begin(), nx.end(), 0.0L);
        auto &M = masks[j];
        for (unsigned long long S = 0; S < B; ++S) {
            ld cur = dp[S];
            if (cur == 0.0L) continue;
            ld val = cur * 0.25L;
            unsigned long long s_mask = S;
            unsigned long long to0 = s_mask & M[0];
            unsigned long long to1 = s_mask & M[1];
            unsigned long long to2 = s_mask & M[2];
            unsigned long long to3 = s_mask & M[3];
            nx[to0] += val;
            nx[to1] += val;
            nx[to2] += val;
            nx[to3] += val;
        }
        dp.swap(nx);
    }

    long double ans = 1.0L - dp[0];
    if (ans < 0) ans = 0;
    if (ans > 1) ans = 1;
    return ans;
}

long double solve_bitset(int n, int m, const vector<string> &pat) {
    using ull = unsigned long long;
    using ld = long double;

    int K = (n + 63) / 64;
    ull B = 1ULL << m;
    size_t BK = (size_t)B * (size_t)K;

    vector<ld> pow4(n + 1);
    pow4[0] = 1.0L;
    for (int i = 1; i <= n; ++i) pow4[i] = pow4[i - 1] * 0.25L;

    vector<ull> base[4];
    for (int l = 0; l < 4; ++l) base[l].assign((size_t)m * K, 0ULL);

    for (int i = 0; i < m; ++i) {
        const string &s = pat[i];
        for (int j = 0; j < n; ++j) {
            char c = s[j];
            int l = cid[(unsigned char)c];
            if (l >= 0) {
                int word = j >> 6;
                size_t idx = (size_t)i * K + word;
                base[l][idx] |= (1ULL << (j & 63));
            }
        }
    }

    vector<ull> P[4];
    for (int l = 0; l < 4; ++l) P[l].assign(BK, 0ULL);

    ld ans = 0.0L;

    for (ull S = 1; S < B; ++S) {
        ull lb = __builtin_ctzll(S);
        ull prev = S & (S - 1);

        size_t offsetS = (size_t)S * K;
        size_t offsetPrev = (size_t)prev * K;
        size_t patOff = (size_t)lb * K;

        for (int l = 0; l < 4; ++l) {
            ull *dest = &P[l][offsetS];
            ull *srcPrev = &P[l][offsetPrev];
            ull *srcPat = &base[l][patOff];
            for (int w = 0; w < K; ++w)
                dest[w] = srcPrev[w] | srcPat[w];
        }

        bool conflict = false;
        int cnt = 0;

        for (int w = 0; w < K; ++w) {
            ull a = P[0][offsetS + w];
            ull b = P[1][offsetS + w];
            ull c = P[2][offsetS + w];
            ull d = P[3][offsetS + w];

            ull any = a | b | c | d;

            ull ab = a & b;
            ull ac = a & c;
            ull ad = a & d;
            ull bc = b & c;
            ull bd = b & d;
            ull cd = c & d;
            ull atLeastTwo = ab | ac | ad | bc | bd | cd;

            if (atLeastTwo) {
                conflict = true;
                break;
            }
            cnt += __builtin_popcountll(any);
        }
        if (conflict) continue;

        int bits = __builtin_popcountll(S);
        ld p = pow4[cnt];
        if (bits & 1) ans += p;
        else ans -= p;
    }

    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    memset(cid, -1, sizeof(cid));
    cid[(unsigned char)'A'] = 0;
    cid[(unsigned char)'C'] = 1;
    cid[(unsigned char)'G'] = 2;
    cid[(unsigned char)'T'] = 3;

    // Remove patterns that are subsumed by more general ones
    vector<bool> removed(m, false);
    for (int i = 0; i < m; ++i) {
        if (removed[i]) continue;
        for (int j = 0; j < m; ++j) {
            if (i == j || removed[j]) continue;
            if (generalizes(s[i], s[j])) {
                removed[j] = true;
            }
        }
    }

    vector<string> pat;
    pat.reserve(m);
    for (int i = 0; i < m; ++i)
        if (!removed[i]) pat.push_back(s[i]);
    m = (int)pat.size();

    if (m == 0) {
        cout.setf(ios::fixed);
        cout << setprecision(10) << 0.0 << '\n';
        return 0;
    }

    unsigned long long B = 1ULL << m;
    int K = (n + 63) / 64;
    long long Bll = (long long)B;

    long double dpOps = 4.0L * (long double)n * (long double)Bll;
    long long memBitset = 4LL * Bll * (long long)K * 8LL;
    const long long MEM_LIMIT = (long long)450 * 1024 * 1024;

    bool canBitset = (memBitset <= MEM_LIMIT);
    bool useDP = (dpOps <= 3e8L) || !canBitset;

    long double ans;
    if (useDP) ans = solve_dp(n, m, pat);
    else ans = solve_bitset(n, m, pat);

    cout.setf(ios::fixed);
    cout << setprecision(10) << (long double)ans << '\n';
    return 0;
}