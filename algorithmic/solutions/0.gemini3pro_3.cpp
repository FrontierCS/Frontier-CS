#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <bitset>
#include <climits>

using namespace std;

struct Point {
    int x, y;
};

struct Polyomino {
    int id;
    int k;
    vector<Point> cells;
};

struct Variant {
    int r, f;
    int w, h;
    int min_x, min_y; 
    vector<Point> cells; 
};

struct Piece {
    int id;
    int original_k;
    vector<Variant> variants;
    int best_var_idx;
    int place_x, place_y;
};

// Max width estimation: 10000 * 10 = 100000 area. sqrt(100000) ~ 316. 
// With 1.5 factor ~ 474. 512 is sufficient.
const int MAX_W = 512;
typedef bitset<MAX_W> RowBits;
vector<RowBits> grid;
vector<int> skyline;
int current_height = 0;

void generate_variants(const Polyomino& p, Piece& piece) {
    struct ShapeRep {
        vector<Point> pts;
        bool operator==(const ShapeRep& other) const {
            if (pts.size() != other.pts.size()) return false;
            for (size_t i = 0; i < pts.size(); ++i) {
                if (pts[i].x != other.pts[i].x || pts[i].y != other.pts[i].y) return false;
            }
            return true;
        }
    };
    vector<ShapeRep> unique_shapes;
    
    // Iterate all 8 transformations
    for (int f = 0; f < 2; ++f) {
        for (int r = 0; r < 4; ++r) {
            int min_x = INT_MAX, min_y = INT_MAX;
            int max_x = INT_MIN, max_y = INT_MIN;
            vector<Point> current_pts;

            for (auto& pt : p.cells) {
                int x = pt.x;
                int y = pt.y;
                
                // Reflection: x -> -x
                if (f) x = -x;
                
                // Rotation: (x, y) -> (y, -x)
                for (int rot = 0; rot < r; ++rot) {
                    int tmp = x;
                    x = y;
                    y = -tmp;
                }
                
                current_pts.push_back({x, y});
                if (x < min_x) min_x = x;
                if (y < min_y) min_y = y;
                if (x > max_x) max_x = x;
                if (y > max_y) max_y = y;
            }

            vector<Point> norm_pts;
            for (auto& pt : current_pts) {
                norm_pts.push_back({pt.x - min_x, pt.y - min_y});
            }
            
            // Check for uniqueness to prune search space
            vector<Point> sorted_pts = norm_pts;
            sort(sorted_pts.begin(), sorted_pts.end(), [](const Point& a, const Point& b) {
                if (a.y != b.y) return a.y < b.y;
                return a.x < b.x;
            });
            
            ShapeRep rep = {sorted_pts};
            bool exists = false;
            for (const auto& existing : unique_shapes) {
                if (existing == rep) {
                    exists = true;
                    break;
                }
            }
            
            if (!exists) {
                unique_shapes.push_back(rep);
                Variant var;
                var.r = r;
                var.f = f;
                var.w = (max_x - min_x) + 1;
                var.h = (max_y - min_y) + 1;
                var.min_x = min_x;
                var.min_y = min_y;
                var.cells = norm_pts;
                piece.variants.push_back(var);
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<Polyomino> input_polys(n);
    long long total_cells = 0;

    for (int i = 0; i < n; ++i) {
        input_polys[i].id = i;
        cin >> input_polys[i].k;
        total_cells += input_polys[i].k;
        for (int j = 0; j < input_polys[i].k; ++j) {
            int x, y;
            cin >> x >> y;
            input_polys[i].cells.push_back({x, y});
        }
    }

    vector<Piece> pieces(n);
    for (int i = 0; i < n; ++i) {
        pieces[i].id = input_polys[i].id;
        pieces[i].original_k = input_polys[i].k;
        generate_variants(input_polys[i], pieces[i]);
    }
    
    // Sort pieces by size descending
    sort(pieces.begin(), pieces.end(), [](const Piece& a, const Piece& b) {
        return a.original_k > b.original_k;
    });

    // Heuristic target width: favor wider rectangle to minimize height
    int target_w = max(12, (int)ceil(sqrt(total_cells) * 1.5));
    if (target_w > MAX_W) target_w = MAX_W;
    
    grid.reserve(max(target_w, (int)(total_cells / target_w * 2)) + 128);
    skyline.assign(target_w, 0);

    int max_x_used = 0;
    int max_y_used = 0;

    for (int i = 0; i < n; ++i) {
        Piece& p = pieces[i];
        
        int best_y = INT_MAX;
        int best_x = -1;
        int best_v = -1;
        
        for (int v = 0; v < p.variants.size(); ++v) {
            const Variant& var = p.variants[v];
            if (var.w > target_w) continue;
            
            // Try all horizontal positions
            for (int x = 0; x <= target_w - var.w; ++x) {
                // Calculate minimum valid y based on skyline
                int start_y = 0;
                for (const auto& cell : var.cells) {
                    int col = x + cell.x;
                    if (skyline[col] - cell.y > start_y) {
                        start_y = skyline[col] - cell.y;
                    }
                }
                
                if (start_y >= best_y) continue; 

                // Search upwards for free spot
                int y = start_y;
                while (y < best_y) {
                    bool collision = false;
                    for (const auto& cell : var.cells) {
                        int cy = y + cell.y;
                        int cx = x + cell.x;
                        if (cy < grid.size()) {
                            if (grid[cy].test(cx)) {
                                collision = true;
                                break;
                            }
                        }
                    }
                    
                    if (!collision) {
                        best_y = y;
                        best_x = x;
                        best_v = v;
                        break;
                    }
                    y++;
                }
            }
        }
        
        // Fallback (should not happen with valid params)
        if (best_v == -1) {
            best_v = 0; best_x = 0; best_y = current_height;
        }

        p.best_var_idx = best_v;
        p.place_x = best_x;
        p.place_y = best_y;
        
        const Variant& var = p.variants[best_v];
        
        // Mark grid
        for (const auto& cell : var.cells) {
            int cx = best_x + cell.x;
            int cy = best_y + cell.y;
            
            if (cy >= grid.size()) {
                grid.resize(cy + 64);
            }
            grid[cy].set(cx);
            
            if (cy + 1 > skyline[cx]) {
                skyline[cx] = cy + 1;
            }
            
            if (cx > max_x_used) max_x_used = cx;
            if (cy > max_y_used) max_y_used = cy;
        }
        if (max_y_used + 1 > current_height) current_height = max_y_used + 1;
    }

    struct Result {
        int x, y, r, f;
    };
    vector<Result> results(n);
    
    for (int i = 0; i < n; ++i) {
        const Piece& p = pieces[i];
        const Variant& v = p.variants[p.best_var_idx];
        
        // Translation needed to move transformed piece from normalized (0,0) to (place_x, place_y)
        // Actual placement = Transform(Original) - (min_x, min_y) + (place_x, place_y)
        // Translation vector T = (place_x - min_x, place_y - min_y)
        
        int tx = p.place_x - v.min_x;
        int ty = p.place_y - v.min_y;
        
        results[p.id] = {tx, ty, v.r, v.f};
    }
    
    cout << (max_x_used + 1) << " " << (max_y_used + 1) << "\n";
    for (int i = 0; i < n; ++i) {
        cout << results[i].x << " " << results[i].y << " " << results[i].r << " " << results[i].f << "\n";
    }

    return 0;
}