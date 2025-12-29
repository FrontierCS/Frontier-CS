#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <set>

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

struct Variant {
    vector<Point> cells;
    int w, h;
    int R, F; // Rotation, Reflection
    int dx, dy; // Shift applied to normalize
};

struct Poly {
    int id;
    int k;
    vector<Point> original_cells;
    vector<Variant> variants;
};

struct Placement {
    int X, Y, R, F;
};

int N;
vector<Poly> polys;
long long total_area = 0;

// Rotate 90 degrees clockwise: (x, y) -> (y, -x)
Point rotatePoint(Point p, int R) {
    for (int r = 0; r < R; ++r) {
        int old_x = p.x;
        p.x = p.y;
        p.y = -old_x;
    }
    return p;
}

// Reflection across Y axis: (x, y) -> (-x, y)
Point reflectPoint(Point p, int F) {
    if (F) {
        p.x = -p.x;
    }
    return p;
}

void generateVariants(Poly& p) {
    // Generate all 8 combinations of F and R
    // Deduplicate based on the set of normalized cells
    set<vector<Point>> unique_shapes;
    
    for (int F = 0; F <= 1; ++F) {
        for (int R = 0; R <= 3; ++R) {
            vector<Point> current_cells;
            int min_x = 1e9, min_y = 1e9;
            int max_x = -1e9, max_y = -1e9;
            
            // Apply transform: Reflection then Rotation
            for (auto pt : p.original_cells) {
                Point trans = reflectPoint(pt, F);
                trans = rotatePoint(trans, R);
                current_cells.push_back(trans);
                if (trans.x < min_x) min_x = trans.x;
                if (trans.y < min_y) min_y = trans.y;
            }
            
            // Normalize
            for (auto& pt : current_cells) {
                pt.x -= min_x;
                pt.y -= min_y;
                if (pt.x > max_x) max_x = pt.x;
                if (pt.y > max_y) max_y = pt.y;
            }
            
            // Sort cells to compare uniqueness
            vector<Point> sorted_cells = current_cells;
            sort(sorted_cells.begin(), sorted_cells.end());
            
            if (unique_shapes.find(sorted_cells) == unique_shapes.end()) {
                unique_shapes.insert(sorted_cells);
                Variant v;
                v.cells = sorted_cells; 
                v.w = max_x + 1;
                v.h = max_y + 1;
                v.R = R;
                v.F = F;
                v.dx = -min_x;
                v.dy = -min_y;
                p.variants.push_back(v);
            }
        }
    }
}

struct Solution {
    int W, H;
    long long area;
    vector<Placement> placements; // indexed by poly id (0 to N-1)
};

Solution solve(int width_limit, const vector<int>& poly_order) {
    // Initial grid allocation
    // We assume H won't exceed total_area (worst case width 1) but practically much smaller
    int current_grid_h = 200;
    vector<vector<bool>> grid(current_grid_h, vector<bool>(width_limit, false));
    
    int first_free_row = 0;
    vector<Placement> results(N);
    int max_y_reached = 0;
    
    for (int idx : poly_order) {
        const Poly& p = polys[idx];
        bool placed = false;
        
        for (int y = first_free_row; ; ++y) {
            // Expand grid if needed
            if (y + 12 >= (int)grid.size()) { 
                grid.resize(grid.size() * 2, vector<bool>(width_limit, false));
            }
            
            for (int x = 0; x < width_limit; ++x) {
                // Optimization: if cell is occupied, we can't anchor a variant at (x,y) 
                // IF we assume variant covers (0,0). But normalized variant has (0,0) as min_x, min_y.
                // It does NOT necessarily occupy (0,0), but usually it does or close to it.
                // To be safe, we just check collisions.
                
                // Fast skip if the cell itself is occupied (heuristic, might miss some placements where (0,0) is empty in shape)
                // Actually, since normalized shape has min_x=0 and min_y=0, there is AT LEAST one cell with x=0 and one with y=0.
                // But not necessarily at (0,0).
                // However, checking is cheap.
                
                for (const auto& var : p.variants) {
                    if (x + var.w > width_limit) continue;
                    
                    bool fit = true;
                    // Check collision
                    for (const auto& cell : var.cells) {
                        if (grid[y + cell.y][x + cell.x]) {
                            fit = false;
                            break;
                        }
                    }
                    
                    if (fit) {
                        // Place it
                        for (const auto& cell : var.cells) {
                            grid[y + cell.y][x + cell.x] = true;
                            if (y + cell.y > max_y_reached) max_y_reached = y + cell.y;
                        }
                        
                        Placement pl;
                        pl.X = x + var.dx;
                        pl.Y = y + var.dy;
                        pl.R = var.R;
                        pl.F = var.F;
                        results[p.id] = pl;
                        
                        placed = true;
                        break;
                    }
                }
                if (placed) break;
            }
            if (placed) break;
            
            // Update first_free_row
            if (y == first_free_row) {
                bool full = true;
                for (int cx = 0; cx < width_limit; ++cx) {
                    if (!grid[y][cx]) {
                        full = false;
                        break;
                    }
                }
                if (full) first_free_row++;
            }
        }
    }
    
    Solution sol;
    sol.W = width_limit;
    sol.H = max_y_reached + 1;
    sol.area = (long long)sol.W * sol.H;
    sol.placements = results;
    return sol;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N)) return 0;
    
    polys.resize(N);
    for (int i = 0; i < N; ++i) {
        polys[i].id = i;
        cin >> polys[i].k;
        total_area += polys[i].k;
        for (int j = 0; j < polys[i].k; ++j) {
            int x, y;
            cin >> x >> y;
            polys[i].original_cells.push_back({x, y});
        }
        generateVariants(polys[i]);
    }
    
    // Sort polys by size descending
    vector<int> p_order(N);
    for(int i=0; i<N; ++i) p_order[i] = i;
    
    sort(p_order.begin(), p_order.end(), [](int a, int b) {
        if (polys[a].k != polys[b].k)
            return polys[a].k > polys[b].k; 
        return a < b;
    });
    
    int sqrt_a = sqrt(total_area);
    vector<int> widths_to_try;
    
    // Heuristic widths
    int w1 = max(10, (int)(sqrt_a * 1.2)); // Often optimal for greedy packing
    int w2 = max(10, (int)(sqrt_a * 1.0));
    
    widths_to_try.push_back(w1);
    if (w1 != w2) widths_to_try.push_back(w2);
    
    // For very large N, limit to 1 attempt to stay within time limit
    if (N > 2000) {
        widths_to_try.resize(1);
    }
    
    Solution best_sol;
    best_sol.area = -1;
    
    for (int w : widths_to_try) {
        Solution s = solve(w, p_order);
        if (best_sol.area == -1 || s.area < best_sol.area || (s.area == best_sol.area && s.H < best_sol.H)) {
            best_sol = s;
        }
    }
    
    cout << best_sol.W << " " << best_sol.H << "\n";
    for (int i = 0; i < N; ++i) {
        const auto& p = best_sol.placements[i];
        cout << p.X << " " << p.Y << " " << p.R << " " << p.F << "\n";
    }
    
    return 0;
}