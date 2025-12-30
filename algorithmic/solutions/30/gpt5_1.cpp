#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> adj;
vector<int> parentArr, depthArr, tin, tout;
int timer_dfs;

void dfs_init(int u, int p){
    parentArr[u] = p;
    tin[u] = ++timer_dfs;
    for(int v: adj[u]){
        if(v == p) continue;
        depthArr[v] = depthArr[u] + 1;
        dfs_init(v, u);
    }
    tout[u] = timer_dfs;
}

inline bool inSub(int x, int y, const vector<int>& tin, const vector<int>& tout){
    return tin[x] <= tin[y] && tin[y] <= tout[x];
}

void dfs_count(int u, int p, const vector<char>& present, vector<int>& scnt){
    int sum = present[u] ? 1 : 0;
    for(int v: adj[u]){
        if(v == p) continue;
        dfs_count(v, u, present, scnt);
        sum += scnt[v];
    }
    scnt[u] = sum;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while(t--){
        cin >> n;
        adj.assign(n+1, {});
        for(int i=0;i<n-1;i++){
            int u,v; cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        parentArr.assign(n+1, 0);
        depthArr.assign(n+1, 0);
        tin.assign(n+1, 0);
        tout.assign(n+1, 0);
        timer_dfs = 0;
        dfs_init(1, 0);
        
        vector<char> present(n+1, false);
        vector<int> Slist;
        for(int i=1;i<=n;i++){ present[i] = true; Slist.push_back(i); }
        int Ssize = n;
        
        auto recompute_Slist = [&](vector<char>& pres, vector<int>& list, int& sz){
            list.clear();
            sz = 0;
            for(int i=1;i<=n;i++){
                if(pres[i]){
                    list.push_back(i);
                    sz++;
                }
            }
        };
        
        while(true){
            if(Ssize == 1){
                int ansNode = -1;
                for(int i=1;i<=n;i++) if(present[i]) { ansNode = i; break; }
                cout << "! " << ansNode << endl;
                cout.flush();
                break;
            }
            // compute subtree counts for all nodes
            vector<int> scnt(n+1, 0);
            dfs_count(1, 0, present, scnt);
            
            // choose best x minimizing max(s1, s0size)
            int bestX = 1;
            int bestVal = INT_MAX;
            vector<int> seen(n+1, 0);
            int token = 1;
            
            for(int x=1;x<=n;x++){
                int s1 = scnt[x];
                // compute s0size: unique parents among outside nodes
                int s0uniq = 0;
                token++;
                for(int y: Slist){
                    if(!(tin[x] <= tin[y] && tin[y] <= tout[x])){
                        int z = (y == 1 ? 1 : parentArr[y]);
                        if(seen[z] != token){
                            seen[z] = token;
                            s0uniq++;
                        }
                    }
                }
                int cur = max(s1, s0uniq);
                if(cur < bestVal){
                    bestVal = cur;
                    bestX = x;
                }
            }
            
            cout << "? " << bestX << endl;
            cout.flush();
            
            int ans;
            if(!(cin >> ans)) return 0;
            if(ans == 1){
                // keep only subtree(bestX)
                for(int i=1;i<=n;i++){
                    if(present[i] && !(tin[bestX] <= tin[i] && tin[i] <= tout[bestX])){
                        present[i] = false;
                    }
                }
                recompute_Slist(present, Slist, Ssize);
            }else{
                // map outside to parents (root stays)
                vector<char> newpresent(n+1, false);
                for(int y: Slist){
                    if(!(tin[bestX] <= tin[y] && tin[y] <= tout[bestX])){
                        int z = (y == 1 ? 1 : parentArr[y]);
                        newpresent[z] = true;
                    }
                }
                present.swap(newpresent);
                recompute_Slist(present, Slist, Ssize);
            }
        }
    }
    return 0;
}