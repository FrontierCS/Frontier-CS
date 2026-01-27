#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M, H;
    if(!(cin >> N >> M >> H)) return 0;
    vector<int> A(N);
    for(int i=0;i<N;i++) cin >> A[i];
    vector<vector<int>> adj(N);
    for(int i=0;i<M;i++){
        int u,v; cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // read coordinates (unused)
    vector<int> x(N), y(N);
    for(int i=0;i<N;i++) cin >> x[i] >> y[i];

    // Order nodes by descending beauty
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j){
        if (A[i] != A[j]) return A[i] > A[j];
        return i < j;
    });

    vector<int> parent(N, -2);
    vector<int> depth(N, -1);

    deque<int> q;
    for(int s : order){
        if(parent[s] != -2) continue;
        parent[s] = -1;
        depth[s] = 0;
        q.clear();
        q.push_back(s);
        while(!q.empty()){
            int u = q.front(); q.pop_front();
            if(depth[u] == H) continue; // cannot expand further
            // Optionally process neighbors with smaller beauty first
            // but keep it simple: natural order
            for(int v : adj[u]){
                if(parent[v] == -2 && depth[u] + 1 <= H){
                    parent[v] = u;
                    depth[v] = depth[u] + 1;
                    q.push_back(v);
                }
            }
        }
    }

    // Output
    for(int i=0;i<N;i++){
        if(i) cout << ' ';
        // safety: any remaining unvisited should be roots
        if(parent[i] == -2) cout << -1;
        else cout << parent[i];
    }
    cout << '\n';
    return 0;
}