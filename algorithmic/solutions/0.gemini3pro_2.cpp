#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

struct Point {
    int x, y;
    bool operator<(const Point& other) const {
        if (y != other.y) return y < other.y;
        return x < other.x;
    }
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

struct PieceInfo {
    int id;
    int k;
    Point offset; // vector from (0,0) to min_x, min_y of original
    vector<Point> norm_cells; // original cells minus offset
};

struct Variant {
    int f, r;
    vector<Point> cells_rel; // coordinates relative to the head (which is at 0,0)
    Point head_orig_norm; // The coordinate of the head in the normalized frame (before F, R)
                          // Wait, we need head in the Transformed Normalized frame to compute T_logic?
                          // Let's store head in Transformed Normalized frame.
    Point head_trans_norm; 
};

struct CanonShape {
    int k;
    vector<Variant> variants;
    vector<int> piece_indices; // indices into raw_pieces
};

struct Placement {
    int id;
    int tx, ty, r, f;
};

// Global Data
int N;
vector<PieceInfo> pieces;
vector<CanonShape> shapes;
vector<int> shapes_by_size[11];

// Helpers
Point apply_trans(Point p, int f, int r) {
    if (f) p.x = -p.x;
    for (int i = 0; i < r; ++i) {
        int tmp = p.x;
        p.x = p.y;
        p.y = -tmp;
    }
    return p;
}

// Best solution
long long best_A = -1;
int best_W, best_H;
vector<Placement> best_placements;

void solve(int W) {
    if (W < 1) return;
    
    vector<vector<bool>> grid;
    // Pre-allocate a reasonable amount to avoid reallocs
    grid.reserve(2 * pieces.size() / W + 100); 
    
    // Copy available pieces
    vector<vector<int>> avail(shapes.size());
    for(size_t i=0; i<shapes.size(); ++i) avail[i] = shapes[i].piece_indices;
    
    vector<Placement> current_sol(N + 1);
    int placed_cnt = 0;
    
    // Grid cursor
    int gy = 0;
    int gx = 0;
    
    // Ensure at least one row
    grid.push_back(vector<bool>(W, false));
    
    // Main packing loop
    while (placed_cnt < N) {
        // Find next empty cell
        while (true) {
            // Ensure grid rows
            if (gy >= grid.size()) {
                grid.push_back(vector<bool>(W, false));
            }
            if (gx >= W) {
                gx = 0;
                gy++;
                if (gy >= grid.size()) {
                    grid.push_back(vector<bool>(W, false));
                }
            }
            if (!grid[gy][gx]) break;
            gx++;
        }
        
        bool placed = false;
        
        // Try to place a piece anchored at (gx, gy)
        // Prioritize larger pieces
        for (int k = 10; k >= 1; --k) {
            for (int s_idx : shapes_by_size[k]) {
                if (avail[s_idx].empty()) continue;
                
                // Try variants
                for (const auto& var : shapes[s_idx].variants) {
                    bool fits = true;
                    for (const auto& p : var.cells_rel) {
                        int nx = gx + p.x;
                        int ny = gy + p.y;
                        if (nx < 0 || nx >= W) { fits = false; break; }
                        // Check grid occupation
                        // if ny is beyond current size, it's empty
                        if (ny < grid.size() && grid[ny][nx]) { fits = false; break; }
                    }
                    
                    if (fits) {
                        // Place it
                        int p_idx = avail[s_idx].back();
                        avail[s_idx].pop_back();
                        
                        // Mark grid
                        for (const auto& p : var.cells_rel) {
                            int nx = gx + p.x;
                            int ny = gy + p.y;
                            while (ny >= grid.size()) grid.push_back(vector<bool>(W, false));
                            grid[ny][nx] = true;
                        }
                        
                        // Calculate output translation
                        // T_out = T_logic - Trans(Offset)
                        // T_logic = (gx, gy) - head_trans_norm
                        
                        int t_log_x = gx - var.head_trans_norm.x;
                        int t_log_y = gy - var.head_trans_norm.y;
                        
                        Point off_trans = apply_trans(pieces[p_idx].offset, var.f, var.r);
                        
                        current_sol[pieces[p_idx].id] = {pieces[p_idx].id, t_log_x - off_trans.x, t_log_y - off_trans.y, var.r, var.f};
                        
                        placed = true;
                        placed_cnt++;
                        break;
                    }
                }
                if (placed) break;
            }
            if (placed) break;
        }
        
        if (!placed) {
            // Waste this cell
            grid[gy][gx] = true;
        }
    }
    
    // Calculate H
    int H = grid.size();
    while (H > 0) {
        bool empty = true;
        for (int x = 0; x < W; ++x) if (grid[H-1][x]) empty = false;
        if (empty) H--;
        else break;
    }
    if (H == 0) H = 1;
    
    long long area = (long long)W * H;
    if (best_A == -1 || area < best_A || (area == best_A && H < best_H)) {
        best_A = area;
        best_W = W;
        best_H = H;
        best_placements = current_sol;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N)) return 0;
    
