#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];
    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;
    
    auto inb = [&](int r, int c){ return r>=0 && r<n && c>=0 && c<m; };
    if (!inb(sr,sc) || !inb(er,ec) || grid[sr][sc]!='1' || grid[er][ec]!='1') {
        cout << -1 << '\n';
        return 0;
    }
    
    // Check connectivity of blank cells from start
    vector<vector<int>> vis(n, vector<int>(m, 0));
    queue<pair<int,int>> q;
    q.push({sr,sc});
    vis[sr][sc]=1;
    int totalBlank=0, reach=0;
    for (int i=0;i<n;i++) for(int j=0;j<m;j++) if(grid[i][j]=='1') totalBlank++;
    int dr4[4]={-1,1,0,0};
    int dc4[4]={0,0,-1,1};
    while(!q.empty()){
        auto [r,c]=q.front(); q.pop();
        reach++;
        for(int k=0;k<4;k++){
            int nr=r+dr4[k], nc=c+dc4[k];
            if(inb(nr,nc) && !vis[nr][nc] && grid[nr][nc]=='1'){
                vis[nr][nc]=1; q.push({nr,nc});
            }
        }
    }
    if (reach != totalBlank) {
        cout << -1 << '\n';
        return 0;
    }
    
    // Helpers for directions
    vector<char> dirs = {'U','D','L','R'};
    auto step = [&](int r, int c, char mv)->pair<int,int>{
        int nr=r, nc=c;
        if(mv=='U') nr--;
        else if(mv=='D') nr++;
        else if(mv=='L') nc--;
        else if(mv=='R') nc++;
        if(inb(nr,nc) && grid[nr][nc]=='1') return {nr,nc};
        return {r,c};
    };
    auto inv = [&](char mv)->char{
        if(mv=='U') return 'D';
        if(mv=='D') return 'U';
        if(mv=='L') return 'R';
        return 'L';
    };
    
    // Attempt multiple randomized DFS traversals
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    vector<string> centers = {"", "L", "R", "U", "D"};
    
    int maxTrials = 200;
    for (int trial=0; trial<maxTrials; ++trial) {
        // Randomize direction order
        array<int,4> order = {0,1,2,3};
        shuffle(order.begin(), order.end(), rng);
        
        vector<vector<int>> seen(n, vector<int>(m, 0));
        string H;
        function<void(int,int)> dfs = [&](int r, int c){
            seen[r][c]=1;
            for(int idx=0; idx<4; ++idx){
                int k = order[idx];
                int nr=r+dr4[k], nc=c+dc4[k];
                if(inb(nr,nc) && grid[nr][nc]=='1' && !seen[nr][nc]){
                    char mv = (k==0?'U':k==1?'D':k==2?'L':'R');
                    H.push_back(mv);
                    dfs(nr,nc);
                    H.push_back(inv(mv));
                }
            }
        };
        dfs(sr,sc);
        // Ensure all seen
        int cntSeen=0;
        for(int i=0;i<n;i++)for(int j=0;j<m;j++) if(grid[i][j]=='1' && seen[i][j]) cntSeen++;
        if(cntSeen != totalBlank) continue; // shouldn't happen
        
        // Try centers
        for (const string& cstr : centers) {
            string S = H;
            S += cstr;
            string Hr = H;
            reverse(Hr.begin(), Hr.end());
            S += Hr;
            // Simulate S
            int r=sr, c=sc;
            vector<vector<int>> visited(n, vector<int>(m, 0));
            visited[r][c]=1;
            for(char mv : S){
                auto pr = step(r,c,mv);
                r=pr.first; c=pr.second;
                visited[r][c]=1;
            }
            if (r==er && c==ec) {
                // Check all visited
                bool all=true;
                for(int i=0;i<n;i++)for(int j=0;j<m;j++) if(grid[i][j]=='1' && !visited[i][j]) { all=false; break; }
                if (all) {
                    cout << S << '\n';
                    return 0;
                }
            }
        }
    }
    
    cout << -1 << '\n';
    return 0;
}