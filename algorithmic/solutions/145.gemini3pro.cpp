#include <iostream>
#include <vector>
#include <string>
#include <cstdlib>
#include <ctime>
#include <numeric>
#include <algorithm>
#include <tuple>

using namespace std;

int R = 12, C = 12;
vector<string> mask_grid;
int target_task; 

// Directions: 0:Right, 1:Down, 2:Left, 3:Up
int dr[] = {0, 1, 0, -1};
int dc[] = {1, 0, -1, 0};

// Grid for loop generation (padded 14x14)
int grid_state[14][14]; 

bool is_mask(int r, int c) {
    if (r < 0 || r >= R || c < 0 || c >= C) return false;
    return mask_grid[r][c] == '0';
}

struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n);
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    void unite(int x, int y) {
        int rootX = find(x);
        int rootY = find(y);
        if (rootX != rootY) parent[rootX] = rootY;
    }
};

pair<int, int> check_topology() {
    DSU dsu_in(14*14), dsu_out(14*14);
    int ones = 0;
    
    for(int i=0; i<14; ++i) {
        for(int j=0; j<14; ++j) {
            int u = i*14 + j;
            if (grid_state[i][j]) ones++;
            if (i+1 < 14 && grid_state[i][j] == grid_state[i+1][j]) {
                int v = (i+1)*14 + j;
                if (grid_state[i][j]) dsu_in.unite(u, v);
                else dsu_out.unite(u, v);
            }
            if (j+1 < 14 && grid_state[i][j] == grid_state[i][j+1]) {
                int v = i*14 + (j+1);
                if (grid_state[i][j]) dsu_in.unite(u, v);
                else dsu_out.unite(u, v);
            }
        }
    }
    
    if (ones == 0) return {0, 1}; 

    int comps_in = 0, comps_out = 0;
    vector<bool> seen_in(14*14, false), seen_out(14*14, false);
    
    for(int i=0; i<14; ++i) {
        for(int j=0; j<14; ++j) {
            int u = i*14 + j;
            if (grid_state[i][j]) {
                int root = dsu_in.find(u);
                if (!seen_in[root]) { seen_in[root] = true; comps_in++; }
            } else {
                int root = dsu_out.find(u);
                if (!seen_out[root]) { seen_out[root] = true; comps_out++; }
            }
        }
    }
    return {comps_in, comps_out};
}

int calculate_clue_from_grid(int r, int c) {
    int gr = r + 1, gc = c + 1;
    int me = grid_state[gr][gc];
    int edges = 0;
    if (grid_state[gr-1][gc] != me) edges++;
    if (grid_state[gr+1][gc] != me) edges++;
    if (grid_state[gr][gc-1] != me) edges++;
    if (grid_state[gr][gc+1] != me) edges++;
    return edges;
}

int current_clues[12][12];
int sol_count = 0;

int H[13][12];
int V[12][13];
int V_deg[13][13];

struct Edge {
    bool isH; 
    int r, c;
    int score;
};
vector<Edge> all_edges;

