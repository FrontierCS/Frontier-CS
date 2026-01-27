#include <bits/stdc++.h>
using namespace std;

struct Base {
    int x, y;
    long long g, c; // supplies
    long long d, v; // for red: defense, value; for blue, d/v unused
    bool destroyed = false; // only for red
};

struct Fighter {
    int x, y;
    int G, C;
    int fuel = 0, missiles = 0;
    int target = -1; // red base id
    vector<pair<int,int>> path; // planned path to adjacency
    int path_idx = 0;
};

int n, m;
vector<string> grid;

int Bn; // number of blue bases
vector<Base> blueBases;
map<pair<int,int>, int> blueBaseIdAt;

int Rn; // number of red bases
vector<Base> redBases;
map<pair<int,int>, int> redBaseIdAt;

int k;
vector<Fighter> fighters;

bool inb(int x, int y){ return x>=0 && x<n && y>=0 && y<m; }

vector<pair<int,int>> reconstructPath(pair<int,int> start, pair<int,int> goal, const vector<vector<pair<int,int>>>& prev) {
    vector<pair<int,int>> path;
    if (goal == make_pair(-1,-1)) return path;
    pair<int,int> cur = goal;
    while (!(cur == start)) {
        path.push_back(cur);
        auto p = prev[cur.first][cur.second];
        if (p.first == -2) { path.clear(); return path; }
        cur = p;
    }
    reverse(path.begin(), path.end());
    return path;
}

// BFS to a specific goal, avoiding alive red base cells
vector<pair<int,int>> bfs_path(pair<int,int> start, pair<int,int> goal, const vector<vector<bool>>& blocked) {
    if (start == goal) return {};
    vector<vector<int>> dist(n, vector<int>(m, -1));
    vector<vector<pair<int,int>>> prev(n, vector<pair<int,int>>(m, {-2,-2}));
    queue<pair<int,int>> q;
    q.push(start);
    dist[start.first][start.second]=0;
    prev[start.first][start.second] = start;
    int dx[4]={-1,1,0,0}, dy[4]={0,0,-1,1};
    while(!q.empty()){
        auto [x,y]=q.front(); q.pop();
        for(int dir=0;dir<4;dir++){
            int nx=x+dx[dir], ny=y+dy[dir];
            if(!inb(nx,ny)) continue;
            if(blocked[nx][ny]) continue;
            if(dist[nx][ny]!=-1) continue;
            dist[nx][ny]=dist[x][y]+1;
            prev[nx][ny]={x,y};
            if (nx==goal.first && ny==goal.second) {
                return reconstructPath(start, goal, prev);
            }
            q.push({nx,ny});
        }
    }
    return {}; // empty means no path or already at goal (handled above)
}

// Choose nearest target red base and approach cell, returning path
bool choose_target_and_path(Fighter &f, vector<vector<bool>>& blocked) {
    // compute distance BFS from fighter position to all cells
    vector<vector<int>> dist(n, vector<int>(m, -1));
    vector<vector<pair<int,int>>> prev(n, vector<pair<int,int>> (m, {-2,-2}));
    queue<pair<int,int>> q;
    q.push({f.x, f.y});
    dist[f.x][f.y]=0;
    prev[f.x][f.y]={f.x,f.y};
    int dx[4]={-1,1,0,0}, dy[4]={0,0,-1,1};
    while(!q.empty()){
        auto [x,y]=q.front(); q.pop();
        for(int dir=0;dir<4;dir++){
            int nx=x+dx[dir], ny=y+dy[dir];
            if(!inb(nx,ny)) continue;
            if(blocked[nx][ny]) continue;
            if(dist[nx][ny]!=-1) continue;
            dist[nx][ny]=dist[x][y]+1;
            prev[nx][ny]={x,y};
            q.push({nx,ny});
        }
    }
    int bestBase=-1;
    pair<int,int> bestCell={-1,-1};
    int bestDist=INT_MAX;
    for(int i=0;i<Rn;i++){
        if(redBases[i].destroyed) continue;
        int rx=redBases[i].x, ry=redBases[i].y;
        for(int dir=0;dir<4;dir++){
            int ax=rx+dx[dir], ay=ry+dy[dir];
            if(!inb(ax,ay)) continue;
            if(dist[ax][ay]==-1) continue;
            if(dist[ax][ay]<bestDist){
                bestDist=dist[ax][ay];
                bestBase=i;
                bestCell={ax,ay};
            }
        }
    }
    if(bestBase==-1) {
        f.target=-1;
        f.path.clear();
        f.path_idx=0;
        return false;
    }
    f.target=bestBase;
    f.path = reconstructPath({f.x,f.y}, bestCell, prev);
    f.path_idx=0;
    return true;
}

