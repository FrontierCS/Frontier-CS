#include <bits/stdc++.h>
using namespace std;

struct Base {
    int x, y;
    long long g, c, d, v; // for blue: g fuel supply, c missile supply; for red: d defense, v value
};

struct Fighter {
    int x, y;
    int G, C;
    int fuel = 0;
    int missiles = 0;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if(!(cin >> n >> m)) {
        return 0;
    }
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    int Nb;
    cin >> Nb;
    vector<Base> blue(Nb);
    map<pair<int,int>, int> blueIndexAt;
    for (int i = 0; i < Nb; ++i) {
        cin >> blue[i].x >> blue[i].y;
        cin >> blue[i].g >> blue[i].c >> blue[i].d >> blue[i].v;
        blueIndexAt[{blue[i].x, blue[i].y}] = i;
    }

    int Nr;
    cin >> Nr;
    vector<Base> red(Nr);
    map<pair<int,int>, int> redIndexAt;
    for (int i = 0; i < Nr; ++i) {
        cin >> red[i].x >> red[i].y;
        cin >> red[i].g >> red[i].c >> red[i].d >> red[i].v; // for red, g,c unused; d defense; v value
        redIndexAt[{red[i].x, red[i].y}] = i;
    }

    int k;
    cin >> k;
    vector<Fighter> F(k);
    for (int i = 0; i < k; ++i) {
        cin >> F[i].x >> F[i].y >> F[i].G >> F[i].C;
        F[i].fuel = 0;
        F[i].missiles = 0;
    }

    auto inb = [&](int x, int y){ return x>=0 && x<n && y>=0 && y<m; };
    const int dx[4] = {-1,1,0,0};
    const int dy[4] = {0,0,-1,1};

    auto isUndestroyedRed = [&](int x, int y)->bool{
        auto it = redIndexAt.find({x,y});
        if (it == redIndexAt.end()) return false;
        int idx = it->second;
        return red[idx].d > 0;
    };

    auto bfs_to_targets = [&](pair<int,int> start, const vector<vector<bool>>& blocked, const vector<vector<bool>>& isTarget)->vector<pair<int,int>>{
        // returns path from start to nearest target (by BFS), as list of cells including start and target; empty if none
        vector<vector<int>> dist(n, vector<int>(m, -1));
        vector<vector<pair<int,int>>> par(n, vector<pair<int,int>>(m, {-1,-1}));
        deque<pair<int,int>> dq;
        if (!inb(start.first, start.second)) return {};
        dist[start.first][start.second] = 0;
        dq.push_back(start);
        pair<int,int> found = {-1,-1};
        while(!dq.empty()){
            auto [x,y]=dq.front(); dq.pop_front();
            if (isTarget[x][y]) { found = {x,y}; break; }
            for(int dir=0; dir<4; ++dir){
                int nx = x + dx[dir], ny = y + dy[dir];
                if(!inb(nx,ny)) continue;
                if(blocked[nx][ny]) continue;
                if(dist[nx][ny]!=-1) continue;
                dist[nx][ny] = dist[x][y] + 1;
                par[nx][ny] = {x,y};
                dq.emplace_back(nx,ny);
            }
        }
        if (found.first==-1) return {};
        vector<pair<int,int>> path;
        pair<int,int> cur = found;
        while(!(cur.first== -1 && cur.second== -1)){
            path.push_back(cur);
            auto p = par[cur.first][cur.second];
            if (p.first==-1 && p.second==-1) break;
            cur = p;
        }
        reverse(path.begin(), path.end());
        return path;
    };

    auto build_blocked = [&](){
        vector<vector<bool>> blocked(n, vector<bool>(m, false));
        // cannot enter undestroyed red bases
        for (auto &rb: red) {
            if (rb.d > 0) blocked[rb.x][rb.y] = true;
        }
        return blocked;
    };

    auto build_adjacent_to_red_targets = [&](){
        vector<vector<bool>> isTarget(n, vector<bool>(m, false));
        for (auto &rb: red) {
            if (rb.d <= 0) continue;
            for(int dir=0; dir<4; ++dir){
                int nx = rb.x + dx[dir], ny = rb.y + dy[dir];
                if (!inb(nx,ny)) continue;
                // Cannot be the red base cell itself (already handled by blocked); any cell adjacent is target
                isTarget[nx][ny] = true;
            }
        }
        return isTarget;
    };

