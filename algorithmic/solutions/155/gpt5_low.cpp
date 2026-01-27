#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj, ti, tj;
    double p;
    if(!(cin >> si >> sj >> ti >> tj >> p)) return 0;
    vector<string> h(20), v(19);
    for (int i = 0; i < 20; ++i) cin >> h[i];
    for (int i = 0; i < 19; ++i) cin >> v[i];

    auto inb = [&](int x, int y){ return 0<=x && x<20 && 0<=y && y<20; };

    const int dx[4] = {-1,1,0,0};
    const int dy[4] = {0,0,-1,1};
    const char dc[4] = {'U','D','L','R'};

    auto canMove = [&](int x, int y, int dir)->bool{
        int nx = x + dx[dir], ny = y + dy[dir];
        if (!inb(nx, ny)) return false;
        if (dir==3) { // R
            return h[x][y]=='0';
        } else if (dir==2) { // L
            return h[x][y-1]=='0';
        } else if (dir==1) { // D
            return v[x][y]=='0';
        } else { // U
            return v[x-1][y]=='0';
        }
    };

    vector<vector<int>> dist(20, vector<int>(20, -1));
    vector<vector<pair<int,int>>> prev(20, vector<pair<int,int>>(20, {-1,-1}));
    vector<vector<char>> pmv(20, vector<char>(20, '?'));
    queue<pair<int,int>> q;
    dist[si][sj]=0;
    q.push({si,sj});
    while(!q.empty()){
        auto [x,y]=q.front(); q.pop();
        if (x==ti && y==tj) break;
        for(int d=0; d<4; ++d){
            if (!inb(x+dx[d], y+dy[d])) continue;
            if (!canMove(x,y,d)) continue;
            int nx=x+dx[d], ny=y+dy[d];
            if (dist[nx][ny]==-1){
                dist[nx][ny]=dist[x][y]+1;
                prev[nx][ny]={x,y};
                pmv[nx][ny]=dc[d];
                q.push({nx,ny});
            }
        }
    }

    string path;
    if (dist[ti][tj] != -1){
        int cx=ti, cy=tj;
        while(!(cx==si && cy==sj)){
            path.push_back(pmv[cx][cy]);
            tie(cx,cy)=prev[cx][cy];
        }
        reverse(path.begin(), path.end());
    }
    // Fallback: if somehow not reachable (shouldn't happen), just output empty or simple moves
    if (path.empty()) {
        cout << "\n";
        return 0;
    }

    int k = (int)ceil(1.0 / max(1e-9, (1.0 - p)));
    if (k > 2) k = 2; // p <= 0.5 guarantees k <= 2, but clamp anyway
    if ((int)path.size() * k > 200) k = 1;

    string out;
    out.reserve(min(200, (int)path.size()*k));
    for(char c: path){
        for(int rep=0; rep<k; ++rep){
            if ((int)out.size() < 200) out.push_back(c);
        }
        if ((int)out.size() >= 200) break;
    }
    if (out.empty()) {
        // ensure non-empty valid output
        out = string(1, path[0]);
    }
    cout << out << "\n";
    return 0;
}