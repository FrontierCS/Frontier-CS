#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, si, sj;
    if(!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for(int i=0;i<N;i++) cin >> grid[i];

    auto idx = [&](int i, int j){ return i*N + j; };
    auto inb = [&](int i, int j){ return 0<=i && i<N && 0<=j && j<N; };

    int V = N*N;
    vector<bool> isRoad(V,false);
    for(int i=0;i<N;i++) for(int j=0;j<N;j++) if(grid[i][j] != '#') isRoad[idx(i,j)] = true;

    vector<vector<int>> adj(V);
    vector<vector<char>> adjDir(V);
    const int di[4] = {-1,1,0,0};
    const int dj[4] = {0,0,-1,1};
    const char dc[4] = {'U','D','L','R'};

    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            if(!isRoad[idx(i,j)]) continue;
            int u = idx(i,j);
            for(int k=0;k<4;k++){
                int ni=i+di[k], nj=j+dj[k];
                if(inb(ni,nj) && isRoad[idx(ni,nj)]){
                    adj[u].push_back(idx(ni,nj));
                    adjDir[u].push_back(dc[k]);
                }
            }
        }
    }

    int s = idx(si,sj);
    vector<char> moveToParent(V, 0);
    vector<int> parent(V, -1);
    vector<char> iterBuilt; // not used
    vector<size_t> it(V, 0);
    vector<bool> vis(V, false);
    string ans;
    vector<int> st;
    st.push_back(s);
    vis[s] = true;
    parent[s] = -1;

    auto rev = [&](char c)->char{
        if(c=='U') return 'D';
        if(c=='D') return 'U';
        if(c=='L') return 'R';
        if(c=='R') return 'L';
        return '?';
    };

    while(!st.empty()){
        int u = st.back();
        if(it[u] < adj[u].size()){
            int v = adj[u][it[u]];
            char d = adjDir[u][it[u]];
            it[u]++;
            if(!vis[v]){
                vis[v] = true;
                parent[v] = u;
                moveToParent[v] = d;
                ans.push_back(d);
                st.push_back(v);
            }
        }else{
            st.pop_back();
            if(!st.empty()){
                int p = st.back();
                // u -> p backtrack: reverse of moveToParent[u]
                ans.push_back(rev(moveToParent[u]));
            }
        }
    }

    cout << ans << "\n";
    return 0;
}