int dir_from_to(int x1,int y1,int x2,int y2){
    if(x2==x1-1 && y2==y1) return 0;
    if(x2==x1+1 && y2==y1) return 1;
    if(x2==x1 && y2==y1-1) return 2;
    if(x2==x1 && y2==y1+1) return 3;
    return -1;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if(!(cin>>n>>m)) return 0;
    grid.resize(n);
    for(int i=0;i<n;i++) cin>>grid[i];

    cin>>Bn;
    blueBases.resize(Bn);
    for(int i=0;i<Bn;i++){
        cin>>blueBases[i].x>>blueBases[i].y;
        blueBaseIdAt[{blueBases[i].x, blueBases[i].y}] = i;
        cin>>blueBases[i].g>>blueBases[i].c>>blueBases[i].d>>blueBases[i].v;
    }
    cin>>Rn;
    redBases.resize(Rn);
    for(int i=0;i<Rn;i++){
        cin>>redBases[i].x>>redBases[i].y;
        redBaseIdAt[{redBases[i].x, redBases[i].y}] = i;
        cin>>redBases[i].g>>redBases[i].c>>redBases[i].d>>redBases[i].v;
        redBases[i].destroyed = (redBases[i].d<=0);
    }
    cin>>k;
    fighters.resize(k);
    for(int i=0;i<k;i++){
        cin>>fighters[i].x>>fighters[i].y>>fighters[i].G>>fighters[i].C;
        fighters[i].fuel=0;
        fighters[i].missiles=0;
        fighters[i].target=-1;
        fighters[i].path_idx=0;
    }

    const int MAX_FRAMES = 15000;
    int frames=0;

    while(frames < MAX_FRAMES){
        // Build blocked grid (alive red bases)
        vector<vector<bool>> blocked(n, vector<bool>(m,false));
        for(int i=0;i<Rn;i++){
            if(!redBases[i].destroyed){
                int x=redBases[i].x, y=redBases[i].y;
                if(inb(x,y)) blocked[x][y]=true;
            }
        }

        // Check if all destroyed
        bool allDestroyed=true;
        for(int i=0;i<Rn;i++) if(!redBases[i].destroyed){ allDestroyed=false; break; }
        if(allDestroyed) break;

        vector<string> outCmds;

        for(int i=0;i<k;i++){
            Fighter &f = fighters[i];

            // If current target destroyed, clear
            if(f.target!=-1 && redBases[f.target].destroyed){
                f.target=-1;
                f.path.clear();
                f.path_idx=0;
            }

            // If on blue base, refuel/reload
            auto itB = blueBaseIdAt.find({f.x,f.y});
            if(itB!=blueBaseIdAt.end()){
                int bid = itB->second;
                // fuel up
                int needFuel = f.G - f.fuel;
                if(needFuel>0 && blueBases[bid].g>0){
                    long long take = min<long long>(needFuel, blueBases[bid].g);
                    if(take>0){
                        outCmds.push_back("fuel " + to_string(i) + " " + to_string(take));
                        f.fuel += (int)take;
                        blueBases[bid].g -= take;
                    }
                }
                // missiles up
                int needMis = f.C - f.missiles;
                if(needMis>0 && blueBases[bid].c>0){
                    long long take = min<long long>(needMis, blueBases[bid].c);
                    if(take>0){
                        outCmds.push_back("missile " + to_string(i) + " " + to_string(take));
                        f.missiles += (int)take;
                        blueBases[bid].c -= take;
                    }
                }
            }

            // Ensure target/path
            if(f.target==-1){
                choose_target_and_path(f, blocked);
            } else {
                // If path empty or finished but not adjacent (e.g., blocked), recompute
                if(f.path_idx >= (int)f.path.size()){
                    // If already adjacent to target, do nothing here
                    int tx=redBases[f.target].x, ty=redBases[f.target].y;
                    int manh = abs(f.x-tx)+abs(f.y-ty);
                    if(manh!=1){
                        choose_target_and_path(f, blocked);
                    }
                }
            }

            // If adjacent to target and has missiles, attack
            if(f.target!=-1 && !redBases[f.target].destroyed){
                int tx=redBases[f.target].x, ty=redBases[f.target].y;
                int manh = abs(f.x-tx)+abs(f.y-ty);
                if(manh==1 && f.missiles>0){
                    int dir = dir_from_to(f.x, f.y, tx, ty);
                    int need = (int)min<long long>(f.missiles, redBases[f.target].d);
                    if(need>0 && dir!=-1){
                        outCmds.push_back("attack " + to_string(i) + " " + to_string(dir) + " " + to_string(need));
                        f.missiles -= need;
                        redBases[f.target].d -= need;
                        if(redBases[f.target].d<=0){
                            redBases[f.target].destroyed = true;
                            f.target=-1;
                            f.path.clear();
                            f.path_idx=0;
                        }
                        // After attack, skip movement this frame to keep simple
                        continue;
                    }
                }
            }

            // Move along path if possible and has fuel
            if(f.path_idx < (int)f.path.size()){
                auto [nx, ny] = f.path[f.path_idx];
                if(f.fuel>0){
                    int dir = dir_from_to(f.x, f.y, nx, ny);
                    if(dir!=-1){
                        outCmds.push_back("move " + to_string(i) + " " + to_string(dir));
                        f.fuel -= 1;
                        f.x = nx; f.y = ny;
                        f.path_idx++;
                    } else {
                        // Path inconsistency, recompute next time
                        f.path.clear();
                        f.path_idx=0;
                    }
                } else {
                    // no fuel; if on base, we refueled above, else stuck
                }
            } else {
                // If no path and not adjacent, try to choose again (maybe map changed)
                if(f.target!=-1){
                    int tx=redBases[f.target].x, ty=redBases[f.target].y;
                    if(abs(f.x-tx)+abs(f.y-ty)!=1){
                        choose_target_and_path(f, blocked);
                    }
                }
            }
        }

        for(auto &s: outCmds) {
            cout<<s<<"\n";
        }
        cout<<"OK\n";
        cout.flush();
        frames++;
    }

    return 0;
}