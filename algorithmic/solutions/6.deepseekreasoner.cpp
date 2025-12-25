#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    if (N == 1) {
        return {{1}};
    }
    
    vector<vector<int>> adj(N+1);
    for (int i = 0; i < M; i++) {
        adj[A[i]].push_back(B[i]);
        adj[B[i]].push_back(A[i]);
    }
    
    vector<int> deg(N+1, 0);
    for (int i = 1; i <= N; i++) {
        deg[i] = adj[i].size();
    }
    
    vector<int> odds;
    for (int i = 1; i <= N; i++) {
        if (deg[i] % 2 == 1) {
            odds.push_back(i);
        }
    }
    
    vector<map<int, int>> multiaj(N+1);
    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        multiaj[u][v]++;
        multiaj[v][u]++;
    }
    
    if (!odds.empty()) {
        for (size_t i = 0; i < odds.size(); i += 2) {
            int u = odds[i], v = odds[i+1];
            vector<int> parent(N+1, -1);
            queue<int> q;
            q.push(u);
            parent[u] = u;
            while (!q.empty()) {
                int cur = q.front(); q.pop();
                if (cur == v) break;
                for (int nxt : adj[cur]) {
                    if (parent[nxt] == -1) {
                        parent[nxt] = cur;
                        q.push(nxt);
                    }
                }
            }
            vector<int> path;
            int cur = v;
            while (cur != u) {
                path.push_back(cur);
                cur