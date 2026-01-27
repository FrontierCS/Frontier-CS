#include <bits/stdc++.h>
using namespace std;

pair<int,int> query(const vector<int>& nodes){
    cout << "? " << nodes.size();
    for(int v : nodes) cout << " " << v;
    cout << endl;
    cout.flush();
    int x, d;
    if(!(cin >> x >> d)) exit(0);
    if(x == -1 && d == -1) exit(0);
    return {x, d};
}

void answer(int a, int b){
    cout << "! " << a << " " << b << endl;
    cout.flush();
    string res;
    if(!(cin >> res)) exit(0);
    if(res != "Correct") exit(0);
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if(!(cin >> T)) return 0;
    while(T--){
        int n;
        cin >> n;
        vector<vector<int>> g(n+1);
        for(int i=0;i<n-1;i++){
            int u,v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        // Initial query with all nodes
        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto [c, D] = query(all); // c is on path(s,f), D = dist(s,f)

        // BFS from c to get depths and layers
        vector<int> distC(n+1, -1);
        queue<int> q;
        q.push(c);
        distC[c] = 0;
        while(!q.empty()){
            int u = q.front(); q.pop();
            for(int w : g[u]){
                if(distC[w] == -1){
                    distC[w] = distC[u] + 1;
                    q.push(w);
                }
            }
        }
        int maxDepth = 0;
        for(int i=1;i<=n;i++) maxDepth = max(maxDepth, distC[i]);
        vector<vector<int>> layers(maxDepth+1);
        for(int i=1;i<=n;i++){
            layers[distC[i]].push_back(i);
        }

        // Binary search the farthest level along the path where sum == D
        int low = 0, high = maxDepth;
        while(low < high){
            int mid = (low + high + 1) / 2;
            auto [xmid, dsum] = query(layers[mid]);
            if(dsum == D) low = mid;
            else high = mid - 1;
        }

        // Get one endpoint u at depth 'low' (it must be on the path)
        auto [u, dsum_u] = query(layers[low]); // dsum_u should be D

        // BFS from u to get nodes at distance D
        vector<int> distU(n+1, -1);
        queue<int> qu;
        qu.push(u);
        distU[u] = 0;
        while(!qu.empty()){
            int v = qu.front(); qu.pop();
            for(int w : g[v]){
                if(distU[w] == -1){
                    distU[w] = distU[v] + 1;
                    qu.push(w);
                }
            }
        }
        vector<int> cand;
        for(int i=1;i<=n;i++){
            if(distU[i] == D) cand.push_back(i);
        }

        auto [v, dsum_v] = query(cand); // v should be the other endpoint
        answer(u, v);
    }
    return 0;
}