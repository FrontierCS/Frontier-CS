#include <iostream>
#include <vector>
#include <string>
#include <cstdlib>
#include <ctime>
#include <queue>
#include <algorithm>

using namespace std;

const int H = 12;
const int W = 12;

vector<string> TEMPLATE = {
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

int region[H + 2][W + 2];
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

bool check_connectivity() {
    int start_r = -1, start_c = -1;
    int ones = 0;
    for (int r = 1; r <= H; ++r) {
        for (int c = 1; c <= W; ++c) {
            if (region[r][c] == 1) {
                if (start_r == -1) { start_r = r; start_c = c; }
                ones++;
            }
        }
    }
    if (ones == 0) return false;

    int seen = 0;
    queue<pair<int, int>> q;
    vector<vector<bool>> vis(H + 2, vector<bool>(W + 2, false));
    q.push({start_r, start_c});
    vis[start_r][start_c] = true;
    seen++;

    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i], nc = c + dc[i];
            if (nr >= 1 && nr <= H && nc >= 1 && nc <= W && region[nr][nc] == 1 && !vis[nr][nc]) {
                vis[nr][nc] = true;
                seen++;
                q.push({nr, nc});
            }
        }
    }
    if (seen != ones) return false;

    int zeros = 0;
    for (int r = 0; r <= H + 1; ++r) for (int c = 0; c <= W + 1; ++c) if (region[r][c] == 0) zeros++;
    
    seen = 0;
    for (int r = 0; r <= H + 1; ++r) fill(vis[r].begin(), vis[r].end(), false);
    q.push({0, 0});
    vis[0][0] = true;
    seen++;

    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        for (int i = 0; i < 4; ++i) {
            int nr = r + dr[i], nc = c + dc[i];
            if (nr >= 0 && nr <= H + 1 && nc >= 0 && nc <= W + 1 && region[nr][nc] == 0 && !vis[nr][nc]) {
                vis[nr][nc] = true;
                seen++;
                q.push({nr, nc});
            }
        }
    }
    return seen == zeros;
}

struct Solver {
    int clues[H][W];
    int h_edges[(H + 1) * W];
    int v_edges[(W + 1) * H];
    int solutions = 0;

    Solver(int puz[H][W]) {
        for(int r=0; r<H; ++r) for(int c=0; c<W; ++c) clues[r][c] = puz[r][c];
        fill(h_edges, h_edges + (H + 1) * W, 0);
        fill(v_edges, v_edges + (W + 1) * H, 0);
    }

    int get_h(int r, int c) { return h_edges[r * W + c]; }
    int get_v(int r, int c) { return v_edges[c * H + r]; }
    void set_h(int r, int c, int v) { h_edges[r * W + c] = v; }
    void set_v(int r, int c, int v) { v_edges[c * H + r] = v; }

    bool check_vertex(int r, int c) {
        int cnt = 0, unk = 0;
        int e[4]; 
        e[0] = (r > 0) ? get_v(r - 1, c) : 2;
        e[1] = (r < H) ? get_v(r, c) : 2;
        e[2] = (c > 0) ? get_h(r, c - 1) : 2;
        e[3] = (c < W) ? get_h(r, c) : 2;
        for(int x : e) { if(x==1) cnt++; if(x==0) unk++; }
        if(cnt > 2) return false;
        if(cnt + unk < 2 && (cnt > 0 || unk > 0)) return false; 
        if(cnt == 1 && unk == 0) return false;
        return true;
    }

    bool check_cell(int r, int c) {
        if(clues[r][c] == -1) return true;
        int cnt = 0, unk = 0;
        int e[4] = { get_h(r, c), get_h(r + 1, c), get_v(r, c), get_v(r, c + 1) };
        for(int x : e) { if(x==1) cnt++; if(x==0) unk++; }
        if(cnt > clues[r][c]) return false;
        if(cnt + unk < clues[r][c]) return false;
        return true;
    }

