#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1005;
bitset<MAXN> adj[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    for(int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj[u][v] = 1;
        adj[v][u] = 1;
    }
    // compute degrees
    vector<pair<int, int>> order;
    for(int i = 0; i < N; i++) {
        int d = adj[i].count();
        order.emplace_back(-d, i);
    }
    sort(order.begin(), order.end());
    // now order[0] has highest deg (since -d smallest)
    bitset<MAXN> clique;
    int clsize = 0;
    for(auto& p : order) {
        int v = p.second;
        if( (adj[v] & clique).count() == clsize ) {
            clique[v] = 1;
            clsize++;
        }
    }
    for(int i = 0; i < N; i++) {
        cout << clique[i] << '\n';
    }
    return 0;
}