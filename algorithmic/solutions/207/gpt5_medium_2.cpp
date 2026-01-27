#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if(!(cin >> N)) return 0;
    vector<int> S(N);
    for (int i = 0; i < N; ++i) cin >> S[i];
    int M;
    cin >> M;
    vector<int> X(M), Y(M);
    for (int i = 0; i < M; ++i) {
        cin >> X[i] >> Y[i];
    }

    // Apply all Jerry swaps to get final state after Jerry's moves
    vector<int> A = S;
    for (int i = 0; i < M; ++i) {
        swap(A[X[i]], A[Y[i]]);
    }

    // Compute sequence of swaps D to sort A to identity
    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[A[i]] = i;
    vector<pair<int,int>> D;
    for (int i = 0; i < N; ++i) {
        while (A[i] != i) {
            int j = pos[i];
            D.emplace_back(i, j);
            // perform swap in A
            int vi = A[i], vj = A[j];
            swap(A[i], A[j]);
            pos[vi] = j;
            pos[vj] = i;
        }
    }
    int K = (int)D.size();
    // It is guaranteed that K <= M for valid instances
    
    // Prepare our moves using conjugation
    vector<pair<int,int>> ans(M, {0,0});
    vector<int> mp(N);
    iota(mp.begin(), mp.end(), 0); // mp represents J_post^{-1}
    long long sumDist = 0;
    for (int i = 0; i < M; ++i) {
        int idx = M - 1 - i; // current round index from the end
        if (i < K) {
            auto pr = D[K - 1 - i]; // reverse order for correct composition
            int u = mp[pr.first];
            int v = mp[pr.second];
            ans[idx] = {u, v};
            sumDist += llabs((long long)u - (long long)v);
        } else {
            ans[idx] = {0, 0}; // identity
        }
        // Update mp by composing with J[idx] on the right: mp' = mp ∘ J[idx]
        swap(mp[X[idx]], mp[Y[idx]]);
    }

    long long R = M;
    long long V = R * sumDist;

    cout << R << "\n";
    for (int i = 0; i < M; ++i) {
        cout << ans[i].first << " " << ans[i].second << "\n";
    }
    cout << V << "\n";
    return 0;
}