    auto build_blue_cells = [&](){
        vector<vector<bool>> isBlue(n, vector<bool>(m, false));
        for (auto &bb: blue) isBlue[bb.x][bb.y] = true;
        return isBlue;
    };

    auto all_red_destroyed = [&](){
        for (auto &rb: red) if (rb.d > 0) return false;
        return true;
    };

    int MAX_FRAMES = 1000;

    for (int frame = 0; frame < MAX_FRAMES; ++frame) {
        // Refuel/reload on blue bases
        for (int i = 0; i < k; ++i) {
            auto &fi = F[i];
            auto it = blueIndexAt.find({fi.x, fi.y});
            if (it != blueIndexAt.end()) {
                int bidx = it->second;
                long long needF = fi.G - fi.fuel;
                if (needF > 0 && blue[bidx].g > 0) {
                    long long give = min(needF, blue[bidx].g);
                    if (give > 0) {
                        cout << "fuel " << i << " " << give << "\n";
                        fi.fuel += (int)give;
                        blue[bidx].g -= give;
                    }
                }
                long long needM = fi.C - fi.missiles;
                if (needM > 0 && blue[bidx].c > 0) {
                    long long give = min(needM, blue[bidx].c);
                    if (give > 0) {
                        cout << "missile " << i << " " << give << "\n";
                        fi.missiles += (int)give;
                        blue[bidx].c -= give;
                    }
                }
            }
        }

        // Attempt attacks if adjacent
        vector<vector<bool>> blocked = build_blocked();
        bool any_action = false;

        for (int i = 0; i < k; ++i) {
            auto &fi = F[i];
            bool attacked = false;
            for (int dir = 0; dir < 4; ++dir) {
                int tx = fi.x + dx[dir], ty = fi.y + dy[dir];
                if (!inb(tx,ty)) continue;
                auto it = redIndexAt.find({tx,ty});
                if (it == redIndexAt.end()) continue;
                int ridx = it->second;
                if (red[ridx].d > 0 && fi.missiles > 0) {
                    int cnt = (int)min<long long>(fi.missiles, red[ridx].d);
                    if (cnt > 0) {
                        cout << "attack " << i << " " << dir << " " << cnt << "\n";
                        fi.missiles -= cnt;
                        red[ridx].d -= cnt;
                        any_action = true;
                        attacked = true;
                    }
                }
                if (attacked) break;
            }
        }

        // Movement if not attacked
        vector<vector<bool>> isBlueCell = build_blue_cells();
        vector<vector<bool>> targetAdj = build_adjacent_to_red_targets();

        for (int i = 0; i < k; ++i) {
            auto &fi = F[i];
            // If already attacked this frame, skip move
            bool attacked = false;
            for (int dir = 0; dir < 4; ++dir) {
                int tx = fi.x + dx[dir], ty = fi.y + dy[dir];
                if (!inb(tx,ty)) continue;
                auto it = redIndexAt.find({tx,ty});
                if (it != redIndexAt.end()) {
                    int ridx = it->second;
                    if (red[ridx].d <= 0) continue;
                    // If had missiles > 0, we would have attacked already
                }
            }
            // Decide destination: if no missiles, go to nearest blue base; else go to adjacent to red
            if (fi.fuel <= 0) continue;

            vector<vector<bool>> targets(n, vector<bool>(m,false));
            if (fi.missiles == 0) {
                for (auto &bb: blue) targets[bb.x][bb.y] = true;
            } else {
                targets = targetAdj;
            }
            // Ensure not attempting to move if already at target and with missiles available but no adjacent red to attack; moving towards red
            if (!targets[fi.x][fi.y]) {
                auto path = bfs_to_targets({fi.x, fi.y}, blocked, targets);
                if (path.size() >= 2) {
                    // Move from path[0] to path[1]
                    int nx = path[1].first, ny = path[1].second;
                    int dir = -1;
                    for (int d = 0; d < 4; ++d) {
                        if (fi.x + dx[d] == nx && fi.y + dy[d] == ny) { dir = d; break; }
                    }
                    if (dir != -1 && fi.fuel > 0) {
                        cout << "move " << i << " " << dir << "\n";
                        fi.x = nx; fi.y = ny;
                        fi.fuel -= 1;
                        any_action = true;
                    }
                }
            }
        }

        cout << "OK\n";
        if (all_red_destroyed()) {
            break;
        }
        // Optional: if no actions possible for anyone and not adjacent to targets, we could break early.
        // However, we keep going until targets destroyed or frames exhausted.
        (void)any_action;
    }

    return 0;
}