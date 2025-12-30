#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <set>

struct Point {
    int x, y;
    bool operator<(const Point& other) const {
        if (y != other.y) return y < other.y;
        return x < other.x;
    }
};

struct Orientation {
    std::vector<Point> cells;
    int w, h;
    int R, F;
};

struct Polyomino {
    int id;
    int k;
    std::vector<Orientation> orientations;
};

struct Placement {
    int X, Y, R, F;
};

std::vector<Polyomino> polys;
std::vector<Placement> final_solution;
int n;
int total_cells = 0;
int max_w_overall = 0;
int max_h_overall = 0;

void generate_orientations(Polyomino& poly, const std::vector<Point>& initial_cells) {
    std::set<std::vector<Point>> unique_shapes;

    for (int F = 0; F < 2; ++F) {
        std::vector<Point> current_cells = initial_cells;
        if (F == 1) {
            for (auto& p : current_cells) {
                p.x = -p.x;
            }
        }

        for (int R = 0; R < 4; ++R) {
            if (R > 0) {
                for (auto& p : current_cells) {
                    int old_x = p.x;
                    p.x = p.y;
                    p.y = -old_x;
                }
            }

            int min_x = 1e9, min_y = 1e9;
            for (const auto& p : current_cells) {
                min_x = std::min(min_x, p.x);
                min_y = std::min(min_y, p.y);
            }

            std::vector<Point> normalized_cells;
            int max_x = 0, max_y = 0;
            for (const auto& p : current_cells) {
                normalized_cells.push_back({p.x - min_x, p.y - min_y});
                max_x = std::max(max_x, p.x - min_x);
                max_y = std::max(max_y, p.y - min_y);
            }
            std::sort(normalized_cells.begin(), normalized_cells.end());
            
            if (unique_shapes.find(normalized_cells) == unique_shapes.end()) {
                unique_shapes.insert(normalized_cells);
                poly.orientations.push_back({normalized_cells, max_x + 1, max_y + 1, R, F});
                max_w_overall = std::max(max_w_overall, max_x + 1);
                max_h_overall = std::max(max_h_overall, max_y + 1);
            }
        }
    }
}

bool try_pack(int W, int H, const std::vector<Polyomino>& scheduled_polys, std::vector<Placement>& current_placements) {
    std::vector<char> grid(W * H, 0);
    current_placements.resize(n);

    for (const auto& poly : scheduled_polys) {
        int best_y = H, best_x = W;
        int best_o_idx = -1;

        for (int o_idx = 0; o_idx < poly.orientations.size(); ++o_idx) {
            const auto& o = poly.orientations[o_idx];
            if (o.h > H || o.w > W) continue;

            for (int y = 0; y <= H - o.h; ++y) {
                for (int x = 0; x <= W - o.w; ++x) {
                    bool valid = true;
                    for (const auto& cell : o.cells) {
                        if (grid[(y + cell.y) * W + (x + cell.x)] != 0) {
                            valid = false;
                            break;
                        }
                    }
                    if (valid) {
                        if (y < best_y || (y == best_y && x < best_x)) {
                            best_y = y;
                            best_x = x;
                            best_o_idx = o_idx;
                        }
                        goto next_orientation;
                    }
                }
            }
        next_orientation:;
        }

        if (best_o_idx == -1) {
            return false;
        }

        const auto& best_o = poly.orientations[best_o_idx];
        for (const auto& cell : best_o.cells) {
            grid[(best_y + cell.y) * W + (best_x + cell.x)] = poly.id;
        }
        current_placements[poly.id - 1] = {best_x, best_y, best_o.R, best_o.F};
    }
    
    return true;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;
    polys.resize(n);

    for (int i = 0; i < n; ++i) {
        polys[i].id = i + 1;
        std::cin >> polys[i].k;
        total_cells += polys[i].k;
        std::vector<Point> initial_cells(polys[i].k);
        for (int j = 0; j < polys[i].k; ++j) {
            std::cin >> initial_cells[j].x >> initial_cells[j].y;
        }
        generate_orientations(polys[i], initial_cells);
    }

    std::vector<Polyomino> scheduled_polys = polys;
    std::sort(scheduled_polys.begin(), scheduled_polys.end(), [](const Polyomino& a, const Polyomino& b) {
        return a.k > b.k;
    });

    long long best_A = -1;
    int best_W = -1, best_H = -1;

    for (int H = max_h_overall; H <= total_cells; ++H) {
        int W = std::max(max_w_overall, (total_cells + H - 1) / H);
        
        if (best_A != -1 && (long long)H * W >= best_A) {
            if (H > best_H && H > sqrt(best_A * 1.2) && H > 100) {
                 break;
            }
        }
        
        std::vector<Placement> current_placements;
        while(true) {
            if (best_A != -1 && (long long)W * H >= best_A) {
                break;
            }
            if (try_pack(W, H, scheduled_polys, current_placements)) {
                if (best_A == -1 || (long long)W * H < best_A ||
                    ((long long)W * H == best_A && H < best_H) ||
                    ((long long)W * H == best_A && H == best_H && W < best_W)) 
                {
                    best_A = (long long)W * H;
                    best_W = W;
                    best_H = H;
                    final_solution = current_placements;
                }
                break; 
            }
            W++;
        }
    }

    std::cout << best_W << " " << best_H << "\n";
    for (int i=0; i<n; ++i) {
        std::cout << final_solution[i].X << " " << final_solution[i].Y << " " << final_solution[i].R << " " << final_solution[i].F << "\n";
    }

    return 0;
}