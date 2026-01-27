#include <bits/stdc++.h>
using namespace std;

pair<int,int> bfs_far(int n, const vector<vector<int>>& g, int src) {
    vector<int> dist(n+1, -1), par(n+1, -1);
    queue<int> q;
    dist[src]=0; q.push(src);
    int last=src;
    while(!q.empty()){
        int u=q.front(); q.pop();
        last=u;
        for(int v:g[u]){
            if(dist[v]==-1){
                dist[v]=dist[u]+1;
                par[v]=u;
                q.push(v);
            }
        }
    }
    return {last, dist[last]};
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin>>t)) return 0;
    while(t--){
        int n; 
        cin>>n;
        vector<vector<int>> g(n+1);
        for(int i=0;i<n-1;i++){
            int u,v; cin>>u>>v;
            g[u].push_back(v);
            g[v].push_back(u);
        }
        int s = bfs_far(n, g, 1).first;
        int f = bfs_far(n, g, s).first;
        cout << s << " " << f << "\n";
    }
    return 0;
}