void backtrack_edges(int idx) {
    if (sol_count > 1) return;
    if (idx == all_edges.size()) {
        DSU dsu(13*13);
        int on_edges = 0;
        for(const auto& e : all_edges) {
            int val = (e.isH ? H[e.r][e.c] : V[e.r][e.c]);
            if(val == 1) {
                on_edges++;
                if (e.isH) dsu.unite(e.r*13+e.c, e.r*13+e.c+1);
                else dsu.unite(e.r*13+e.c, (e.r+1)*13+e.c);
            }
        }
        if (on_edges == 0) return;
        
        int root = -1;
        for(int i=0; i<13; ++i) {
            for(int j=0; j<13; ++j) {
                if (V_deg[i][j] > 0) {
                    if (V_deg[i][j] != 2) return; 
                    int rt = dsu.find(i*13+j);
                    if (root == -1) root = rt;
                    else if (root != rt) return;
                }
            }
        }
        sol_count++;
        return;
    }

    const Edge& e = all_edges[idx];
    int u = e.r*13 + e.c;
    int v = (e.isH) ? (e.r*13 + e.c + 1) : ((e.r+1)*13 + e.c);

    // Try NO LINE (-1)
    {
        if (e.isH) H[e.r][e.c] = -1; else V[e.r][e.c] = -1;
        bool ok = true;
        int cells[2][2]; int cnt = 0;
        if (e.isH) {
            if (e.r > 0) { cells[cnt][0]=e.r-1; cells[cnt][1]=e.c; cnt++; }
            if (e.r < R) { cells[cnt][0]=e.r;   cells[cnt][1]=e.c; cnt++; }
        } else {
            if (e.c > 0) { cells[cnt][0]=e.r; cells[cnt][1]=e.c-1; cnt++; }
            if (e.c < C) { cells[cnt][0]=e.r; cells[cnt][1]=e.c;   cnt++; }
        }

        for(int k=0; k<cnt; ++k) {
            int cr = cells[k][0], cc = cells[k][1];
            if (!is_mask(cr, cc)) continue;
            int clue = current_clues[cr][cc];
            int l=0, unk=0;
            int vals[4] = {H[cr][cc], H[cr+1][cc], V[cr][cc], V[cr][cc+1]};
            for(int val : vals) { if (val == 1) l++; if (val == 0) unk++; }
            if (l > clue || l + unk < clue) { ok = false; break; }
        }
        
        if (ok) {
            int verts[2] = {u, v};
            for(int vv : verts) {
                int vr = vv/13, vc = vv%13;
                int deg=0, unk=0;
                if (vr>0) { int val=V[vr-1][vc]; if(val==1) deg++; if(val==0) unk++; }
                if (vr<R) { int val=V[vr][vc];   if(val==1) deg++; if(val==0) unk++; }
                if (vc>0) { int val=H[vr][vc-1]; if(val==1) deg++; if(val==0) unk++; }
                if (vc<C) { int val=H[vr][vc];   if(val==1) deg++; if(val==0) unk++; }
                if (deg > 2) { ok=false; break; }
                if (unk == 0 && deg == 1) { ok=false; break; } 
            }
        }

        if (ok) {
            backtrack_edges(idx+1);
            if (sol_count > 1) return;
        }
    }

    // Try LINE (1)
    {
        if (e.isH) H[e.r][e.c] = 1; else V[e.r][e.c] = 1;
        V_deg[u/13][u%13]++;
        V_deg[v/13][v%13]++;
        
        bool ok = true;
        int cells[2][2]; int cnt = 0;
        if (e.isH) {
            if (e.r > 0) { cells[cnt][0]=e.r-1; cells[cnt][1]=e.c; cnt++; }
            if (e.r < R) { cells[cnt][0]=e.r;   cells[cnt][1]=e.c; cnt++; }
        } else {
            if (e.c > 0) { cells[cnt][0]=e.r; cells[cnt][1]=e.c-1; cnt++; }
            if (e.c < C) { cells[cnt][0]=e.r; cells[cnt][1]=e.c;   cnt++; }
        }

        for(int k=0; k<cnt; ++k) {
            int cr = cells[k][0], cc = cells[k][1];
            if (!is_mask(cr, cc)) continue;
            int clue = current_clues[cr][cc];
            int l=0, unk=0;
            int vals[4] = {H[cr][cc], H[cr+1][cc], V[cr][cc], V[cr][cc+1]};
            for(int val : vals) { if (val == 1) l++; if (val == 0) unk++; }
            if (l > clue || l + unk < clue) { ok = false; break; }
        }

        if (ok) {
            int verts[2] = {u, v};
            for(int vv : verts) {
                if (V_deg[vv/13][vv%13] > 2) { ok=false; break; }
                int vr = vv/13, vc = vv%13;
                int deg=0, unk=0;
                if (vr>0) { int val=V[vr-1][vc]; if(val==1) deg++; if(val==0) unk++; }
                if (vr<R) { int val=V[vr][vc];   if(val==1) deg++; if(val==0) unk++; }
                if (vc>0) { int val=H[vr][vc-1]; if(val==1) deg++; if(val==0) unk++; }
                if (vc<C) { int val=H[vr][vc];   if(val==1) deg++; if(val==0) unk++; }
                if (unk == 0 && deg == 1) { ok=false; break; }
            }
        }
        
        if (ok) backtrack_edges(idx+1);

        V_deg[u/13][u%13]--;
        V_deg[v/13][v%13]--;
    }
    if (e.isH) H[e.r][e.c] = 0; else V[e.r][e.c] = 0;
}

