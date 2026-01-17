#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    cin >> n;
    
    // comp[i][j] = 1 if a_i < a_j, 0 if a_i > a_j (only for queried pairs)
    vector<vector<int>> comp(n+1, vector<int>(n+1, -1));
    
    auto ask = [&](int i, int j) -> bool {
        cout << "? " << i << " " << j << endl;
        char c;
        cin >> c;
        if (c == '<') {
            comp[i][j] = 1;
            comp[j][i] = 0;
            return true;
        } else {
            comp[i][j] = 0;
            comp[j][i] = 1;
            return false;
        }
    };
    
    // Ask all adjacent comparisons
    for (int i = 1; i < n; ++i) {
        ask(i, i+1);
    }
    
    // Ask i,i+2 for odd i
    for (int i = 1; i + 2 <= n; i += 2) {
        ask(i, i+2);
    }
    
    // Build graph: edge i -> j means a_i < a_j
    vector<vector<int>> adj(n+1);
    vector<int> indeg(n+1, 0);
    for (int i = 1; i <= n; ++i) {
        for (int j = i+1; j <= n; ++j) {
            if (comp[i][j] != -1) {
                if (comp[i][j] == 1) { // a_i < a_j
                    adj[i].push_back(j);
                    indeg[j]++;
                } else { // a_i > a_j
                    adj[j].push_back(i);
                    indeg[i]++;
                }
            }
        }
    }
    
    // Topological sort with min-heap of indices (smallest index first)
    priority_queue<int, vector<int>, greater<int>> pq;
    for (int i = 1; i <= n; ++i) {
        if (indeg[i] == 0) {
            pq.push(i);
        }
    }
    
    vector<int> ans(n+1);
    int cur = 1;
    while (!pq.empty()) {
        int u = pq.top();
        pq.pop();
        ans[u] = cur++;
        for (int v : adj[u]) {
            indeg[v]--;
            if (indeg[v] == 0) {
                pq.push(v);
            }
        }
    }
    
    // Output answer
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;
    
    return 0;
}