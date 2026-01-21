#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<int> S(N);
    for (int i = 0; i < N; ++i) cin >> S[i];

    int M;
    cin >> M;
    vector<int> X(M), Y(M);

    // First pass: compute pi_M^{-1} (inverse of Jerry's total permutation)
    vector<int> pi_inv_M(N);
    for (int i = 0; i < N; ++i) pi_inv_M[i] = i;

    for (int k = 0; k < M; ++k) {
        int x, y;
        cin >> x >> y;
        X[k] = x;
        Y[k] = y;
        if (x != y) {
            swap(pi_inv_M[x], pi_inv_M[y]);
        }
    }

    // T = pi_M^{-1} ◦ A_init
    vector<int> T(N);
    for (int p = 0; p < N; ++p) {
        int val = S[p];
        T[p] = pi_inv_M[val];
    }

    // Decompose T into transpositions (minimal number)
    vector<char> vis(N, 0);
    vector<pair<int,int>> R_ops;
    R_ops.reserve(N);

    for (int i = 0; i < N; ++i) {
        if (!vis[i]) {
            int cur = i;
            vector<int> cycle;
            while (!vis[cur]) {
                vis[cur] = 1;
                cycle.push_back(cur);
                cur = T[cur];
            }
            int L = (int)cycle.size();
            if (L > 1) {
                int c0 = cycle[0];
                for (int idx = 1; idx < L; ++idx) {
                    int cj = cycle[idx];
                    R_ops.emplace_back(c0, cj);
                }
            }
        }
    }

    int L_ops = (int)R_ops.size();
    // Problem guarantee ensures L_ops <= M

    // Second pass: compute our swaps using prefix permutations π_{k+1}
    vector<int> U(M), V(M);
    vector<int> pi(N), pi_inv(N);
    for (int i = 0; i < N; ++i) {
        pi[i] = i;
        pi_inv[i] = i;
    }

    int idx_ops = 0;
    long long sumDist = 0;

    for (int k = 0; k < M; ++k) {
        int x = X[k], y = Y[k];

        // Update π and π_inv for Jerry's move J_k = (x, y)
        if (x != y) {
            int a = pi_inv[x];
            int b = pi_inv[y];
            swap(pi[a], pi[b]);
            swap(pi_inv[x], pi_inv[y]);
        }

        int u, v;
        if (idx_ops < L_ops) {
            int p = R_ops[idx_ops].first;
            int q = R_ops[idx_ops].second;
            ++idx_ops;
            u = pi[p];
            v = pi[q];
        } else {
            u = v = 0; // identity swap
        }
        U[k] = u;
        V[k] = v;
        long long d = (long long)u - (long long)v;
        if (d < 0) d = -d;
        sumDist += d;
    }

    long long R_rounds = M;
    long long Vtotal = R_rounds * sumDist;

    cout << R_rounds << '\n';
    for (int k = 0; k < M; ++k) {
        cout << U[k] << ' ' << V[k] << '\n';
    }
    cout << Vtotal << '\n';

    return 0;
}