int main() {
    int t;
    if (cin >> t) target_task = t;
    else target_task = 0;

    mask_grid = {
        "0   0   000 ",
        "00 00  0   0",
        "0 0 0  0   0",
        "0 0 0  0000 ",
        "0 0 0  0    ",
        "0   0  0    ",
        "            ",
        "0  0   00000",
        "0 0      0  ",
        "00   0 0 0  ",
        "0 0  0 0 0  ",
        "0  0 000 0  "
    };

    srand(time(0));

    while(true) {
        // Generate Loop using SA
        for(int i=0; i<14; ++i) for(int j=0; j<14; ++j) grid_state[i][j] = 0;

        int size = rand() % 40 + 40; 
        int r = 6, c = 6;
        grid_state[r][c] = 1;
        vector<pair<int, int>> frontier;
        auto add_frontier = [&](int rr, int cc) {
            for(int k=0; k<4; ++k) {
                int nr = rr + dr[k], nc = cc + dc[k];
                if (nr >= 1 && nr <= 12 && nc >= 1 && nc <= 12 && grid_state[nr][nc] == 0) {
                    bool in_front = false;
                    for(auto &p : frontier) if(p.first==nr && p.second==nc) in_front=true;
                    if(!in_front) frontier.push_back({nr, nc});
                }
            }
        };
        add_frontier(r, c);
        
        for(int k=0; k<size; ++k) {
            if (frontier.empty()) break;
            int idx = rand() % frontier.size();
            pair<int, int> p = frontier[idx];
            grid_state[p.first][p.second] = 1;
            frontier.erase(frontier.begin() + idx);
            add_frontier(p.first, p.second);
        }

        for(int iter=0; iter<3000; ++iter) {
            pair<int, int> topo = check_topology();
            int bad_topo = (topo.first - 1) + (topo.second - 1);
            int bad_clues = 0;
            
            for(int i=0; i<12; ++i) {
                for(int j=0; j<12; ++j) {
                    if (is_mask(i, j)) {
                        int clue = calculate_clue_from_grid(i, j);
                        if (clue == 4) bad_clues++;
                        if (target_task == 1 && clue == 0) bad_clues++;
                    }
                }
            }

            if (bad_topo == 0 && bad_clues == 0) break;

            int fr = rand() % 12 + 1;
            int fc = rand() % 12 + 1;
            grid_state[fr][fc] ^= 1;

            pair<int, int> new_topo = check_topology();
            int new_bad_topo = (new_topo.first - 1) + (new_topo.second - 1);
            int new_bad_clues = 0;
            for(int i=0; i<12; ++i) {
                for(int j=0; j<12; ++j) {
                    if (is_mask(i, j)) {
                        int clue = calculate_clue_from_grid(i, j);
                        if (clue == 4) new_bad_clues++;
                        if (target_task == 1 && clue == 0) new_bad_clues++;
                    }
                }
            }

            int current_E = bad_topo * 100 + bad_clues;
            int new_E = new_bad_topo * 100 + new_bad_clues;

            if (new_E <= current_E) {
            } else {
                grid_state[fr][fc] ^= 1;
            }
        }

        pair<int, int> topo = check_topology();
        int bad = 0;
        if (topo.first != 1 || topo.second != 1) bad = 1;
        for(int i=0; i<12; ++i) {
            for(int j=0; j<12; ++j) {
                if (is_mask(i, j)) {
                    int clue = calculate_clue_from_grid(i, j);
                    if (clue == 4) bad = 1;
                    if (target_task == 1 && clue == 0) bad = 1;
                }
            }
        }

        if (bad == 0) {
            for(int i=0; i<12; ++i) for(int j=0; j<12; ++j) current_clues[i][j] = -1;
            for(int i=0; i<12; ++i) {
                for(int j=0; j<12; ++j) {
                    if (is_mask(i, j)) {
                        current_clues[i][j] = calculate_clue_from_grid(i, j);
                    }
                }
            }
            
            all_edges.clear();
            for(int i=0; i<=12; ++i) for(int j=0; j<12; ++j) all_edges.push_back({true, i, j, 0});
            for(int i=0; i<12; ++i) for(int j=0; j<=12; ++j) all_edges.push_back({false, i, j, 0});
            
            for(auto &e : all_edges) {
                int score = 0;
                int cells[2][2]; int cnt = 0;
                if (e.isH) {
                    if (e.r > 0) { cells[cnt][0]=e.r-1; cells[cnt][1]=e.c; cnt++; }
                    if (e.r < R) { cells[cnt][0]=e.r;   cells[cnt][1]=e.c; cnt++; }
                } else {
                    if (e.c > 0) { cells[cnt][0]=e.r; cells[cnt][1]=e.c-1; cnt++; }
                    if (e.c < C) { cells[cnt][0]=e.r; cells[cnt][1]=e.c;   cnt++; }
                }
                for(int k=0; k<cnt; ++k) {
                    if (is_mask(cells[k][0], cells[k][1])) {
                        int cl = current_clues[cells[k][0]][cells[k][1]];
                        score += 10;
                        if (cl == 0 || cl == 3) score += 5;
                    }
                }
                e.score = score;
            }
            sort(all_edges.begin(), all_edges.end(), [](const Edge& a, const Edge& b){
                return a.score > b.score;
            });

            for(int i=0; i<13; ++i) for(int j=0; j<12; ++j) H[i][j] = 0;
            for(int i=0; i<12; ++i) for(int j=0; j<13; ++j) V[i][j] = 0;
            for(int i=0; i<13; ++i) for(int j=0; j<13; ++j) V_deg[i][j] = 0;
            sol_count = 0;
            
            backtrack_edges(0);

            if (sol_count == 1) {
                for(int i=0; i<12; ++i) {
                    for(int j=0; j<12; ++j) {
                        if (is_mask(i, j)) cout << current_clues[i][j];
                        else cout << " ";
                    }
                    cout << endl;
                }
                return 0;
            }
        }
    }
}