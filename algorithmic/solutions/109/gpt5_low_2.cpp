#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if(!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0; // 0-index
    
    vector<vector<char>> vis(N, vector<char>(N, 0));
    
    // Knight moves
    const int dx[8] = {2,2,1,1,-1,-1,-2,-2};
    const int dy[8] = {1,-1,2,-2,2,-2,1,-1};
    
    auto inb = [&](int r, int c){ return r>=0 && r<N && c>=0 && c<N; };
    
    // Precompute static degrees (optional, for tie-break)
    vector<vector<int>> deg(N, vector<int>(N, 0));
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            int cnt=0;
            for(int k=0;k<8;k++){
                int ni=i+dx[k], nj=j+dy[k];
                if(inb(ni,nj)) cnt++;
            }
            deg[i][j]=cnt;
        }
    }
    
    vector<pair<int,int>> path;
    path.reserve(1LL*N*N);
    int cr=r0, cc=c0;
    vis[cr][cc]=1;
    path.emplace_back(cr,cc);
    
    auto onward_unvisited = [&](int r, int c)->int{
        int cnt=0;
        for(int k=0;k<8;k++){
            int nr=r+dx[k], nc=c+dy[k];
            if(inb(nr,nc) && !vis[nr][nc]) cnt++;
        }
        return cnt;
    };
    
    for(;;){
        int best_k = -1;
        int best_onward = INT_MAX;
        int best_static_deg = INT_MAX;
        // small heuristic: iterate move order shuffled by preference to keep deterministic
        for(int k=0;k<8;k++){
            int nr = cr + dx[k], nc = cc + dy[k];
            if(!inb(nr,nc) || vis[nr][nc]) continue;
            int ow = onward_unvisited(nr,nc);
            if(ow < best_onward || (ow == best_onward && deg[nr][nc] < best_static_deg)){
                best_onward = ow;
                best_static_deg = deg[nr][nc];
                best_k = k;
            }
        }
        if(best_k == -1) break; // no moves
        cr += dx[best_k];
        cc += dy[best_k];
        vis[cr][cc]=1;
        path.emplace_back(cr,cc);
        if((int)path.size() == N*1LL*N) break;
    }
    
    cout << path.size() << "\n";
    for(size_t i=0;i<path.size();++i){
        cout << (path[i].first+1) << " " << (path[i].second+1);
        if(i+1<path.size()) cout << "\n";
    }
    return 0;
}