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

    // Jerry's total permutation J_total
    vector<int> Jperm(N);
    iota(Jperm.begin(), Jperm.end(), 0);
    for (int k = 0; k < M; ++k) {
        cin >> X[k] >> Y[k];
        if (X[k] != Y[k]) swap(Jperm[X[k]], Jperm[Y[k]]);
    }

    // pi0_inv: value -> position in initial array
    vector<int> pi_inv(N);
    for (int i = 0; i < N; ++i) pi_inv[S[i]] = i;

    // Inverse of J_total
    vector<int> Jinv(N);
    for (int i = 0; i < N; ++i) Jinv[Jperm[i]] = i;

    // W = Jinv ∘ pi_inv
    vector<int> W(N);
    for (int i = 0; i < N; ++i) W[i] = Jinv[pi_inv[i]];

    // Decompose W into transpositions
    vector<char> vis(N, 0);
    vector<pair<int,int>> trans;
    trans.reserve(N);
    for (int i = 0; i < N; ++i) {
        if (!vis[i]) {
            int x = i;
            vector<int> cyc;
            while (!vis[x]) {
                vis[x] = 1;
                cyc.push_back(x);
                x = W[x];
            }
            int len = (int)cyc.size();
            if (len > 1) {
                int root = cyc[0];
                for (int t = len - 1; t >= 1; --t) {
                    trans.emplace_back(root, cyc[t]);
                }
            }
        }
    }

    int r = (int)trans.size();
    // It is guaranteed that r <= M (see problem guarantee)

    // C_t sequence (in "global" coordinates after all Jerry moves)
    vector<int> Cc(M), Cd(M);
    for (int t = 0; t < M; ++t) {
        if (t < r) {
            Cc[t] = trans[t].first;
            Cd[t] = trans[t].second;
        } else {
            Cc[t] = 0;
            Cd[t] = 0; // identity
        }
    }

    // Compute P_t from right to left:
    // Maintain suf = Suf_{t+1}, sufInv its inverse.
    vector<int> suf(N), sufInv(N);
    for (int i = 0; i < N; ++i) {
        suf[i] = i;
        sufInv[i] = i;
    }

    vector<int> U(M), V(M);
    for (int t = M - 1; t >= 0; --t) {
        int a = Cc[t];
        int b = Cd[t];
        int u = suf[a];
        int v = suf[b];
        U[t] = u;
        V[t] = v;

        int x = X[t], y = Y[t];
        if (x != y) {
            int px = sufInv[x];
            int py = sufInv[y];
            // Currently suf[px] = x, suf[py] = y
            suf[px] = y;
            suf[py] = x;
            sufInv[x] = py;
            sufInv[y] = px;
        }
    }

    long long R = M;
    long long sumDist = 0;
    for (int t = 0; t < M; ++t) {
        sumDist += llabs((long long)U[t] - (long long)V[t]);
    }
    long long Vtotal = R * sumDist;

    cout << R << '\n';
    for (int t = 0; t < M; ++t) {
        cout << U[t] << ' ' << V[t] << '\n';
    }
    cout << Vtotal << '\n';

    return 0;
}