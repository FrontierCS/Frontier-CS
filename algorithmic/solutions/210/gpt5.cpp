#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long fuelRem;
    long long missRem;
    int d, v; // unused
};

struct RedBase {
    int x, y;
    long long defRem;
    int v;
    bool destroyed;
};

struct BFSInfo {
    int sx, sy;
    int n, m;
    vector<vector<int>> dist;
    vector<vector<pair<int,int>>> parent;
    vector<vector<char>> pdir; // dir from parent to this cell
};

struct Fighter {
    int id;
    int x, y;
    int G, C;
    int fuel = 0;
    int missile = 0;
    int homeBaseId = -1;

    // plan
    enum State { Idle, Prepare, MoveOut, Attack, MoveBack } state = Idle;
    int targetRid = -1;
    int attackDir = -1;
    int adjX = -1, adjY = -1;
    vector<int> path;      // from base to adj
    vector<int> pathBack;  // reverse
    int idx = 0;           // index for moving out
    int idxBack = 0;       // index for moving back
};

int n, m;
vector<string> grid;
int NB_blue, NB_red, k;
vector<BlueBase> blueBases;
vector<RedBase> redBases;
vector<Fighter> fighters;
vector<vector<int>> blueBaseIdAt; // -1 if none
vector<vector<int>> redBaseIdAt;  // -1 if none
const int INF = 1e9;
int dx[4] = {-1, 1, 0, 0};
int dy[4] = {0, 0, -1, 1};

BFSInfo computeBFSFrom(int sx, int sy, const vector<string>& grid) {
    BFSInfo info;
    info.sx = sx; info.sy = sy;
    info.n = grid.size();
    info.m = grid[0].size();
    info.dist.assign(info.n, vector<int>(info.m, INF));
    info.parent.assign(info.n, vector<pair<int,int>>(info.m, {-1,-1}));
    info.pdir.assign(info.n, vector<char>(info.m, -1));
    deque<pair<int,int>> q;
    info.dist[sx][sy] = 0;
    q.push_back({sx,sy});
    while(!q.empty()){
        auto [x,y] = q.front(); q.pop_front();
        for(int d=0; d<4; ++d){
            int nx = x + dx[d];
            int ny = y + dy[d];
            if(nx<0||nx>=info.n||ny<0||ny>=info.m) continue;
            if(grid[nx][ny] == '#') continue; // cannot enter red base cells
            if(info.dist[nx][ny] > info.dist[x][y] + 1) {
                info.dist[nx][ny] = info.dist[x][y] + 1;
                info.parent[nx][ny] = {x,y};
                info.pdir[nx][ny] = (char)d; // move from parent to this
                q.push_back({nx,ny});
            }
        }
    }
    return info;
}

vector<int> reconstructPath(const BFSInfo& bfs, int ax, int ay) {
    vector<int> seq;
    int cx = ax, cy = ay;
    while(!(cx == bfs.sx && cy == bfs.sy)) {
        auto p = bfs.parent[cx][cy];
        if(p.first == -1) { // unreachable
            seq.clear();
            return seq;
        }
        int d = bfs.pdir[cx][cy];
        seq.push_back(d);
        cx = p.first; cy = p.second;
    }
    reverse(seq.begin(), seq.end());
    return seq;
}

int oppositeDir(int d) {
    if(d == 0) return 1;
    if(d == 1) return 0;
    if(d == 2) return 3;
    return 2;
}

struct Precomp {
    BFSInfo bfs;
    bool ok;
};
unordered_map<int, Precomp> precompByBase; // key = baseId

