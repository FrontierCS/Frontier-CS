#include <bits/stdc++.h>
using namespace std;

using ll = long long;

// compute delta for swapping facilities a and b
double compute_delta(int a, int b, const vector<vector<int>>& F,
                     const vector<vector<int>>& D,
                     const vector<int>& p) {
    double delta = 0.0;
    int pa = p[a], pb = p[b];
    int n = F.size();
    for (int j = 0; j < n; ++j) {
        int pj = p[j];
        delta += (F[a][j] - F[b][j]) * (D[pb][pj] - D[pa][pj]);
        delta += (F[j][a] - F[j][b]) * (D[pj][pb] - D[pj][pa]);
    }
    return delta;
}

// power iteration for largest eigenvector
vector<double> power_iteration(const vector<vector<int>>& M, int iters=100) {
    int n = M.size();
    vector<double> v(n);
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> dist(0.0, 1.0);
    for (int i = 0; i < n; ++i) v[i] = dist(rng);

    for (int iter = 0; iter < iters; ++iter) {
        vector<double> w(n, 0.0);
        for (int i = 0; i < n; ++i) {
            double s = 0.0;
            for (int j = 0; j < n; ++j)
                s += M[i][j] * v[j];
            w[i] = s;
        }
        double norm = 0.0;
        for (double x : w) norm += x*x;
        norm = sqrt(norm);
        if (norm < 1e-12) break;
        for (int i = 0; i < n; ++i) v[i] = w[i] / norm;
    }
    return v;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<vector<int>> D(n, vector<int>(n));
    vector<vector<int>> F(n, vector<int>(n));

    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            cin >> D[i][j];

    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            cin >> F[i][j];

    // symmetrize matrices for spectral method
    vector<vector<int>> F_sym(n, vector<int>(n));
    vector<vector<int>> D_sym(n, vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            F_sym[i][j] = F[i][j] + F[j][i];
            D_sym[i][j] = D[i][j] + D[j][i];
        }
    }
    // similarity matrix S = 2 - D_sym
    vector<vector<int>> S(n, vector<int>(n));
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            S[i][j] = 2 - D_sym[i][j];

    // compute eigenvectors
    vector<double> v_fac = power_iteration(F_sym, 100);
    vector<double> v_loc = power_iteration(S, 100);

    // get orders by sorting indices
    vector<int> idx_fac(n), idx_loc(n);
    iota(idx_fac.begin(), idx_fac.end(), 0);
    iota(idx_loc.begin(), idx_loc.end(), 0);
    sort(idx_fac.begin(), idx_fac.end(),
         [&](int a, int b) { return v_fac[a] < v_fac[b]; });
    sort(idx_loc.begin(), idx_loc.end(),
         [&](int a, int b) { return v_loc[a] < v_loc[b]; });

    // build permutation from alignment
    auto build_perm = [&](bool reverse_loc) {
        vector<int> p(n);
        for (int i = 0; i < n; ++i) {
            int fac = idx_fac[i];
            int loc = reverse_loc ? idx_loc[n-1-i] : idx_loc[i];
            p[fac] = loc;
        }
        return p;
    };

    // try both alignments and choose the one with lower cost
    vector<int> best_p;
    ll best_cost = LLONG_MAX;

    for (int rev = 0; rev < 2; ++rev) {
        vector<int> p = build_perm(rev);
        ll cost = 0;
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                cost += F[i][j] * D[p[i]][p[j]];
        if (cost < best_cost) {
            best_cost = cost;
            best_p = p;
        }
    }

    // local search with random swaps
    ll current_cost = best_cost;
    vector<int> p = best_p;
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> rand_idx(0, n-1);
    int attempts = 200000; // adjust based on time limit
    for (int t = 0; t < attempts; ++t) {
        int a = rand_idx(rng);
        int b = rand_idx(rng);
        if (a == b) continue;
        double delta = compute_delta(a, b, F, D, p);
        if (delta < 0) {
            swap(p[a], p[b]);
            current_cost += (ll)round(delta); // delta is actually integer, but stored as double
        }
    }

    // output permutation (1-indexed)
    for (int i = 0; i < n; ++i) {
        cout << p[i] + 1;
        if (i+1 < n) cout << ' ';
    }
    cout << '\n';

    return 0;
}