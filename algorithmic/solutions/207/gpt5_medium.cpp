#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if(!(cin >> N)) return 0;
    vector<int> S(N);
    for(int i = 0; i < N; ++i) cin >> S[i];
    int M;
    cin >> M;
    vector<int> X(M), Y(M);
    for(int i = 0; i < M; ++i) cin >> X[i] >> Y[i];

    // Build Pi_needed: Pi[i] = position of value i in initial S
    vector<int> pos0(N);
    for (int i = 0; i < N; ++i) pos0[S[i]] = i;
    vector<int> Pi(N);
    for (int i = 0; i < N; ++i) Pi[i] = pos0[i];

    // Build T_inv = Q_final after all M Jerry swaps: swap entries at positions X[i], Y[i]
    vector<int> Tinv(N);
    iota(Tinv.begin(), Tinv.end(), 0);
    for (int i = 0; i < M; ++i) {
        swap(Tinv[X[i]], Tinv[Y[i]]);
    }

    // D = Pi ∘ T_inv
    vector<int> D(N);
    for (int i = 0; i < N; ++i) D[i] = Pi[Tinv[i]];

    // Decompose D into cycles and build transpositions U so that product U_{K-1}...U_0 = D
    vector<char> vis(N, 0);
    vector<pair<int,int>> U;
    U.reserve(N);
    for (int i = 0; i < N; ++i) {
        if (vis[i]) continue;
        int cur = i;
        vector<int> cyc;
        while (!vis[cur]) {
            vis[cur] = 1;
            cyc.push_back(cur);
            cur = D[cur];
        }
        int L = (int)cyc.size();
        if (L > 1) {
            for (int p = L - 1; p >= 1; --p) {
                U.emplace_back(cyc[0], cyc[p]);
            }
        }
    }

    int K = (int)U.size();

    // If K > M, it's impossible with R = M using this construction.
    // Relying on problem guarantee, assume K <= M.
    int R = M;

    // Prepare l_k assignment for k in [0, M-1]
    vector<pair<int,int>> l(M, {-1, -1});
    for (int j = 0; j < K; ++j) {
        int k = M - K + j;
        l[k] = U[j];
    }

    // Prepare to compute s_k = C_k^{-1} l_k C_k, where C_k = t_{M-1}...t_{k+1}
    // Maintain A = C_k^{-1}, B = C_k (inverse of A)
    vector<int> A(N), B(N);
    iota(A.begin(), A.end(), 0);
    iota(B.begin(), B.end(), 0);

    vector<pair<int,int>> ans(M);
    long long sumDist = 0;

    for (int k = M - 1; k >= 0; --k) {
        int u = 0, v = 0;
        if (l[k].first != -1) {
            int a = l[k].first;
            int b = l[k].second;
            u = A[a];
            v = A[b];
            if (u == v) {
                // Shouldn't happen for a != b, but safe-guard
                u = v = 0;
            }
        } else {
            u = v = 0;
        }
        ans[k] = {u, v};
        sumDist += llabs((long long)u - (long long)v);

        // Update A, B for next iteration: A' = t_k ∘ A; B' = C_{k-1} = C_k ∘ t_k
        int x = X[k], y = Y[k];
        int idx1 = B[x], idx2 = B[y];
        if (idx1 != idx2) {
            swap(A[idx1], A[idx2]);
            swap(B[x], B[y]);
        }
    }

    cout << R << "\n";
    for (int i = 0; i < R; ++i) {
        cout << ans[i].first << " " << ans[i].second << "\n";
    }
    long long V = (long long)R * sumDist;
    cout << V << "\n";

    return 0;
}