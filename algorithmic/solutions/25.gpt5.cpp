#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if(!(cin >> T)) return 0;
    for(int tc = 0; tc < T; ++tc) {
        int n;
        if(!(cin >> n)) return 0;
        string dummy;
        getline(cin, dummy); // consume endline

        vector<string> mat;
        mat.reserve(n);
        while ((int)mat.size() < n) {
            string line;
            if(!getline(cin, line)) break;
            string s;
            for(char c : line) if(c == '0' || c == '1') s.push_back(c);
            if((int)s.size() == n) mat.push_back(s);
        }

        // If not enough lines read, assume empty graph
        if((int)mat.size() != n) {
            cout << "! " << (n <= 1 ? 1 : 0) << "\n";
            continue;
        }

        vector<vector<int>> adj(n);
        for(int i = 0; i < n; ++i) {
            for(int j = 0; j < n; ++j) {
                if(mat[i][j] == '1') adj[i].push_back(j);
            }
        }

        vector<int> vis(n, 0);
        queue<int> q;
        if(n > 0) {
            vis[0] = 1;
            q.push(0);
        }
        while(!q.empty()) {
            int u = q.front(); q.pop();
            for(int v : adj[u]) {
                if(!vis[v]) {
                    vis[v] = 1;
                    q.push(v);
                }
            }
        }

        bool connected = true;
        for(int i = 0; i < n; ++i) if(!vis[i]) { connected = false; break; }
        cout << "! " << (connected ? 1 : 0) << "\n";
    }
    return 0;
}