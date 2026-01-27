#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    vector<pair<int,int>> moves = {
        {2,1},{1,2},{-1,2},{-2,1},{-2,-1},{-1,-2},{1,-2},{2,-1}
    };

    auto inside = [&](int r, int c){ return r>=0 && r<N && c>=0 && c<N; };

    vector<vector<char>> vis(N, vector<char>(N, 0));
    vector<vector<int>> deg(N, vector<int>(N, 0));
    for (int r=0;r<N;r++){
        for (int c=0;c<N;c++){
            int d=0;
            for (auto [dr,dc]: moves){
                int nr=r+dr, nc=c+dc;
                if (inside(nr,nc)) d++;
            }
            deg[r][c]=d;
        }
    }

    vector<pair<int,int>> path;
    path.reserve((size_t)N*N);
    int cr=r0, cc=c0;
    vis[cr][cc]=1;
    path.emplace_back(cr,cc);
    // decrement neighbors of start
    for (auto [dr,dc]: moves){
        int nr=cr+dr, nc=cc+dc;
        if (inside(nr,nc) && !vis[nr][nc]) deg[nr][nc]--;
    }

    for (long long step=1; step < 1LL*N*N; ++step){
        int best_r=-1, best_c=-1;
        int best_deg=INT_MAX;
        int best_tie=INT_MAX;

        for (auto [dr,dc]: moves){
            int nr=cr+dr, nc=cc+dc;
            if (!inside(nr,nc) || vis[nr][nc]) continue;
            int d = deg[nr][nc];

            // second tie-breaker: minimal degree among next-next moves
            int min_next = INT_MAX;
            for (auto [dr2,dc2]: moves){
                int rr=nr+dr2, cc2=nc+dc2;
                if (!inside(rr,cc2) || vis[rr][cc2]) continue;
                min_next = min(min_next, deg[rr][cc2]);
            }
            if (min_next==INT_MAX) min_next = -1; // dead-end (no onward moves)

            if (d < best_deg || (d==best_deg && min_next < best_tie)){
                best_deg = d;
                best_tie = min_next;
                best_r = nr;
                best_c = nc;
            }
        }

        if (best_r==-1) break; // stuck
        cr = best_r; cc = best_c;
        vis[cr][cc]=1;
        path.emplace_back(cr,cc);
        for (auto [dr,dc]: moves){
            int nr=cr+dr, nc=cc+dc;
            if (inside(nr,nc) && !vis[nr][nc]) deg[nr][nc]--;
        }
    }

    cout << path.size() << '\n';
    for (size_t i=0;i<path.size();++i){
        cout << (path[i].first+1) << ' ' << (path[i].second+1);
        if (i+1<path.size()) cout << '\n';
    }
    return 0;
}