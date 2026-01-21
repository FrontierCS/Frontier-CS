#include <bits/stdc++.h>
using namespace std;

struct FastMap {
    uint32_t mask;
    vector<uint32_t> keys; // 0 means empty, keys > 0
    vector<uint32_t> vals;

    static inline uint32_t hash32(uint32_t x) {
        x ^= x >> 16;
        x *= 0x7feb352dU;
        x ^= x >> 15;
        x *= 0x846ca68bU;
        x ^= x >> 16;
        return x;
    }

    explicit FastMap(uint32_t capPow2) {
        keys.assign(capPow2, 0);
        vals.assign(capPow2, 0);
        mask = capPow2 - 1;
    }

    inline bool contains(uint32_t k) const {
        uint32_t i = hash32(k) & mask;
        while (true) {
            uint32_t kk = keys[i];
            if (kk == 0) return false;
            if (kk == k) return true;
            i = (i + 1) & mask;
        }
    }

    inline uint32_t get(uint32_t k) const {
        uint32_t i = hash32(k) & mask;
        while (true) {
            uint32_t kk = keys[i];
            if (kk == k) return vals[i];
            if (kk == 0) return 0;
            i = (i + 1) & mask;
        }
    }

    inline void insert(uint32_t k, uint32_t v) {
        uint32_t i = hash32(k) & mask;
        while (true) {
            uint32_t kk = keys[i];
            if (kk == 0) {
                keys[i] = k;
                vals[i] = v;
                return;
            }
            if (kk == k) {
                // should not happen if keys are unique by construction
                vals[i] = v;
                return;
            }
            i = (i + 1) & mask;
        }
    }
};

struct SAM {
    struct State {
        int next[2];
        int link;
        int len;
    };
    vector<State> st;
    int last;

    explicit SAM(int maxLen = 0) {
        st.reserve(max(2, 2 * maxLen));
        init();
    }

    void init() {
        st.clear();
        st.push_back(State{{-1, -1}, -1, 0});
        last = 0;
    }

    void extend(int c) {
        int cur = (int)st.size();
        st.push_back(State{{-1, -1}, 0, st[last].len + 1});
        int p = last;
        while (p != -1 && st[p].next[c] == -1) {
            st[p].next[c] = cur;
            p = st[p].link;
        }
        if (p == -1) {
            st[cur].link = 0;
        } else {
            int q = st[p].next[c];
            if (st[p].len + 1 == st[q].len) {
                st[cur].link = q;
            } else {
                int clone = (int)st.size();
                st.push_back(st[q]);
                st[clone].len = st[p].len + 1;
                while (p != -1 && st[p].next[c] == q) {
                    st[p].next[c] = clone;
                    p = st[p].link;
                }
                st[q].link = st[cur].link = clone;
            }
        }
        last = cur;
    }

    uint64_t countDistinctSubstrings() const {
        uint64_t ans = 0;
        for (int v = 1; v < (int)st.size(); v++) {
            int p = st[v].link;
            ans += (uint64_t)(st[v].len - st[p].len);
        }
        return ans;
    }
};

static inline uint32_t power_formula(uint32_t a, uint32_t c, uint32_t e) {
    // String: X^a O X^c O X^e, with a,c,e >= 1
    uint32_t mx = max(a, max(c, e));
    uint32_t m1 = min(a, c);
    uint32_t m2 = min(c, e);

    uint64_t term2 = (uint64_t)(a + 1) * (uint64_t)(c + 1);
    uint64_t term3 = (uint64_t)(c + 1) * (uint64_t)(e + 1);
    uint64_t term4 = (uint64_t)(a + 1) * (uint64_t)(e + 1);
    uint64_t term5 = (uint64_t)(m1 + 1) * (uint64_t)(m2 + 1);

    uint64_t p = (uint64_t)mx + term2 + term3 + term4 - term5;
    return (uint32_t)p;
}

static inline uint32_t power_concat(uint32_t Au, uint32_t Bu, uint32_t Av, uint32_t Bv) {
    // w_u = X^Au O X^Bu
    // w_v = X^Av O X^Bv
    // w_u w_v = X^Au O X^(Bu+Av) O X^Bv
    return power_formula(Au, Bu + Av, Bv);
}

static void self_test_formula() {
    // Exhaustive small test
    for (uint32_t a = 1; a <= 6; a++) {
        for (uint32_t c = 1; c <= 6; c++) {
            for (uint32_t e = 1; e <= 6; e++) {
                string s;
                s.append(a, 'X');
                s.push_back('O');
                s.append(c, 'X');
                s.push_back('O');
                s.append(e, 'X');

                SAM sam((int)s.size());
                sam.init();
                for (char ch : s) sam.extend(ch == 'X' ? 0 : 1);
                uint64_t samAns = sam.countDistinctSubstrings();
                uint64_t fAns = power_formula(a, c, e);
                if (samAns != fAns) {
                    // If this ever triggers, formula is wrong.
                    exit(0);
                }
            }
        }
    }
}

