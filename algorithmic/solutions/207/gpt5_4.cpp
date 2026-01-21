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
    vector<int> invJ(N);
    iota(invJ.begin(), invJ.end(), 0);
    for(int i = 0; i < M; ++i){
        int x, y;
        cin >> x >> y;
        swap(invJ[x], invJ[y]);
    }
    
    // W = pi ∘ invJ, where pi(i) = S[i]
    vector<int> W(N);
    for(int i = 0; i < N; ++i){
        W[i] = S[invJ[i]];
    }
    
    // Decompose W into transpositions (minimum number) using star decomposition per cycle.
    vector<char> vis(N, 0);
    vector<pair<int,int>> moves;
    moves.reserve(N);
    long long sumCost = 0;
    
    for(int i = 0; i < N; ++i){
        if(vis[i]) continue;
        int cur = i;
        vector<int> cyc;
        while(!vis[cur]){
            vis[cur] = 1;
            cyc.push_back(cur);
            cur = W[cur];
        }
        if((int)cyc.size() <= 1) continue;
        // Choose anchor as median to minimize sum of distances
        vector<int> sorted = cyc;
        sort(sorted.begin(), sorted.end());
        int anchor = sorted[sorted.size()/2];
        int pos = 0;
        for(int j = 0; j < (int)cyc.size(); ++j){
            if(cyc[j] == anchor){ pos = j; break; }
        }
        int L = cyc.size();
        for(int j = 1; j < L; ++j){
            int v = cyc[(pos + j) % L];
            moves.emplace_back(anchor, v);
            sumCost += llabs((long long)anchor - (long long)v);
        }
    }
    
    int R = M;
    cout << R << '\n';
    int t = (int)moves.size();
    for(int i = 0; i < t; ++i){
        cout << moves[i].first << ' ' << moves[i].second << '\n';
    }
    for(int i = t; i < M; ++i){
        cout << 0 << ' ' << 0 << '\n';
    }
    long long V = (long long)R * sumCost;
    cout << V << '\n';
    return 0;
}