    pieces.resize(N);
    long long total_cells = 0;
    map<vector<Point>, int> sig_map;
    
    for (int i = 0; i < N; ++i) {
        pieces[i].id = i + 1;
        int k; cin >> k;
        pieces[i].k = k;
        total_cells += k;
        
        int min_x = 1e9, min_y = 1e9;
        vector<Point> raw(k);
        for (int j = 0; j < k; ++j) {
            cin >> raw[j].x >> raw[j].y;
            if (raw[j].x < min_x) min_x = raw[j].x;
            if (raw[j].y < min_y) min_y = raw[j].y;
        }
        pieces[i].offset = {min_x, min_y};
        for (int j = 0; j < k; ++j) {
            raw[j].x -= min_x;
            raw[j].y -= min_y;
        }
        pieces[i].norm_cells = raw;
        
        // Canonical signature: Smallest sorted normalized vector of points among all 8 transforms
        vector<Point> best_sig;
        bool first = true;
        
        for (int f = 0; f < 2; ++f) {
            for (int r = 0; r < 4; ++r) {
                vector<Point> pts = pieces[i].norm_cells;
                for (auto& p : pts) p = apply_trans(p, f, r);
                
                // Re-normalize bbox
                int mx = 1e9, my = 1e9;
                for (auto& p : pts) {
                    if (p.x < mx) mx = p.x;
                    if (p.y < my) my = p.y;
                }
                for (auto& p : pts) {
                    p.x -= mx;
                    p.y -= my;
                }
                sort(pts.begin(), pts.end());
                
                if (first || pts < best_sig) {
                    best_sig = pts;
                    first = false;
                }
            }
        }
        
        int s_idx;
        if (sig_map.find(best_sig) == sig_map.end()) {
            s_idx = shapes.size();
            sig_map[best_sig] = s_idx;
            
            CanonShape cs;
            cs.k = k;
            
            // Generate Rooted Variants
            // Based on this piece's norm_cells geometry
            vector<Point> base = pieces[i].norm_cells;
            
            // Collect unique relative shapes
            // Store as sorted vectors to check uniqueness
            vector<vector<Point>> seen_rel_shapes;
            
            for (int f = 0; f < 2; ++f) {
                for (int r = 0; r < 4; ++r) {
                    vector<Point> pts = base;
                    for (auto& p : pts) p = apply_trans(p, f, r);
                    
                    // Find head (min y, then min x)
                    Point head = {10000, 10000};
                    for (auto& p : pts) {
                        if (p < head) head = p;
                    }
                    
                    Variant v;
                    v.f = f;
                    v.r = r;
                    v.head_trans_norm = head;
                    
                    for (auto& p : pts) {
                        v.cells_rel.push_back({p.x - head.x, p.y - head.y});
                    }
                    
                    // Check uniqueness
                    vector<Point> sorted_rel = v.cells_rel;
                    sort(sorted_rel.begin(), sorted_rel.end());
                    
                    bool exists = false;
                    for (const auto& s : seen_rel_shapes) {
                        if (s == sorted_rel) {
                            exists = true;
                            break;
                        }
                    }
                    
                    if (!exists) {
                        seen_rel_shapes.push_back(sorted_rel);
                        cs.variants.push_back(v);
                    }
                }
            }
            shapes.push_back(cs);
            shapes_by_size[k].push_back(s_idx);
        } else {
            s_idx = sig_map[best_sig];
        }
        shapes[s_idx].piece_indices.push_back(i);
    }
    
    // Sort variant lists to possibly optimize? Not strictly needed.
    
    int S = (int)sqrt(total_cells);
    // Try widths
    vector<int> ws;
    ws.push_back(S);
    if (S < 1000) {
        ws.push_back(S + 1);
        ws.push_back(S + 2);
        ws.push_back(max(1, (int)(S * 1.05)));
        ws.push_back(max(1, (int)(S * 1.1)));
    }
    sort(ws.begin(), ws.end());
    ws.erase(unique(ws.begin(), ws.end()), ws.end());
    
    int tries = 0;
    for (int w : ws) {
        solve(w);
        tries++;
        if (tries >= 3 && N > 2000) break;
    }
    
    cout << best_W << " " << best_H << "\n";
    for (int i = 1; i <= N; ++i) {
        cout << best_placements[i].tx << " " << best_placements[i].ty << " " 
             << best_placements[i].r << " " << best_placements[i].f << "\n";
    }
    
    return 0;
}