static inline uint32_t pack_uv(uint32_t u, uint32_t v) {
    return (u << 10) | v; // u,v <= 1000 < 1024
}
static inline uint32_t unpack_u(uint32_t packed) { return packed >> 10; }
static inline uint32_t unpack_v(uint32_t packed) { return packed & 1023U; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    self_test_formula();

    int n;
    if (!(cin >> n)) return 0;

    uint32_t nn = (uint32_t)n;
    uint64_t need = (uint64_t)nn * (uint64_t)nn;
    uint32_t cap = 1;
    while ((uint64_t)cap < need * 2ULL) cap <<= 1;
    FastMap mp(cap);

    // Initial max word length target (can expand if needed), must be <= 30*n
    int maxWordLen = min(30 * n, 8000);
    if (maxWordLen < 3) maxWordLen = 3;
    int limitR = (maxWordLen - 1) / 2;
    if (limitR < 1) limitR = 1;

    vector<uint32_t> A(n + 1), B(n + 1);
    vector<string> words(n + 1);

    unordered_set<uint64_t> usedAB;
    usedAB.reserve((size_t)n * 2);

    uint64_t rng = 88172645463325252ull;
    auto next64 = [&]() -> uint64_t {
        rng ^= rng << 7;
        rng ^= rng >> 9;
        return rng;
    };

    for (uint32_t i = 1; i <= (uint32_t)n; i++) {
        int attempts = 0;
        while (true) {
            attempts++;
            if (attempts > 200000) {
                if (maxWordLen < 30 * n) {
                    maxWordLen = min(30 * n, maxWordLen * 2);
                    limitR = (maxWordLen - 1) / 2;
                    if (limitR < 1) limitR = 1;
                    attempts = 0;
                } else {
                    // Should be extremely unlikely; restart with different RNG state.
                    rng ^= (uint64_t)i * 0x9e3779b97f4a7c15ULL;
                    attempts = 0;
                }
            }

            uint32_t Ac = 1 + (uint32_t)(next64() % (uint64_t)limitR);
            uint32_t Bc = 1 + (uint32_t)(next64() % (uint64_t)limitR);
            if ((int)(Ac + Bc + 1) > maxWordLen) continue;

            uint64_t abKey = (uint64_t(Ac) << 32) | uint64_t(Bc);
            if (usedAB.find(abKey) != usedAB.end()) continue;

            bool ok = true;
            vector<uint32_t> pvals;
            pvals.reserve(2 * i - 1);

            for (uint32_t j = 1; j < i; j++) {
                uint32_t p1 = power_concat(Ac, Bc, A[j], B[j]);
                if (p1 == 0 || mp.contains(p1)) { ok = false; break; }
                pvals.push_back(p1);

                uint32_t p2 = power_concat(A[j], B[j], Ac, Bc);
                if (p2 == 0 || mp.contains(p2)) { ok = false; break; }
                pvals.push_back(p2);
            }
            if (!ok) continue;

            uint32_t ps = power_concat(Ac, Bc, Ac, Bc);
            if (ps == 0 || mp.contains(ps)) continue;
            pvals.push_back(ps);

            sort(pvals.begin(), pvals.end());
            for (size_t k = 1; k < pvals.size(); k++) {
                if (pvals[k] == pvals[k - 1]) { ok = false; break; }
            }
            if (!ok) continue;

            A[i] = Ac;
            B[i] = Bc;
            usedAB.insert(abKey);

            // Insert new pairs into map
            for (uint32_t j = 1; j < i; j++) {
                uint32_t p_ij = power_concat(A[i], B[i], A[j], B[j]);
                uint32_t p_ji = power_concat(A[j], B[j], A[i], B[i]);
                mp.insert(p_ij, pack_uv(i, j));
                mp.insert(p_ji, pack_uv(j, i));
            }
            uint32_t p_ii = power_concat(A[i], B[i], A[i], B[i]);
            mp.insert(p_ii, pack_uv(i, i));

            break;
        }

        // Construct the word
        string w;
        w.reserve((size_t)A[i] + 1 + (size_t)B[i]);
        w.append(A[i], 'X');
        w.push_back('O');
        w.append(B[i], 'X');
        words[i] = std::move(w);
    }

    for (int i = 1; i <= n; i++) {
        cout << words[i] << '\n';
    }
    cout.flush();

    int q;
    if (!(cin >> q)) return 0;
    for (int qi = 0; qi < q; qi++) {
        long long p;
        cin >> p;
        uint32_t packed = mp.get((uint32_t)p);
        uint32_t u = unpack_u(packed);
        uint32_t v = unpack_v(packed);
        cout << u << ' ' << v << '\n';
        cout.flush();
    }

    return 0;
}