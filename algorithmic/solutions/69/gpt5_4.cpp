#include <bits/stdc++.h>
using namespace std;

struct Entry {
    unsigned long long val;
    int u, v;
};

static inline unsigned long long compute_val(int A, int B, int C, int D) {
    __int128 sX = (A > C ? A : C);
    __int128 sO = (B > D ? B : D);
    __int128 AB = (__int128)A * B;
    __int128 CD = (__int128)C * D;
    __int128 mnAC = (A < C ? A : C);
    __int128 mnBD = (B < D ? B : D);
    __int128 BC = (__int128)B * C;
    __int128 ABC = AB * C;
    __int128 BCD = BC * D;
    __int128 ABCD = AB * CD;
    __int128 res = sX + sO + (AB + CD - mnAC * mnBD) + BC + ABC + BCD + ABCD;
    return (unsigned long long)res;
}

bool build_mapping(int n, int L, const vector<int>& A, vector<Entry>& vec) {
    vec.clear();
    vec.reserve((size_t)n * (size_t)n);
    vector<int> B(n+1);
    vector<unsigned long long> AB(n+1);
    for (int i = 1; i <= n; ++i) {
        B[i] = L - A[i];
        AB[i] = (unsigned long long)A[i] * (unsigned long long)B[i];
    }
    for (int i = 1; i <= n; ++i) {
        int Ai = A[i], Bi = B[i];
        for (int j = 1; j <= n; ++j) {
            int Aj = A[j], Bj = B[j];
            unsigned long long val = compute_val(Ai, Bi, Aj, Bj);
            vec.push_back({val, i, j});
        }
    }
    sort(vec.begin(), vec.end(), [](const Entry& x, const Entry& y){
        if (x.val != y.val) return x.val < y.val;
        if (x.u != y.u) return x.u < y.u;
        return x.v < y.v;
    });
    for (size_t k = 1; k < vec.size(); ++k) {
        if (vec[k].val == vec[k-1].val) {
            if (vec[k].u != vec[k-1].u || vec[k].v != vec[k-1].v) {
                return false; // collision
            }
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Try to find L and A[] such that mapping is injective
    int L = max(n + 1, 2 * n); // start with moderate length
    int Lmax = 30 * n;
    vector<int> A(n+1);
    vector<Entry> vec;

    bool ok = false;
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    while (true) {
        if (L > Lmax) L = Lmax;
        // First try deterministic A[i] = i
        for (int i = 1; i <= n; ++i) A[i] = i;
        if (build_mapping(n, L, A, vec)) { ok = true; break; }

        // Try a randomized assignment of A within [1..L-1], distinct
        if (L >= n + 1) {
            vector<int> pool(L - 1);
            iota(pool.begin(), pool.end(), 1);
            shuffle(pool.begin(), pool.end(), rng);
            for (int i = 1; i <= n; ++i) A[i] = pool[i - 1];
            if (build_mapping(n, L, A, vec)) { ok = true; break; }
        }

        if (L == Lmax) break;
        // Increase L and try again
        long long nextL = (long long)L * 2;
        if (nextL > Lmax) nextL = Lmax;
        L = (int)nextL;
    }

    if (!ok) {
        // As a last resort, try maximal L with a different random A a couple of times
        L = Lmax;
        for (int attempt = 0; attempt < 3 && !ok; ++attempt) {
            vector<int> pool(L - 1);
            iota(pool.begin(), pool.end(), 1);
            shuffle(pool.begin(), pool.end(), rng);
            for (int i = 1; i <= n; ++i) A[i] = pool[i - 1];
            if (build_mapping(n, L, A, vec)) { ok = true; break; }
        }
        if (!ok) {
            // Fallback: deterministic A[i] = i at Lmax (should be extremely unlikely to fail uniqueness)
            for (int i = 1; i <= n; ++i) A[i] = i;
            build_mapping(n, L, A, vec);
        }
    }

    // Print the words
    for (int i = 1; i <= n; ++i) {
        int Ai = A[i];
        int Bi = L - Ai;
        string s1(Ai, 'X');
        string s2(Bi, 'O');
        cout << s1 << s2 << '\n';
    }
    cout.flush();

    // Read queries and answer via binary search over vec
    int q;
    if (!(cin >> q)) return 0;
    while (q--) {
        unsigned long long p;
        cin >> p;
        auto it = lower_bound(vec.begin(), vec.end(), p, [](const Entry& e, const unsigned long long x){
            return e.val < x;
        });
        if (it != vec.end() && it->val == p) {
            cout << it->u << ' ' << it->v << '\n';
        } else {
            // Should not happen if uniqueness holds; fallback
            cout << 1 << ' ' << 1 << '\n';
        }
        cout.flush();
    }

    return 0;
}