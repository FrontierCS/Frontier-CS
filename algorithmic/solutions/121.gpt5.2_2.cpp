#include <bits/stdc++.h>
using namespace std;

static inline int letterIdx(char c) {
    if (c == 'A') return 0;
    if (c == 'C') return 1;
    if (c == 'G') return 2;
    return 3; // 'T'
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<string> s(m);
    for (int i = 0; i < m; i++) cin >> s[i];

    const int B = (n + 63) / 64;
    auto ptrAt = [B](vector<uint64_t>& v, int i, int l) -> uint64_t* {
        return v.data() + (size_t)(i * 5 + l) * B;
    };
    auto cptrAt = [B](const vector<uint64_t>& v, int i, int l) -> const uint64_t* {
        return v.data() + (size_t)(i * 5 + l) * B;
    };

    vector<uint64_t> pat((size_t)m * 5 * B, 0);

    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            char c = s[i][j];
            if (c == '?') continue;
            int l = letterIdx(c);
            int blk = j >> 6;
            int bit = j & 63;
            uint64_t mask = 1ULL << bit;
            ptrAt(pat, i, l)[blk] |= mask;
            ptrAt(pat, i, 4)[blk] |= mask;
        }
    }

    // If any pattern is all '?', probability is 1
    for (int i = 0; i < m; i++) {
        const uint64_t* all = cptrAt(pat, i, 4);
        bool any = false;
        for (int b = 0; b < B; b++) {
            if (all[b]) { any = true; break; }
        }
        if (!any) {
            cout << setprecision(20) << (long double)1.0 << "\n";
            return 0;
        }
    }

    // Remove patterns subsumed by another
    vector<char> alive(m, 1);
    auto subsumes = [&](int j, int i) -> bool {
        for (int l = 0; l < 4; l++) {
            const uint64_t* pj = cptrAt(pat, j, l);
            const uint64_t* pi = cptrAt(pat, i, l);
            for (int b = 0; b < B; b++) {
                if (pj[b] & ~pi[b]) return false;
            }
        }
        return true;
    };

    if (m <= 200) {
        for (int i = 0; i < m; i++) {
            if (!alive[i]) continue;
            for (int j = 0; j < m; j++) {
                if (i == j || !alive[j]) continue;
                if (subsumes(j, i)) { alive[i] = 0; break; }
            }
        }
    }

    vector<int> idxs;
    idxs.reserve(m);
    for (int i = 0; i < m; i++) if (alive[i]) idxs.push_back(i);

    int m2 = (int)idxs.size();
    vector<uint64_t> pat2((size_t)m2 * 5 * B, 0);
    for (int ni = 0; ni < m2; ni++) {
        int oi = idxs[ni];
        for (int l = 0; l < 5; l++) {
            const uint64_t* src = cptrAt(pat, oi, l);
            uint64_t* dst = ptrAt(pat2, ni, l);
            memcpy(dst, src, (size_t)B * sizeof(uint64_t));
        }
    }
    pat.swap(pat2);
    m = m2;

    if (m == 0) {
        cout << setprecision(20) << (long double)0.0 << "\n";
        return 0;
    }

    // Inclusion-exclusion with DFS; states indexed by subset size k
    vector<uint64_t> state((size_t)(m + 1) * 5 * B, 0);
    auto statePtr = [B](vector<uint64_t>& v, int k, int l) -> uint64_t* {
        return v.data() + (size_t)(k * 5 + l) * B;
    };
    auto stateCPtr = [B](const vector<uint64_t>& v, int k, int l) -> const uint64_t* {
        return v.data() + (size_t)(k * 5 + l) * B;
    };

    vector<int> fixedCnt(m + 1, 0);
    vector<char> conflict(m + 1, 0);

    long double ans = 0.0L;

    function<void(int,int)> dfs = [&](int pos, int k) {
        if (conflict[k]) return;

        if (pos == m) {
            if (k > 0) {
                long double term = ldexpl(1.0L, -2 * fixedCnt[k]); // 4^{-fixedCnt}
                if (k & 1) ans += term;
                else ans -= term;
            }
            return;
        }

        // Exclude
        dfs(pos + 1, k);

        // Include
        const uint64_t* pA = cptrAt(pat, pos, 0);
        const uint64_t* pC = cptrAt(pat, pos, 1);
        const uint64_t* pG = cptrAt(pat, pos, 2);
        const uint64_t* pT = cptrAt(pat, pos, 3);
        const uint64_t* pAll = cptrAt(pat, pos, 4);

        const uint64_t* cA = stateCPtr(state, k, 0);
        const uint64_t* cC = stateCPtr(state, k, 1);
        const uint64_t* cG = stateCPtr(state, k, 2);
        const uint64_t* cT = stateCPtr(state, k, 3);
        const uint64_t* cAll = stateCPtr(state, k, 4);

        uint64_t* nA = statePtr(state, k + 1, 0);
        uint64_t* nC = statePtr(state, k + 1, 1);
        uint64_t* nG = statePtr(state, k + 1, 2);
        uint64_t* nT = statePtr(state, k + 1, 3);
        uint64_t* nAll = statePtr(state, k + 1, 4);

        bool conf = false;
        int add = 0;

        for (int b = 0; b < B; b++) {
            uint64_t curAll = cAll[b];

            uint64_t ca = cA[b], cc = cC[b], cg = cG[b], ct = cT[b];
            uint64_t pa = pA[b], pc = pC[b], pg = pG[b], pt = pT[b];
            uint64_t pall = pAll[b];

            uint64_t confBits = 0;
            confBits |= (pa & (curAll & ~ca));
            confBits |= (pc & (curAll & ~cc));
            confBits |= (pg & (curAll & ~cg));
            confBits |= (pt & (curAll & ~ct));
            if (confBits) {
                conf = true;
                break;
            }

            nA[b] = ca | pa;
            nC[b] = cc | pc;
            nG[b] = cg | pg;
            nT[b] = ct | pt;

            uint64_t newAll = curAll | pall;
            nAll[b] = newAll;

            uint64_t newBits = pall & ~curAll;
            add += __builtin_popcountll(newBits);
        }

        conflict[k + 1] = conf;
        if (!conf) {
            fixedCnt[k + 1] = fixedCnt[k] + add;
            dfs(pos + 1, k + 1);
        }
    };

    dfs(0, 0);

    if (fabsl(ans) < 1e-30L) ans = 0.0L;
    if (ans < 0.0L) ans = 0.0L;
    if (ans > 1.0L) ans = 1.0L;

    cout << setprecision(20) << ans << "\n";
    return 0;
}