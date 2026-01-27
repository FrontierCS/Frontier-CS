#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() {
        return getchar_unlocked();
    }
    int nextInt() {
        int c = gc();
        while (c!='-' && (c<'0' || c>'9')) c = gc();
        int sgn = 1;
        if (c=='-') { sgn = -1; c = gc(); }
        int x = 0;
        while (c>='0' && c<='9') {
            x = x*10 + (c - '0');
            c = gc();
        }
        return x * sgn;
    }
} fs;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    n = fs.nextInt();
    if (n <= 0) return 0;

    const int N = n;
    vector<uint8_t> D((size_t)N * N);
    vector<uint8_t> F((size_t)N * N);

    vector<int> rowSumD(N,0), colSumD(N,0);
    for (int i = 0; i < N; ++i) {
        size_t base = (size_t)i * N;
        for (int j = 0; j < N; ++j) {
            int v = fs.nextInt();
            uint8_t b = (uint8_t)(v & 1);
            D[base + j] = b;
            rowSumD[i] += b;
            colSumD[j] += b;
        }
    }
    vector<int> rowSumF(N,0), colSumF(N,0);
    for (int i = 0; i < N; ++i) {
        size_t base = (size_t)i * N;
        for (int j = 0; j < N; ++j) {
            int v = fs.nextInt();
            uint8_t b = (uint8_t)(v & 1);
            F[base + j] = b;
            rowSumF[i] += b;
            colSumF[j] += b;
        }
    }

    // Degrees
    vector<int> degF(N), degD(N);
    for (int i = 0; i < N; ++i) {
        degF[i] = rowSumF[i] + colSumF[i];
        degD[i] = rowSumD[i] + colSumD[i];
    }

    // Initial assignment: map high-degree F to low-degree D
    vector<int> fac_idx(N), loc_idx(N);
    iota(fac_idx.begin(), fac_idx.end(), 0);
    iota(loc_idx.begin(), loc_idx.end(), 0);
    sort(fac_idx.begin(), fac_idx.end(), [&](int a, int b){ 
        if (degF[a] != degF[b]) return degF[a] > degF[b];
        return a < b;
    });
    sort(loc_idx.begin(), loc_idx.end(), [&](int a, int b){ 
        if (degD[a] != degD[b]) return degD[a] < degD[b];
        return a < b;
    });

    vector<int> pos(N, -1); // facility -> location
    for (int k = 0; k < N; ++k) pos[fac_idx[k]] = loc_idx[k];

    // Optional: slight shuffle among equal degree blocks to avoid ties
    // Skipped to keep deterministic.

    // Compute initial cost (not necessary for output but for improvement)
    auto compute_cost = [&](const vector<int>& p)->long long {
        long long cost = 0;
        // cost = sum_{i,j} F[i,j] * D[p(i), p(j)]
        for (int i = 0; i < N; ++i) {
            const uint8_t* Fi = &F[(size_t)i * N];
            int pi = p[i];
            const uint8_t* Dpi = &D[(size_t)pi * N];
            for (int j = 0; j < N; ++j) {
                if (Fi[j]) {
                    int pj = p[j];
                    cost += Dpi[pj];
                }
            }
        }
        return cost;
    };

    // Local search: pairwise swaps with sampled candidates
    // Time-bounded
    auto now = chrono::steady_clock::now;
    auto start = now();
    const double TIME_LIMIT_MS = 900.0; // adjust conservatively
    // Precompute list of indices for sampling
    vector<int> allIdx(N);
    iota(allIdx.begin(), allIdx.end(), 0);
    std::mt19937 rng(712367123);
    int sampleSize = max(5, min(50, N / 20)); // adaptive sample size

    // Helper to compute delta for swapping facilities a and b (positions pos[a], pos[b])
    auto delta_swap = [&](int a, int b, const vector<int>& p)->long long {
        int pa = p[a], pb = p[b];
        if (pa == pb) return 0;
        long long delta = 0;

        // Terms for k != a,b
        for (int k = 0; k < N; ++k) {
            if (k == a || k == b) continue;
            int pk = p[k];

            // F[a][k]*(D[pb][pk]-D[pa][pk]) + F[b][k]*(D[pa][pk]-D[pb][pk])
            uint8_t Fak = F[(size_t)a * N + k];
            uint8_t Fbk = F[(size_t)b * N + k];
            int d_apb_pk = D[(size_t)pb * N + pk] - D[(size_t)pa * N + pk];
            int d_bpa_pk = -d_apb_pk; // D[pa][pk]-D[pb][pk]
            delta += (long long)Fak * d_apb_pk + (long long)Fbk * d_bpa_pk;

            // F[k][a]*(D[pk][pb]-D[pk][pa]) + F[k][b]*(D[pk][pa]-D[pk][pb])
            uint8_t Fka = F[(size_t)k * N + a];
            uint8_t Fkb = F[(size_t)k * N + b];
            int d_pk_papb = D[(size_t)pk * N + pb] - D[(size_t)pk * N + pa];
            int d_pk_pbpa = -d_pk_papb;
            delta += (long long)Fka * d_pk_papb + (long long)Fkb * d_pk_pbpa;
        }

        // Self and cross terms for a,b
        uint8_t Faa = F[(size_t)a * N + a];
        uint8_t Fbb = F[(size_t)b * N + b];
        uint8_t Fab = F[(size_t)a * N + b];
        uint8_t Fba = F[(size_t)b * N + a];

        int Dpbpb = D[(size_t)pb * N + pb];
        int Dpapa = D[(size_t)pa * N + pa];
        int Dpbpa = D[(size_t)pb * N + pa];
        int Dpapb = D[(size_t)pa * N + pb];

        delta += (long long)Faa * (Dpbpb - Dpapa);
        delta += (long long)Fbb * (Dpapa - Dpbpb);
        delta += (long long)Fab * (Dpbpa - Dpapb);
        delta += (long long)Fba * (Dpapb - Dpbpa);

        return delta;
    };

    // Try limited rounds of improvement
    // We'll do first-improvement with sampled partners until time runs or no improvement in a full pass.
    while (true) {
        bool improved_any = false;
        // Order of facilities
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);

        for (int idx = 0; idx < N; ++idx) {
            if (chrono::duration<double, std::milli>(now() - start).count() > TIME_LIMIT_MS) break;
            int a = order[idx];

            // Sample candidate b's
            // We'll sample from allIdx; ensure distinct from a
            for (int s = 0; s < sampleSize; ++s) {
                int b = rng() % N;
                if (b == a) continue;

                long long d = delta_swap(a, b, pos);
                if (d < 0) {
                    // Apply swap
                    std::swap(pos[a], pos[b]);
                    improved_any = true;
                    break; // first improvement for this a
                }
            }
        }
        if (!improved_any) break;
        if (chrono::duration<double, std::milli>(now() - start).count() > TIME_LIMIT_MS) break;
    }

    // Output permutation 1-based
    // p_i = assigned location index + 1
    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << (pos[i] + 1);
    }
    cout << '\n';
    return 0;
}