bool findAndSetTarget(Fighter &f) {
    int hb = f.homeBaseId;
    if(hb < 0) return false;
    if(precompByBase.find(hb) == precompByBase.end()) return false;
    auto &pre = precompByBase[hb];
    const auto &dist = pre.bfs.dist;
    // select best target
    double bestScore = -1e100;
    int bestRid = -1;
    int bestAdjX = -1, bestAdjY = -1;
    int bestAttackDir = -1;
    int bestD = INF;

    for (int j = 0; j < (int)redBases.size(); ++j) {
        if (redBases[j].defRem <= 0) continue;
        int rx = redBases[j].x, ry = redBases[j].y;
        int bestLocalD = INF;
        int adjx = -1, adjy = -1;
        int attDir = -1;
        for (int d = 0; d < 4; ++d) {
            int nx = rx + dx[d];
            int ny = ry + dy[d];
            if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
            if (grid[nx][ny] == '#') continue; // cannot stand on red base cells
            if (dist[nx][ny] >= INF) continue;
            int dd = dist[nx][ny];
            if (dd < bestLocalD) {
                bestLocalD = dd;
                adjx = nx; adjy = ny;
                // attack direction depends on relative position fighter->target
                // if fighter at (rx-1,ry), attack down (1)
                // if fighter at (rx+1,ry), attack up (0)
                // if fighter at (rx,ry-1), attack right (3)
                // if fighter at (rx,ry+1), attack left (2)
                if (nx == rx - 1 && ny == ry) attDir = 1;
                else if (nx == rx + 1 && ny == ry) attDir = 0;
                else if (nx == rx && ny == ry - 1) attDir = 3;
                else if (nx == rx && ny == ry + 1) attDir = 2;
                else attDir = -1;
            }
        }
        if (bestLocalD >= INF) continue;
        long long requiredRound = 2LL * bestLocalD;
        if (requiredRound > f.G) continue;
        if (blueBases[hb].fuelRem < requiredRound) continue;
        if (blueBases[hb].missRem <= 0) continue;
        double score = (double)redBases[j].v / (bestLocalD + 1.0);
        // prefer closer when same score
        if (score > bestScore || (abs(score - bestScore) < 1e-12 && bestLocalD < bestD)) {
            bestScore = score;
            bestRid = j;
            bestAdjX = adjx; bestAdjY = adjy;
            bestAttackDir = attDir;
            bestD = bestLocalD;
        }
    }
    if (bestRid == -1) return false;
    // set plan
    vector<int> path = reconstructPath(pre.bfs, bestAdjX, bestAdjY);
    if ((int)path.size() != bestD) {
        // Something off; but continue only if consistent
        if ((int)path.size() == 0 && bestD != 0) return false;
    }
    f.targetRid = bestRid;
    f.attackDir = bestAttackDir;
    f.adjX = bestAdjX;
    f.adjY = bestAdjY;
    f.path = path;
    f.pathBack.clear();
    for (int i = (int)path.size() - 1; i >= 0; --i) {
        f.pathBack.push_back(oppositeDir(path[i]));
    }
    f.idx = 0;
    f.idxBack = 0;
    f.state = Fighter::Prepare;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if(!(cin >> n >> m)) {
        return 0;
    }
    grid.resize(n);
    for(int i=0;i<n;++i) cin >> grid[i];

    cin >> NB_blue;
    blueBases.resize(NB_blue);
    blueBaseIdAt.assign(n, vector<int>(m, -1));
    for(int i=0;i<NB_blue;++i){
        int x,y; long long g,c; int d,v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        blueBases[i] = {x,y,g,c,d,v};
        if (x>=0 && x<n && y>=0 && y<m) {
            blueBaseIdAt[x][y] = i;
        }
    }
    cin >> NB_red;
    redBases.resize(NB_red);
    redBaseIdAt.assign(n, vector<int>(m, -1));
    for(int i=0;i<NB_red;++i){
        int x,y; long long g,c; long long d; int v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        redBases[i] = {x,y,d,v,false};
        if (x>=0 && x<n && y>=0 && y<m) {
            redBaseIdAt[x][y] = i;
        }
    }
    cin >> k;
    fighters.resize(k);
    for(int i=0;i<k;++i){
        int x,y,G,C;
        cin >> x >> y >> G >> C;
        fighters[i].id = i;
        fighters[i].x = x; fighters[i].y = y;
        fighters[i].G = G; fighters[i].C = C;
        fighters[i].fuel = 0; fighters[i].missile = 0;
        int hb = -1;
        if (x>=0 && x<n && y>=0 && y<m) hb = blueBaseIdAt[x][y];
        fighters[i].homeBaseId = hb;
        fighters[i].state = Fighter::Idle;
        fighters[i].targetRid = -1;
    }

    // Precompute BFS for unique home bases
    // Build passability grid: treat '#' cells as blocked always
    // BFS is computed per base position
    vector<bool> baseBFSComputed(NB_blue, false);
    for (auto &f : fighters) {
        int hb = f.homeBaseId;
        if (hb < 0) continue;
        if (!baseBFSComputed[hb]) {
            Precomp pre;
            pre.ok = true;
            pre.bfs = computeBFSFrom(blueBases[hb].x, blueBases[hb].y, grid);
            precompByBase[hb] = pre;
            baseBFSComputed[hb] = true;
        }
    }

    const int MAX_FRAMES = 15000;
    for (int frame = 0; frame < MAX_FRAMES; ++frame) {
        vector<string> cmds;
        bool anyProgressPossible = false;

        // For Idle fighters, try to set a target (no command emitted)
        for (auto &f : fighters) {
            if (f.state == Fighter::Idle) {
                bool got = findAndSetTarget(f);
                if (got) {
                    anyProgressPossible = true;
                }
            }
        }

        // For all fighters, execute one step
        for (auto &f : fighters) {
            if (f.state == Fighter::Prepare) {
                anyProgressPossible = true;
                int hb = f.homeBaseId;
                if (hb < 0) { f.state = Fighter::Idle; f.targetRid = -1; continue; }
                long long desiredFuel = 2LL * (long long)f.path.size();
                // Ensure desiredFuel <= G
                if (desiredFuel > f.G) {
                    // cannot proceed; abort plan
                    f.state = Fighter::Idle; f.targetRid = -1;
                    continue;
                }
                // Fuel up to desired
                long long missingFuel = max(0LL, desiredFuel - (long long)f.fuel);
                long long canFuel = min(missingFuel, blueBases[hb].fuelRem);
                if (canFuel > 0) {
                    cmds.push_back("fuel " + to_string(f.id) + " " + to_string(canFuel));
                    f.fuel += (int)canFuel;
                    blueBases[hb].fuelRem -= canFuel;
                }
                // Missiles up to min(C, base miss, red def)
                long long defRem = (f.targetRid >=0 ? redBases[f.targetRid].defRem : 0LL);
                long long wantMiss = 0;
                if (f.targetRid >= 0 && defRem > 0) {
                    wantMiss = min( (long long)f.C, min(blueBases[hb].missRem, defRem) );
                }
                long long missingMiss = max(0LL, wantMiss - (long long)f.missile);
                long long canMiss = min(missingMiss, blueBases[hb].missRem);
                if (canMiss > 0) {
                    cmds.push_back("missile " + to_string(f.id) + " " + to_string(canMiss));
                    f.missile += (int)canMiss;
                    blueBases[hb].missRem -= canMiss;
                }
                // Check if ready to depart
                bool readyFuel = ((long long)f.fuel >= desiredFuel);
                bool readyMiss = (f.missile > 0);
                if (readyFuel && readyMiss) {
                    f.state = Fighter::MoveOut;
                    f.idx = 0;
                } else {
                    // If impossible to ever proceed (no supplies left)
                    bool fuelImpossible = ((long long)f.fuel + blueBases[hb].fuelRem < desiredFuel);
                    bool missileImpossible = (f.missile == 0 && blueBases[hb].missRem == 0);
                    if (fuelImpossible || missileImpossible) {
                        // abort mission
                        f.state = Fighter::Idle;
                        f.targetRid = -1;
                    }
                }
            } else if (f.state == Fighter::MoveOut) {
                anyProgressPossible = true;
                if (f.idx < (int)f.path.size()) {
                    int dir = f.path[f.idx];
                    int nx = f.x + dx[dir];
                    int ny = f.y + dy[dir];
                    // Safety check
                    if (nx>=0 && nx<n && ny>=0 && ny<m && grid[nx][ny] != '#') {
                        if (f.fuel > 0) {
                            cmds.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.x = nx; f.y = ny;
                            f.fuel -= 1;
                            f.idx++;
                        } else {
                            // Shouldn't happen due to planning; fallback abort
                            f.state = Fighter::Idle; f.targetRid = -1;
                        }
                    } else {
                        // Invalid path; abort
                        f.state = Fighter::Idle; f.targetRid = -1;
                    }
                } else {
                    // reached adjacency
                    f.state = Fighter::Attack;
                }
            } else if (f.state == Fighter::Attack) {
                anyProgressPossible = true;
                if (f.targetRid < 0) {
                    f.state = Fighter::MoveBack;
                    f.idxBack = 0;
                } else {
                    long long need = redBases[f.targetRid].defRem;
                    if (need <= 0) {
                        f.state = Fighter::MoveBack;
                        f.idxBack = 0;
                    } else {
                        int count = (int)min<long long>((long long)f.missile, need);
                        if (count > 0) {
                            cmds.push_back("attack " + to_string(f.id) + " " + to_string(f.attackDir) + " " + to_string(count));
                            f.missile -= count;
                            redBases[f.targetRid].defRem -= count;
                            if (redBases[f.targetRid].defRem <= 0) {
                                redBases[f.targetRid].destroyed = true;
                            }
                        }
                        // move back after attack
                        f.state = Fighter::MoveBack;
                        f.idxBack = 0;
                    }
                }
            } else if (f.state == Fighter::MoveBack) {
                anyProgressPossible = true;
                if (f.idxBack < (int)f.pathBack.size()) {
                    int dir = f.pathBack[f.idxBack];
                    int nx = f.x + dx[dir];
                    int ny = f.y + dy[dir];
                    if (nx>=0 && nx<n && ny>=0 && ny<m && grid[nx][ny] != '#') {
                        if (f.fuel > 0) {
                            cmds.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.x = nx; f.y = ny;
                            f.fuel -= 1;
                            f.idxBack++;
                        } else {
                            // Shouldn't happen
                            f.state = Fighter::Idle; f.targetRid = -1;
                        }
                    } else {
                        // invalid; abort
                        f.state = Fighter::Idle; f.targetRid = -1;
                    }
                } else {
                    // reached base
                    f.state = Fighter::Idle;
                    f.targetRid = -1;
                }
            } else {
                // Idle - handled above
            }
        }

        if (!cmds.empty()) {
            for (auto &s : cmds) cout << s << "\n";
            cout << "OK\n";
        } else {
            // If nothing to do and no more progress possible, end early
            if (!anyProgressPossible) {
                break;
            } else {
                // advance a frame doing nothing (could help to wait, but supplies don't increase; however to keep simple, we can still output OK)
                cout << "OK\n";
            }
        }
    }

    return 0;
}