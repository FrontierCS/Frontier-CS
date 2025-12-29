#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <set>

// A struct for a 2D point with a custom comparator for use in std::set
struct Point {
    int x, y;
    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
};

// Represents one of the 8 possible transformations of a polyomino
struct TransformedPoly {
    std::vector<Point> cells;
    int width, height;
    int R, F; // Rotation and Flip that generated this
};

// Represents an original polyomino from the input
struct OriginalPoly {
    int id;
    int k;
    std::vector<TransformedPoly> transforms;
};

// Represents the final placement of a single polyomino
struct Placement {
    int X, Y, R, F;
};

// Normalizes a polyomino's cell coordinates to be relative to (0,0)
void normalize(std::vector<Point>& cells) {
    if (cells.empty()) return;
    int min_x = cells[0].x, min_y = cells[0].y;
    for (const auto& p : cells) {
        min_x = std::min(min_x, p.x);
        min_y = std::min(min_y, p.y);
    }
    for (auto& p : cells) {
        p.x -= min_x;
        p.y -= min_y;
    }
}

// Generates all unique transformations for a polyomino
void generate_transformations(OriginalPoly& poly, const std::vector<Point>& initial_cells) {
    std::set<std::vector<Point>> unique_forms;

    for (int F = 0; F < 2; ++F) {
        for (int R = 0; R < 4; ++R) {
            TransformedPoly t;
            t.R = R;
            t.F = F;
            t.cells.reserve(poly.k);

            for (const auto& p : initial_cells) {
                int cur_x = p.x, cur_y = p.y;
                if (F == 1) { // Reflection across y-axis
                    cur_x = -cur_x;
                }
                for (int rot = 0; rot < R; ++rot) { // 90-degree clockwise rotations
                    int next_x = cur_y;
                    int next_y = -cur_x;
                    cur_x = next_x;
                    cur_y = next_y;
                }
                t.cells.push_back({cur_x, cur_y});
            }

            normalize(t.cells);
            std::sort(t.cells.begin(), t.cells.end());

            if (unique_forms.find(t.cells) == unique_forms.end()) {
                unique_forms.insert(t.cells);
                t.width = 0; t.height = 0;
                for (const auto& p : t.cells) {
                    t.width = std::max(t.width, p.x + 1);
                    t.height = std::max(t.height, p.y + 1);
                }
                poly.transforms.push_back(t);
            }
        }
    }
}

// Checks if a transformed polyomino can be placed at (X,Y) on the grid
bool is_valid(const TransformedPoly& trans, int X, int Y, const std::vector<std::vector<int>>& grid, int W, int H) {
    for (const auto& cell : trans.cells) {
        int gx = X + cell.x;
        int gy = Y + cell.y;
        if (gx < 0 || gx >= W || gy < 0 || gy >= H || grid[gy][gx] != 0) {
            return false;
        }
    }
    return true;
}

// Places a polyomino on the grid
void place_on_grid(const TransformedPoly& trans, int X, int Y, std::vector<std::vector<int>>& grid, int id) {
    for (const auto& cell : trans.cells) {
        grid[Y + cell.y][X + cell.x] = id;
    }
}

// The core packing algorithm for a given rectangle size (W, H)
std::vector<Placement> try_pack(int W, int H, const std::vector<int>& p_indices, const std::vector<OriginalPoly>& polys_orig) {
    std::vector<std::vector<int>> grid(H, std::vector<int>(W, 0));
    std::vector<Placement> placements(polys_orig.size());
    
    int empty_r_cache = 0;

    for (int p_idx : p_indices) {
        const auto& poly = polys_orig[p_idx];
        bool placed = false;
        
        // Find the first empty cell (r,c)
        int r, c;
        bool found_empty = false;
        for (r = empty_r_cache; r < H; ++r) {
            for (c = 0; c < W; ++c) {
                if (grid[r][c] == 0) {
                    found_empty = true;
                    break;
                }
            }
            if (found_empty) break;
        }
        
        if (!found_empty) return {}; // No empty space left, but piece remains

        empty_r_cache = r;
        
        // Try to place the polyomino by aligning one of its cells with (r,c)
        for (const auto& trans : poly.transforms) {
            for (const auto& cell : trans.cells) {
                int X = c - cell.x;
                int Y = r - cell.y;
                if (is_valid(trans, X, Y, grid, W, H)) {
                    place_on_grid(trans, X, Y, grid, p_idx + 1);
                    placements[p_idx] = {X, Y, trans.R, trans.F};
                    placed = true;
                    goto next_piece;
                }
            }
        }

    next_piece:
        if (!placed) return {}; // Failed to place this piece
    }
    return placements;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<OriginalPoly> polys_orig(n);
    long long total_cells = 0;

    for (int i = 0; i < n; ++i) {
        polys_orig[i].id = i;
        std::cin >> polys_orig[i].k;
        total_cells += polys_orig[i].k;
        std::vector<Point> initial_cells(polys_orig[i].k);
        for (int j = 0; j < polys_orig[i].k; ++j) {
            std::cin >> initial_cells[j].x >> initial_cells[j].y;
        }
        generate_transformations(polys_orig[i], initial_cells);
    }
    
    std::vector<int> p_indices(n);
    std::iota(p_indices.begin(), p_indices.end(), 0);
    std::sort(p_indices.begin(), p_indices.end(), [&](int a, int b) {
        return polys_orig[a].k > polys_orig[b].k;
    });

    long long best_A = -1;
    int best_W = -1, best_H = -1;
    std::vector<Placement> best_placements;

    int side_len = std::ceil(std::sqrt(total_cells));
    int min_w = std::max(1, static_cast<int>(side_len * 0.80));
    int max_w = static_cast<int>(side_len * 1.25);

    for (int W = min_w; W <= max_w; ++W) {
        for (int slack = 0; slack < 6; ++slack) {
            int H = std::ceil(static_cast<double>(total_cells) / W) + slack;
            
            // Try packing into WxH
            long long A = (long long)W * H;
            if (best_A == -1 || A < best_A || (A == best_A && H < best_H)) {
                auto placements = try_pack(W, H, p_indices, polys_orig);
                if (!placements.empty()) {
                    if (best_A == -1 || A < best_A || (A == best_A && H < best_H) || (A == best_A && H == best_H && W < best_W)) {
                        best_A = A; best_W = W; best_H = H; best_placements = placements;
                    }
                }
            }
            
            // Try packing into HxW
            if (W != H) {
                 A = (long long)H * W;
                 if (best_A == -1 || A < best_A || (A == best_A && W < best_H)) {
                    auto placements = try_pack(H, W, p_indices, polys_orig);
                    if (!placements.empty()) {
                         if (best_A == -1 || A < best_A || (A == best_A && W < best_H) || (A == best_A && W == best_H && H < best_W)) {
                            best_A = A; best_W = H; best_H = W; best_placements = placements;
                        }
                    }
                }
            }
        }
    }

    std::cout << best_W << " " << best_H << "\n";
    for (int i = 0; i < n; ++i) {
        const auto& p = best_placements[i];
        std::cout << p.X << " " << p.Y << " " << p.R << " " << p.F << "\n";
    }

    return 0;
}