#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

typedef long long ll;
typedef complex<double> cd;
const double PI = acos(-1.0);

void fft(vector<cd>& a, bool invert) {
    int n = (int)a.size();
    for (int i = 1, j = 0; i < n; i++) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) swap(a[i], a[j]);
    }
    for (int len = 2; len <= n; len <<= 1) {
        double ang = 2.0 * PI / len * (invert ? -1 : 1);
        cd wlen(cos(ang), sin(ang));
        for (int i = 0; i < n; i += len) {
            cd w(1);
            for (int j = 0; j < len / 2; j++) {
                cd u = a[i+j], v = a[i+j+len/2]*w;
                a[i+j] = u+v;
                a[i+j+len/2] = u-v;
                w *= wlen;
            }
        }
    }
    if (invert) {
        for (auto& x : a) x /= n;
    }
}

vector<ll> cyclic_conv(const vector<int>& fA, const vector<int>& fB, int M) {
    int n = 1;
    while (n < 2*M) n <<= 1;
    vector<cd> fa(n, 0), fb(n, 0);
    for (int i = 0; i < M; i++) fa[i] = fA[i];
    for (int i = 0; i < M; i++) fb[i] = fB[i];
    fft(fa, false);
    fft(fb, false);
    for (int i = 0; i < n; i++) fa[i] *= fb[i];
    fft(fa, true);
    vector<ll> res(M, 0);
    for (int i = 0; i < 2*M-1; i++) {
        res[i % M] += llround(fa[i].real());
    }
    return res;
}

ll compute_objective(const vector<int>& indicators, int M,
                     const vector<ll>& w,
                     const vector<ll>& d) {
    int sizeA = 0;
    for (int i = 0; i < M; i++) sizeA += indicators[i];
    if (sizeA == 0 || sizeA == M) return 0LL;

    vector<int> fB(M);
    for (int i = 0; i < M; i++) fB[i] = 1 - indicators[i];

    vector<ll> c = cyclic_conv(indicators, fB, M);

    ll total = 0;
    for (int r = 0; r < M; r++) {
        ll contrib = w[r] * min(c[r], d[r]);
        total += contrib;
    }
    return total;
}

// Compute baseline: sort by (cost_i, i) ascending, greedily add while budget allows
vector<int> compute_baseline(int M, const vector<ll>& cost, ll B) {
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        return cost[a] < cost[b] || (cost[a] == cost[b] && a < b);
    });
    vector<int> base;
    ll spent = 0;
    for (int i : order) {
        if (cost[i] <= B - spent) {
            base.push_back(i);
            spent += cost[i];
        }
    }
    return base;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    int M = inf.readInt();
    ll B = inf.readLong();

    vector<ll> cost(M);
    for (int i = 0; i < M; i++) cost[i] = inf.readLong();

    vector<ll> w(M), d(M);
    for (int i = 0; i < M; i++) w[i] = inf.readLong();
    for (int i = 0; i < M; i++) d[i] = inf.readLong();

    // Compute baseline
    vector<int> base_sol = compute_baseline(M, cost, B);
    vector<int> base_ind(M, 0);
    for (int p : base_sol) base_ind[p] = 1;
    ll U_base = compute_objective(base_ind, M, w, d);

    // Read participant output
    int K = ouf.readInt(0, M, "K must be between 0 and M");

    vector<int> ports;
    ports.reserve(K);
    for (int i = 0; i < K; i++) {
        int p = ouf.readInt(0, M-1, "port index out of range [0, M-1]");
        ports.push_back(p);
    }

    // *** Strict EOF check: reject trailing garbage ***
    // readEof() in testlib skips whitespace/newlines and then asserts EOF
    if (!ouf.seekEof()) {
        quitf(_wa, "extra output after the %d port indices", K);
    }

    // Validate strictly increasing order
    for (int i = 1; i < K; i++) {
        if (ports[i] <= ports[i-1]) {
            quitf(_wa, "ports must be strictly increasing (got %d then %d at positions %d,%d)",
                  ports[i-1], ports[i], i-1, i);
        }
    }

    // Validate all ports distinct (strictly increasing already guarantees this,
    // but keep for clarity)
    {
        set<int> seen(ports.begin(), ports.end());
        if ((int)seen.size() != K) {
            quitf(_wa, "duplicate ports in output");
        }
    }

    // Validate budget (overflow-safe)
    ll total_cost = 0;
    for (int p : ports) {
        if (cost[p] > B - total_cost) {
            quitf(_wa, "total cost exceeds budget B=%lld", B);
        }
        total_cost += cost[p];
    }

    // Compute participant objective
    vector<int> part_f(M, 0);
    for (int p : ports) part_f[p] = 1;
    ll U = compute_objective(part_f, M, w, d);

    // Scoring per problem statement:
    // score = 0                    if U == 0 and U_base == 0
    // score = 100 * U / (U+U_base) otherwise
    // We pass ratio in [0,1] to quitp (it multiplies by 100 internally).
    double ratio;
    if (U == 0 && U_base == 0) {
        ratio = 0.0;
    } else {
        double dU = (double)U;
        double dBase = (double)U_base;
        ratio = dU / (dU + dBase);
    }
    if (ratio < 0.0) ratio = 0.0;
    if (ratio > 1.0) ratio = 1.0;

    quitp(ratio, "U=%lld U_base=%lld Ratio: %.9f", U, U_base, ratio);

    return 0;
}