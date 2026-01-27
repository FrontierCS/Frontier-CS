#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    vector<vector<char>> adj(N+1, vector<char>(N+1, 0));
    vector<int> deg(N+1, 0);
    for(int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if(!adj[u][v]) {
            adj[u][v] = adj[v][u] = 1;
            deg[u]++;
            deg[v]++;
        }
    }
    vector<int> order(N);
    iota(order.begin(), order.end(), 1);
    sort(order.begin(), order.end(), [&](int a, int b){
        return deg[a] < deg[b];
    });
    vector<int> color(N+1, 0);
    for(int i = 0; i < N; i++) {
        int v = order[i];
        vector<char> forbidden(N+1, 0);
        for(int w = 1; w <= N; w++) {
            if(color[w] != 0 && !adj[v][w]) {
                forbidden[color[w]] = 1;
            }
        }
        int c = 1;
        while(forbidden[c]) c++;
        color[v] = c;
    }
    for(int i = 1; i <= N; i++) {
        cout << color[i] << endl;
    }
    return 0;
}