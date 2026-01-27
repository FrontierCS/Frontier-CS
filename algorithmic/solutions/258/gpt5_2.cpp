#include <bits/stdc++.h>
using namespace std;

pair<int,int> ask(const vector<int>& nodes){
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

vector<int> bfs(int n, const vector<vector<int>>& g, int s){
    vector<int> d(n+1, -1);
    queue<int> q;
    d[s] = 0;
    q.push(s);
    while(!q.empty()){
        int v = q.front(); q.pop();
        for(int to : g[v]){
            if(d[to] == -1){
                d[to] = d[v] + 1;
                q.push(to);
            }
        }
    }
    return d;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if(!(cin >> t)) return 0;
    while(t--){
        int n;
        cin >> n;
        vector<vector<int>> g(n+1);
        for(int i=0;i<n-1;i++){
            int u,v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }
        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto init = ask(all);
        int root = init.first;
        int D = init.second;

        auto distRoot = bfs(n, g, root);
        int maxDepth = 0;
        for(int i=1;i<=n;i++) maxDepth = max(maxDepth, distRoot[i]);

        int low = -1, high = maxDepth;
        while(high - low > 1){
            int mid = (low + high) / 2;
            vector<int> S;
            S.reserve(n);
            for(int i=1;i<=n;i++) if(distRoot[i] > mid) S.push_back(i);
            if(S.empty()){
                high = mid;
                continue;
            }
            auto res = ask(S);
            if(res.second == D) low = mid;
            else high = mid;
        }
        int rMax = high;

        vector<int> layer;
        for(int i=1;i<=n;i++) if(distRoot[i] == rMax) layer.push_back(i);
        auto firstEnd = ask(layer);
        int e1 = firstEnd.first;

        auto distE1 = bfs(n, g, e1);
        vector<int> atD;
        for(int i=1;i<=n;i++) if(distE1[i] == D) atD.push_back(i);
        auto secondEnd = ask(atD);
        int e2 = secondEnd.first;

        answer(e1, e2);
    }
    return 0;
}