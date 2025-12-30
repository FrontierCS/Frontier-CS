#include <bits/stdc++.h>
using namespace std;

struct Bits {
    uint64_t lo = 0, hi = 0; // supports up to 128 bits
};
static inline void setbit(Bits &b, int idx) {
    if (idx < 64) b.lo |= (1ULL << idx);
    else b.hi |= (1ULL << (idx - 64));
}
static inline Bits bor(const Bits &a, const Bits &b) {
    return Bits{a.lo | b.lo, a.hi | b.hi};
}
static inline bool beq(const Bits &a, const Bits &b) {
    return a.lo == b.lo && a.hi == b.hi;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int N = 1000;
    const int q = 11;
    const int L = 6;
    const int M = q * L; // 66 tests

    vector<vector<int>> rows(M);
    vector<Bits> masks(N + 1);

    // Map position p (1..1000) to polynomial f(x)=a0+a1*x+a2*x^2 over GF(11), degree < 3
    // Evaluate at x=0..5 to get L symbols, then KS one-hot mapping to rows.
    for (int p = 1; p <= N; ++p) {
        int idx = p - 1;
        int a0 = idx % q; idx /= q;
        int a1 = idx % q; idx /= q;
        int a2 = idx % q;

        Bits bm;
        for (int t = 0; t < L; ++t) {
            int x = t;
            int y = (a0 + a1 * x + a2 * x * x) % q;
            int r = t * q + y;
            rows[r].push_back(p);
            setbit(bm, r);
        }
        masks[p] = bm;
    }

    auto send_query = [&](const vector<int>& pos) {
        cout << "? " << pos.size();
        for (int v : pos) cout << ' ' << v;
        cout << '\n';
        cout.flush();
    };

    int sent = 0;
    for (int r = 0; r < M && sent < R; ++r) {
        send_query(rows[r]);
        ++sent;
    }

    cout << "@\n";
    cout.flush();

    int Lresp;
    if (!(cin >> Lresp)) return 0;
    vector<int> resp(sent, 0);
    for (int i = 0; i < Lresp; ++i) {
        int x; cin >> x;
        if (i < sent) resp[i] = x;
    }

    Bits outcome;
    for (int i = 0; i < sent; ++i) if (resp[i]) setbit(outcome, i);

    vector<int> cand;
    cand.reserve(2);

    // Subset-check decoding (works for 2-disjunct matrices)
    for (int p = 1; p <= N; ++p) {
        Bits bm = masks[p];
        bool ok = ((bm.lo & ~outcome.lo) == 0) && ((bm.hi & ~outcome.hi) == 0);
        if (ok) cand.push_back(p);
    }

    int a = 1, b = 1;
    if (cand.size() == 1) {
        a = b = cand[0];
    } else if (cand.size() == 2) {
        a = cand[0];
        b = cand[1];
    } else {
        // Fallback: brute-force unique pair by OR-matching outcome
        bool found = false;
        for (int i = 1; i <= N && !found; ++i) {
            for (int j = i; j <= N; ++j) {
                Bits u = bor(masks[i], masks[j]);
                if (beq(u, outcome)) {
                    a = i; b = j;
                    found = true;
                    break;
                }
            }
        }
    }

    cout << "! " << a << ' ' << b << '\n';
    cout.flush();
    return 0;
}