#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<int> S0(N);
    for (int i = 0; i < N; ++i) cin >> S0[i];

    int M;
    cin >> M;
    vector<pair<int,int>> J(M);
    for (int i = 0; i < M; ++i) {
        cin >> J[i].first >> J[i].second;
    }

    // Step 1: compute final mapping f_M (logical -> physical) after all Jerry swaps
    vector<int> f(N), g(N);
    iota(f.begin(), f.end(), 0);
    iota(g.begin(), g.end(), 0);
    for (int k = 0; k < M; ++k) {
        int x = J[k].first;
        int y = J[k].second;
        if (x == y) continue;
        int jx = g[x];
        int jy = g[y];
        if (jx == jy) continue;
        swap(g[x], g[y]);
        swap(f[jx], f[jy]);
    }
    vector<int> target = f; // desired virtual final array A_M

    // Step 2: compute minimal swap sequence P to transform S0 -> target in virtual space
    vector<int> A = S0;
    vector<int> posA(N);
    for (int i = 0; i < N; ++i) posA[A[i]] = i;

    vector<pair<int,int>> P;
    P.reserve(N);
    for (int i = 0; i < N; ++i) {
        if (A[i] == target[i]) continue;
        int need = target[i];
        int j = posA[need];
        if (j == i) continue; // should not happen if data is consistent
        int val_i = A[i];
        swap(A[i], A[j]);
        posA[val_i] = j;
        posA[need] = i;
        P.emplace_back(i, j);
    }
    int L = (int)P.size();
    if (L > M) {
        // According to problem guarantee this should not happen.
        // Fallback: truncate (will likely be incorrect but avoids UB).
        P.resize(M);
        L = M;
    }

    // Step 3: generate physical swaps for each of M rounds
    vector<pair<int,int>> U(M);
    long long sumDist = 0;

    iota(f.begin(), f.end(), 0);
    iota(g.begin(), g.end(), 0);
    int opIdx = 0;

    for (int k = 0; k < M; ++k) {
        int x = J[k].first;
        int y = J[k].second;
        // Update mapping due to Jerry's swap
        if (x != y) {
            int jx = g[x];
            int jy = g[y];
            if (jx != jy) {
                swap(g[x], g[y]);
                swap(f[jx], f[jy]);
            }
        }
        // Apply next planned virtual swap if any
        if (opIdx < L) {
            int u = P[opIdx].first;
            int v = P[opIdx].second;
            int pu = f[u];
            int pv = f[v];
            U[k] = {pu, pv};
            sumDist += llabs((long long)pu - (long long)pv);
            ++opIdx;
        } else {
            U[k] = {0, 0}; // dummy swap
        }
    }

    long long R = M;
    long long V = R * sumDist;

    cout << R << '\n';
    for (int k = 0; k < M; ++k) {
        cout << U[k].first << ' ' << U[k].second << '\n';
    }
    cout << V << '\n';

    return 0;
}