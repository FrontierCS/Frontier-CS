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
    vector<pair<int,int>> j(M);
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        j[i] = {x, y};
    }
    
    // Apply all Jerry swaps to get final array after all Jerry moves
    vector<int> B = S;
    for (int k = 0; k < M; ++k) {
        int x = j[k].first, y = j[k].second;
        swap(B[x], B[y]);
    }
    
    // Generate minimal swaps to sort B into identity
    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[B[i]] = i;
    vector<pair<int,int>> W;
    for (int i = 0; i < N; ++i) {
        while (B[i] != i) {
            int jpos = pos[i];
            W.emplace_back(i, jpos);
            int vi = B[i], vj = B[jpos];
            swap(B[i], B[jpos]);
            pos[vi] = jpos;
            pos[vj] = i;
        }
    }
    int K = (int)W.size();
    
    // Plan to use all M rounds, schedule W in the last K rounds
    int R = M;
    vector<pair<int,int>> ans(M, {0,0});
    
    // Maintain suffix permutation J_{>t} = g(t+1)
    // cur[i] = g(current_k+1)(i), invCur is inverse
    vector<int> cur(N), invCur(N);
    iota(cur.begin(), cur.end(), 0);
    iota(invCur.begin(), invCur.end(), 0);
    
    for (int k = M - 1; k >= 0; --k) {
        if (k >= M - K) {
            int idx = k - (M - K);
            int a = W[idx].first;
            int b = W[idx].second;
            int u = invCur[a];
            int v = invCur[b];
            ans[k] = {u, v};
        }
        // Update cur and invCur to g(k) = g(k+1) ∘ swap_k
        int x = j[k].first, y = j[k].second;
        int ax = cur[x], ay = cur[y];
        swap(cur[x], cur[y]);
        swap(invCur[ax], invCur[ay]);
    }
    
    // Compute total cost
    long long sumDist = 0;
    for (int k = 0; k < R; ++k) {
        long long u = ans[k].first;
        long long v = ans[k].second;
        sumDist += llabs(u - v);
    }
    long long V = (long long)R * sumDist;
    
    // Output
    cout << R << '\n';
    for (int k = 0; k < R; ++k) {
        cout << ans[k].first << ' ' << ans[k].second << '\n';
    }
    cout << V << '\n';
    
    return 0;
}