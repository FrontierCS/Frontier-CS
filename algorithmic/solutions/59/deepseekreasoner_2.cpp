#include <bits/stdc++.h>
using namespace std;

int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    char c;
    cin >> c;
    return c == '<' ? -1 : 1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    cin >> n;
    
    vector<vector<int>> adj(n+1, vector<int>(n+1, 0));
    
    // ask all adjacent comparisons
    for (int i = 1; i < n; i++) {
        int res = ask(i, i+1);
        if (res == -1) {
            adj[i][i+1] = -1;
            adj[i+1][i] = 1;
        } else {
            adj[i][i+1] = 1;
            adj[i+1][i] = -1;
        }
    }
    
    // ask i,i+2 for odd i
    for (int i = 1; i+2 <= n; i += 2) {
        int res = ask(i, i+2);
        if (res == -1) {
            adj[i][i+2] = -1;
            adj[i+2][i] = 1;
        } else {
            adj[i][i+2] = 1;
            adj[i+2][i] = -1;
        }
    }
    
    // topological sort
    vector<int> indeg(n+1, 0);
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            if (adj[i][j] == -1) {
                indeg[j]++;
            }
        }
    }
    
    priority_queue<int, vector<int>, greater<int>> pq;
    for (int i = 1; i <= n; i++) {
        if (indeg[i] == 0) {
            pq.push(i);
        }
    }
    
    vector<int> order;
    while (!pq.empty()) {
        int u = pq.top(); pq.pop();
        order.push_back(u);
        for (int v = 1; v <= n; v++) {
            if (adj[u][v] == -1) {
                indeg[v]--;
                if (indeg[v] == 0) {
                    pq.push(v);
                }
            }
        }
    }
    
    vector<int> ans(n+1);
    for (int i = 0; i < n; i++) {
        ans[order[i]] = i+1;
    }
    
    cout << "!";
    for (int i = 1; i <= n; i++) {
        cout << " " << ans[i];
    }
    cout << endl;
    
    return 0;
}