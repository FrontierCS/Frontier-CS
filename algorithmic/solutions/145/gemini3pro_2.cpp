#include <iostream>
#include <vector>
#include <string>
#include <cstdlib>
#include <ctime>
#include <cstring>
#include <algorithm>

using namespace std;

// Mask derived from the problem description's sample output structure
const vector<string> MASK_RAW = {
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

int grid_clues[12][12];
bool is_template[12][12];
int task_type;

// Edges: 0=Unknown, 1=Line, 2=Cross
int H[13][12]; 
int V[12][13];

struct State {
    int H[13][12];
    int V[12][13];
};

struct EdgeCoord { char t; int r, c; };
vector<EdgeCoord> edges_list;
long long sol_count = 0;

void parse_mask() {
    memset(is_template, 0, sizeof(is_template));
    for(int r=0; r<12; ++r) {
        for(int c=0; c<12; ++c) {
            if (r < MASK_RAW.size() && c < MASK_RAW[r].size()) {
                if (MASK_RAW[r][c] == '0') {
                    is_template[r][c] = true;
                }
            }
        }
    }
}

// ---------------- Solver ----------------

// Quick check of constraints
bool propagate(vector<EdgeCoord>& dirty_edges) {
    int head = 0;
    while(head < dirty_edges.size()) {
        EdgeCoord ec = dirty_edges[head++];
        
        // Check incident cells
        int cells[2][2];
        int num_cells = 0;
        if (ec.t == 'H') {
            if (ec.r > 0) { cells[num_cells][0] = ec.r-1; cells[num_cells][1] = ec.c; num_cells++; }
            if (ec.r < 12) { cells[num_cells][0] = ec.r; cells[num_cells][1] = ec.c; num_cells++; }
        } else {
            if (ec.c > 0) { cells[num_cells][0] = ec.r; cells[num_cells][1] = ec.c-1; num_cells++; }
            if (ec.c < 12) { cells[num_cells][0] = ec.r; cells[num_cells][1] = ec.c; num_cells++; }
        }

        for(int i=0; i<num_cells; ++i) {
            int r = cells[i][0];
            int c = cells[i][1];
            if (grid_clues[r][c] == -1) continue;
            int on = 0, off = 0, unk = 0;
            int* vals[4] = { &H[r][c], &H[r+1][c], &V[r][c], &V[r][c+1] };
            for(int k=0; k<4; ++k) {
                if (*vals[k] == 1) on++;
                else if (*vals[k] == 2) off++;
                else unk++;
            }
            int target = grid_clues[r][c];
            if (on > target) return false;
            if (on + unk < target) return false;
            if (unk > 0) {
                if (on == target) {
                     for(int k=0; k<4; ++k) if (*vals[k] == 0) {
                         *vals[k] = 2;
                         dirty_edges.push_back( (k<2) ? EdgeCoord{'H', r+k, c} : EdgeCoord{'V', r, c+(k-2)} );
                     }
                } else if (on + unk == target) {
                     for(int k=0; k<4; ++k) if (*vals[k] == 0) {
                         *vals[k] = 1;
                         dirty_edges.push_back( (k<2) ? EdgeCoord{'H', r+k, c} : EdgeCoord{'V', r, c+(k-2)} );
                     }
                }
            }
        }
        
        // Check incident vertices
        int verts[2][2]; 
        int num_verts = 0;
        if (ec.t == 'H') {
            verts[0][0] = ec.r; verts[0][1] = ec.c;
            verts[1][0] = ec.r; verts[1][1] = ec.c+1;
            num_verts = 2;
        } else {
            verts[0][0] = ec.r; verts[0][1] = ec.c;
            verts[1][0] = ec.r+1; verts[1][1] = ec.c;
            num_verts = 2;
        }
        
        for(int i=0; i<num_verts; ++i) {
            int r = verts[i][0];
            int c = verts[i][1];
            int on = 0, off = 0, unk = 0;
            // Up, Down, Left, Right
            int* neighbors[4];
            int cnt = 0;
            if (r>0) neighbors[cnt++] = &V[r-1][c];
            if (r<12) neighbors[cnt++] = &V[r][c];
            if (c>0) neighbors[cnt++] = &H[r][c-1];
            if (c<12) neighbors[cnt++] = &H[r][c];
            
            for(int k=0; k<cnt; ++k) {
                if (*neighbors[k] == 1) on++;
                else if (*neighbors[k] == 2) off++;
                else unk++;
            }
            
            if (on > 2) return false;
            if (on > 0 && on + unk < 2) return false;
            if (unk == 0 && on == 1) return false;
        }
    }
    return true;
}

struct DSU {
    vector<int> p;
    DSU(int n) { p.resize(n); for(int i=0; i<n; ++i) p[i]=i; }
    int find(int i) { return (p[i]==i)?i:(p[i]=find(p[i])); }
    void unite(int i, int j) { p[find(i)] = find(j); }
};

bool verify_solution() {
    int deg[13][13]; memset(deg, 0, sizeof(deg));
    DSU dsu(169);
    int edges = 0;
    
    for(int r=0; r<=12; ++r) for(int c=0; c<12; ++c) {
        if (H[r][c] == 1) {
            deg[r][c]++; deg[r][c+1]++;
            dsu.unite(r*13+c, r*13+c+1);
            edges++;
        } else if (H[r][c] == 0) return false;
    }
    for(int r=0; r<12; ++r) for(int c=0; c<=12; ++c) {
        if (V[r][c] == 1) {
            deg[r][c]++; deg[r+1][c]++;
            dsu.unite(r*13+c, (r+1)*13+c);
            edges++;
        } else if (V[r][c] == 0) return false;
    }
    
    if (edges == 0) return false;
    int start = -1;
    for(int r=0; r<=12; ++r) for(int c=0; c<=12; ++c) {
        if (deg[r][c] != 0 && deg[r][c] != 2) return false;
        if (deg[r][c] == 2) {
            if (start == -1) start = r*13+c;
            else if (dsu.find(r*13+c) != dsu.find(start)) return false;
        }
    }
    
    for(int r=0; r<12; ++r) for(int c=0; c<12; ++c) {
        if (grid_clues[r][c] != -1) {
            int cnt = 0;
            if (H[r][c]==1) cnt++;
            if (H[r+1][c]==1) cnt++;
            if (V[r][c]==1) cnt++;
            if (V[r][c+1]==1) cnt++;
            if (cnt != grid_clues[r][c]) return false;
        }
    }
    
    return true;
}

void solve(int idx) {
    if (sol_count > 1) return;
    
    while(idx < edges_list.size()) {
        EdgeCoord& ec = edges_list[idx];
        int val = (ec.t == 'H') ? H[ec.r][ec.c] : V[ec.r][ec.c];
        if (val == 0) break;
        idx++;
    }
    
    if (idx == edges_list.size()) {
        if (verify_solution()) sol_count++;
        return;
    }
    
    EdgeCoord& ec = edges_list[idx];
    
    State backup;
    memcpy(backup.H, H, sizeof(H));
    memcpy(backup.V, V, sizeof(V));
    
    // Try Line
    if (ec.t == 'H') H[ec.r][ec.c] = 1; else V[ec.r][ec.c] = 1;
    vector<EdgeCoord> q;
    q.push_back(ec);
    
    if (propagate(q)) {
        solve(idx+1);
    }
    
    if (sol_count > 1) return;
    
    memcpy(H, backup.H, sizeof(H));
    memcpy(V, backup.V, sizeof(V));
    
    // Try Cross
    if (ec.t == 'H') H[ec.r][ec.c] = 2; else V[ec.r][ec.c] = 2;
    q.clear();
    q.push_back(ec);
    
    if (propagate(q)) {
        solve(idx+1);
    }
    
    memcpy(H, backup.H, sizeof(H));
    memcpy(V, backup.V, sizeof(V));
}

// ---------------- Generator ----------------

bool gen_loop[13][12];
bool gen_loop_v[12][13];

void generate() {
    memset(gen_loop, 0, sizeof(gen_loop));
    memset(gen_loop_v, 0, sizeof(gen_loop_v));
    
    for(int c=0; c<12; ++c) { gen_loop[0][c] = 1; gen_loop[12][c] = 1; }
    for(int r=0; r<12; ++r) { gen_loop_v[r][0] = 1; gen_loop_v[r][12] = 1; }
    
    int steps = 2000;
    for(int i=0; i<steps; ++i) {
        int r = rand() % 12;
        int c = rand() % 12;
        
        bool e1 = gen_loop[r][c];
        bool e2 = gen_loop[r+1][c];
        bool e3 = gen_loop_v[r][c];
        bool e4 = gen_loop_v[r][c+1];
        
        bool n1=!e1, n2=!e2, n3=!e3, n4=!e4;
        
        auto get_deg = [&](int rr, int cc) {
            int d=0;
            if (rr>0) d+=gen_loop_v[rr-1][cc];
            if (rr<12) d+=gen_loop_v[rr][cc];
            if (cc>0) d+=gen_loop[rr][cc-1];
            if (cc<12) d+=gen_loop[rr][cc];
            return d;
        };
        
        gen_loop[r][c]=n1; gen_loop[r+1][c]=n2; gen_loop_v[r][c]=n3; gen_loop_v[r][c+1]=n4;
        
        if (get_deg(r,c)>2 || get_deg(r,c+1)>2 || get_deg(r+1,c)>2 || get_deg(r+1,c+1)>2) {
             gen_loop[r][c]=e1; gen_loop[r+1][c]=e2; gen_loop_v[r][c]=e3; gen_loop_v[r][c+1]=e4;
             continue;
        }
        
        DSU d(169);
        int edges = 0;
        int u = -1;
        for(int rr=0; rr<=12; ++rr) for(int cc=0; cc<12; ++cc) if(gen_loop[rr][cc]) {
            d.unite(rr*13+cc, rr*13+cc+1); edges++; u=rr*13+cc;
        }
        for(int rr=0; rr<12; ++rr) for(int cc=0; cc<=12; ++cc) if(gen_loop_v[rr][cc]) {
            d.unite(rr*13+cc, (rr+1)*13+cc); edges++; u=rr*13+cc;
        }
        
        if (edges == 0) {
             gen_loop[r][c]=e1; gen_loop[r+1][c]=e2; gen_loop_v[r][c]=e3; gen_loop_v[r][c+1]=e4;
             continue;
        }
        
        bool conn = true;
        int root = d.find(u);
        for(int rr=0; rr<=12; ++rr) for(int cc=0; cc<12; ++cc) if(gen_loop[rr][cc]) if(d.find(rr*13+cc)!=root) conn=false;
        for(int rr=0; rr<12; ++rr) for(int cc=0; cc<=12; ++cc) if(gen_loop_v[rr][cc]) if(d.find(rr*13+cc)!=root) conn=false;
        
        if (!conn) {
             gen_loop[r][c]=e1; gen_loop[r+1][c]=e2; gen_loop_v[r][c]=e3; gen_loop_v[r][c+1]=e4;
        }
    }
}

int main() {
    srand(time(0));
    int t;
    if (!(cin >> t)) return 0;
    task_type = t;
    parse_mask();
    
    for(int r=0; r<=12; ++r) for(int c=0; c<12; ++c) edges_list.push_back({'H', r, c});
    for(int r=0; r<12; ++r) for(int c=0; c<=12; ++c) edges_list.push_back({'V', r, c});
    
    while(true) {
        generate();
        bool fail = false;
        for(int r=0; r<12; ++r) {
            for(int c=0; c<12; ++c) {
                if (is_template[r][c]) {
                    int cnt = 0;
                    if (gen_loop[r][c]) cnt++;
                    if (gen_loop[r+1][c]) cnt++;
                    if (gen_loop_v[r][c]) cnt++;
                    if (gen_loop_v[r][c+1]) cnt++;
                    grid_clues[r][c] = cnt;
                    if (task_type == 1 && cnt == 0) { fail = true; break; }
                } else {
                    grid_clues[r][c] = -1;
                }
            }
            if (fail) break;
        }
        if (fail) continue;
        
        memset(H, 0, sizeof(H));
        memset(V, 0, sizeof(V));
        sol_count = 0;
        solve(0);
        
        if (sol_count == 1) {
            for(int r=0; r<12; ++r) {
                for(int c=0; c<12; ++c) {
                    if (grid_clues[r][c] != -1) cout << grid_clues[r][c];
                    else cout << " ";
                }
                cout << endl;
            }
            break;
        }
    }
    return 0;
}