    void run(int idx) {
        if(solutions > 1) return;
        int max_edges = (H + 1) * W + (W + 1) * H;
        if(idx == max_edges) {
            // Check single loop
            int deg[H + 1][W + 1] = {0};
            int ec = 0;
            struct DSU { vector<int> p; DSU(int n){p.resize(n);for(int i=0;i<n;++i)p[i]=i;} int find(int x){return p[x]==x?x:p[x]=find(p[x]);} void unite(int a,int b){p[find(a)]=find(b);} } dsu((H+1)*(W+1));
            
            for(int r=0; r<=H; ++r) for(int c=0; c<W; ++c) if(get_h(r,c)==1) { deg[r][c]++; deg[r][c+1]++; dsu.unite(r*(W+1)+c, r*(W+1)+c+1); ec++; }
            for(int r=0; r<H; ++r) for(int c=0; c<=W; ++c) if(get_v(r,c)==1) { deg[r][c]++; deg[r+1][c]++; dsu.unite(r*(W+1)+c, (r+1)*(W+1)+c); ec++; }
            
            if(ec == 0) return;
            int root = -1;
            for(int r=0; r<=H; ++r) for(int c=0; c<=W; ++c) {
                if(deg[r][c] != 0 && deg[r][c] != 2) return;
                if(deg[r][c] > 0) {
                    int p = dsu.find(r*(W+1)+c);
                    if(root == -1) root = p;
                    else if(root != p) return;
                }
            }
            solutions++;
            return;
        }

        bool is_h = idx < (H + 1) * W;
        int e_idx = is_h ? idx : idx - (H + 1) * W;
        int r = is_h ? e_idx / W : e_idx % H;
        int c = is_h ? e_idx % W : e_idx / H;

        auto attempt = [&](int val) {
            if(is_h) h_edges[e_idx] = val; else v_edges[e_idx] = val;
            bool ok = true;
            if(!check_vertex(r, c)) ok = false;
            if(ok) {
                int r2 = is_h ? r : r+1;
                int c2 = is_h ? c+1 : c;
                if(!check_vertex(r2, c2)) ok = false;
            }
            if(ok) {
                if(is_h) {
                    if(r > 0 && !check_cell(r-1, c)) ok = false;
                    if(ok && r < H && !check_cell(r, c)) ok = false;
                } else {
                    if(c > 0 && !check_cell(r, c-1)) ok = false;
                    if(ok && c < W && !check_cell(r, c)) ok = false;
                }
            }
            if(ok) run(idx + 1);
            if(is_h) h_edges[e_idx] = 0; else v_edges[e_idx] = 0;
        };

        // Heuristic: try X (2) first to keep sparse
        attempt(2);
        if(solutions > 1) return;
        attempt(1);
    }
};

int main() {
    int type;
    if (!(cin >> type)) return 0;
    
    int seed = 0;
    while(true) {
        srand(seed++);
        for(int i=0; i<H+2; ++i) for(int j=0; j<W+2; ++j) region[i][j] = 0;
        
        int sr = rand() % H + 1;
        int sc = rand() % W + 1;
        region[sr][sc] = 1;
        
        vector<pair<int,int>> cands;
        auto add_cands = [&](int r, int c) {
            for(int k=0; k<4; ++k) {
                int nr = r+dr[k], nc = c+dc[k];
                if(nr>=1 && nr<=H && nc>=1 && nc<=W && region[nr][nc]==0) cands.push_back({nr,nc});
            }
        };
        add_cands(sr, sc);
        
        int limit = H*W/2 + rand() % (H*W/4);
        while(!cands.empty() && limit > 0) {
            int idx = rand() % cands.size();
            auto [r, c] = cands[idx];
            cands.erase(cands.begin() + idx);
            if(region[r][c] == 1) continue;
            region[r][c] = 1;
            if(check_connectivity()) {
                add_cands(r, c);
                limit--;
            } else {
                region[r][c] = 0;
            }
        }
        
        int puz[H][W];
        bool possible = true;
        for(int r=0; r<H; ++r) {
            for(int c=0; c<W; ++c) {
                if(TEMPLATE[r][c] != ' ') {
                    int cnt = 0;
                    if(region[r+1][c+1] != region[r][c+1]) cnt++;
                    if(region[r+1][c+1] != region[r+2][c+1]) cnt++;
                    if(region[r+1][c+1] != region[r+1][c]) cnt++;
                    if(region[r+1][c+1] != region[r+1][c+2]) cnt++;
                    puz[r][c] = cnt;
                    if(type == 1 && cnt == 0) possible = false;
                    if(cnt > 3) possible = false;
                } else {
                    puz[r][c] = -1;
                }
            }
        }
        
        if(!possible) continue;
        
        Solver solver(puz);
        solver.run(0);
        if(solver.solutions == 1) {
            for(int r=0; r<H; ++r) {
                for(int c=0; c<W; ++c) {
                    if(puz[r][c] != -1) cout << puz[r][c];
                    else cout << " ";
                }
                cout << endl;
            }
            break;
        }
    }
    return 0;
}