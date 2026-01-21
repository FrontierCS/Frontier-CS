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
    for (int i = 0; i < M; ++i) {
        cin >> X[i] >> Y[i];
    }

    // Compute inverse of initial permutation S
    vector<int> invS(N);
    for (int i = 0; i < N; ++i) {
        invS[S[i]] = i;
    }

    // Compute P_Jtotal = J0 ∘ J1 ∘ ... ∘ J_{M-1}
    vector<int> pJ(N);
    iota(pJ.begin(), pJ.end(), 0);
    for (int k = 0; k < M; ++k) {
        int a = X[k], b = Y[k];
        if (a != b) swap(pJ[a], pJ[b]);
    }

    // Inverse of P_Jtotal
    vector<int> invPJ(N);
    for (int i = 0; i < N; ++i) {
        invPJ[pJ[i]] = i;
    }

    // Q_target = P_Jtotal^{-1} ∘ S^{-1}
    vector<int> Q(N);
    for (int i = 0; i < N; ++i) {
        Q[i] = invPJ[invS[i]];
    }

    // Decompose Q into transpositions
    vector<char> used(N, 0);
    vector<pair<int,int>> trans;
    trans.reserve(N);
    for (int i = 0; i < N; ++i) {
        if (used[i]) continue;
        int cur = i;
        vector<int> cyc;
        while (!used[cur]) {
            used[cur] = 1;
            cyc.push_back(cur);
            cur = Q[cur];
        }
        if (cyc.size() <= 1) continue;
        int a0 = cyc[0];
        for (int j = (int)cyc.size() - 1; j >= 1; --j) {
            trans.emplace_back(a0, cyc[j]);
        }
    }

    // Build C_i sequence (c_i in analysis), length M
    vector<int> C1(M, 0), C2(M, 0);
    int Lc = (int)trans.size();
    if (Lc > M) Lc = M; // Should not happen for valid inputs
    for (int i = 0; i < Lc; ++i) {
        C1[i] = trans[i].first;
        C2[i] = trans[i].second;
    }
    // Remaining C's already identity (0,0)

    // Compute U_i from C_i using suffix permutations of Jerry's swaps
    vector<int> U1(M), U2(M);
    vector<int> p(N), pinv(N);
    iota(p.begin(), p.end(), 0);
    iota(pinv.begin(), pinv.end(), 0);

    for (int i = M - 1; i >= 0; --i) {
        int a = C1[i];
        int b = C2[i];
        int ua = p[a];
        int ub = p[b];
        U1[i] = ua;
        U2[i] = ub;

        int x = X[i], y = Y[i];
        if (x != y) {
            int dx = pinv[x];
            int dy = pinv[y];
            if (dx != dy) {
                swap(p[dx], p[dy]);
                swap(pinv[x], pinv[y]);
            }
        }
    }

    // Compute total distance cost
    long long sumDist = 0;
    for (int i = 0; i < M; ++i) {
        sumDist += llabs((long long)U1[i] - (long long)U2[i]);
    }
    long long R = M;
    long long V = R * sumDist;

    // Output
    cout << R << '\n';
    for (int i = 0; i < M; ++i) {
        cout << U1[i] << ' ' << U2[i] << '\n';
    }
    cout << V << '\n';

    return 0;
}