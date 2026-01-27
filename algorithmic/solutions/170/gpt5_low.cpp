#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    long long L;
    if (!(cin >> N >> L)) return 0;
    vector<int> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];

    // Constants: N=100, L=500000
    // We set a_i as a Hamiltonian cycle to guarantee reachability.
    vector<int> a(N), b(N);
    for (int i = 0; i < N; ++i) a[i] = (i + 1) % N;

    // Desired total in-degree per node ~ din[i] = 200 * T[i] / L, clamp to [1,4]
    // We will allocate extras e[i] = din[i] - 1, with 0 <= e[i] <= 3 and sum e[i] = N.
    const int total_out = 2 * N; // 200
    const int base_in_each = 1;  // from a-cycle
    const int D = N;             // total extras to allocate across b-edges

    vector<double> w(N), econt(N), residual(N);
    vector<int> e(N);
    int S = 0;
    for (int i = 0; i < N; ++i) {
        w[i] = (double)total_out * (double)T[i] / (double)L; // in [0,4]
        econt[i] = w[i] - 1.0; // in [-1,3]
        double r = floor(econt[i] + 0.5); // nearest integer
        int er = (int)r;
        if (er < 0) er = 0;
        if (er > 3) er = 3;
        e[i] = er;
        S += e[i];
        residual[i] = econt[i] - (double)e[i]; // in [-0.5,0.5]
    }

    // Adjust to ensure sum e[i] == D
    vector<int> idx(N);
    iota(idx.begin(), idx.end(), 0);

    if (S < D) {
        // increase some e[i] where possible (e[i] < 3) with largest positive residual
        sort(idx.begin(), idx.end(), [&](int i, int j){
            if (residual[i] != residual[j]) return residual[i] > residual[j];
            return T[i] > T[j];
        });
        int need = D - S;
        for (int k = 0; k < N && need > 0; ++k) {
            int i = idx[k];
            if (e[i] < 3) {
                e[i]++; need--;
            }
        }
        // If still need (all at cap due to pathological rounding), distribute arbitrarily
        for (int i = 0; i < N && need > 0; ++i) {
            if (e[i] < 3) { e[i]++; need--; }
        }
    } else if (S > D) {
        // decrease some e[i] where possible (e[i] > 0) with most negative residual
        sort(idx.begin(), idx.end(), [&](int i, int j){
            if (residual[i] != residual[j]) return residual[i] < residual[j];
            return T[i] < T[j];
        });
        int need = S - D;
        for (int k = 0; k < N && need > 0; ++k) {
            int i = idx[k];
            if (e[i] > 0) {
                e[i]--; need--;
            }
        }
        // If still need (all at floor 0), take from largest e arbitrarily
        for (int i = 0; i < N && need > 0; ++i) {
            if (e[i] > 0) { e[i]--; need--; }
        }
    }

    // Build target pool for b-edges: each node i appears e[i] times; total N entries
    vector<int> pool;
    pool.reserve(N);
    for (int i = 0; i < N; ++i) {
        for (int k = 0; k < e[i]; ++k) pool.push_back(i);
    }
    // Ensure size N (it should be)
    if ((int)pool.size() != N) {
        // In case of any rounding mishap, fix by padding or trimming
        while ((int)pool.size() < N) {
            // Add to nodes with smallest current e and largest T
            int best = -1;
            for (int i = 0; i < N; ++i) {
                if (e[i] < 3 && (best == -1 || e[i] < e[best] || (e[i] == e[best] && T[i] > T[best]))) best = i;
            }
            if (best == -1) best = 0;
            e[best]++; pool.push_back(best);
        }
        while ((int)pool.size() > N) {
            // Remove from nodes with largest e and smallest T
            int best = -1;
            for (int i = 0; i < N; ++i) {
                if (e[i] > 0 && (best == -1 || e[i] > e[best] || (e[i] == e[best] && T[i] < T[best]))) best = i;
            }
            if (best == -1) { pool.resize(N); break; }
            // remove one occurrence of 'best' from pool
            auto it = find(pool.begin(), pool.end(), best);
            if (it != pool.end()) { pool.erase(it); e[best]--; }
            else { pool.pop_back(); }
        }
    }

    // Shuffle pool to spread targets
    // Seed with a simple deterministic seed based on inputs
    uint32_t seed = 123456789u;
    for (int i = 0; i < N; ++i) {
        seed ^= (uint32_t)T[i] + 0x9e3779b9 + (seed<<6) + (seed>>2);
    }
    mt19937 rng(seed);
    shuffle(pool.begin(), pool.end(), rng);

    // Assign b_i from pool, trying to avoid b_i == a_i if possible
    for (int i = 0; i < N; ++i) {
        if (pool.empty()) {
            b[i] = (i + 1) % N; // fallback
            continue;
        }
        int chosen_idx = (int)pool.size() - 1;
        int target = pool[chosen_idx];
        if ((int)pool.size() >= 2 && target == a[i]) {
            // try swap with another to avoid matching a_i
            int other_idx = -1;
            // pick a random other index
            uniform_int_distribution<int> dist(0, (int)pool.size() - 2);
            int start = dist(rng);
            for (int t = 0; t < (int)pool.size() - 1; ++t) {
                int j = (start + t) % ((int)pool.size() - 1);
                if (pool[j] != a[i]) { other_idx = j; break; }
            }
            if (other_idx != -1) chosen_idx = other_idx;
        }
        b[i] = pool[chosen_idx];
        pool.erase(pool.begin() + chosen_idx);
    }

    // Output
    for (int i = 0; i < N; ++i) {
        cout << a[i] << ' ' << b[i] << '\n';
    }

    return 0;
}