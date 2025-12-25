#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <set>
#include <map>

struct Point {
    int x, y;
    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
};

struct Shape {
    std::vector<Point> cells;
    int w = 0, h = 0;
    int r = 0, f = 0;
};

struct Polyomino {
    int id;
    int k;
    std::vector<Point> initial_cells;
    std::vector<Shape> orientations;
};

struct Placement {
    int id;
    int x, y, r, f;
};

void normalize(Shape& s) {
    if (s.cells.empty()) {
        s.w = s.h = 0;
        return;
    }
    int min_x = s.cells[0].x, min_y = s.cells[0].y;
    int max_x = min_x, max_y = min_y;
    for (size_t i = 1; i < s.cells.size(); ++i) {
        min_x = std::min(min_x, s.cells[i].x);
        min_y = std::min(min_y, s.cells[i].y);
        max_x = std::max(max_x, s.cells[i].x);
        max_y = std::max(max_y, s.cells[i].y);
    }
    for (auto& p : s.cells) {
        p.x -= min_x;
        p.y -= min_y;
    }
    s.w = max_x - min_x + 1;
    s.h = max_y - min_y + 1;
    std::sort(s.cells.begin(), s.cells.end());
}

Shape transform(const std::vector<Point>& cells, int r, int f) {
    Shape s;
    s.r = r;
    s.f = f;
    s.cells.reserve(cells.size());
    for (const auto& p : cells) {
        int cur_x = p.x, cur_y = p.y;
        if (f) cur_x = -cur_x;
        for (int i = 0; i < r; ++i) {
            int next_x = cur_y;
            int next_y = -cur_x;
            cur_x = next_x;
            cur_y = next_y;
        }
        s.cells.push_back({cur_x, cur_y});
    }
    return s;
}

void generate_orientations(Polyomino& poly) {
    std::set<std::vector<Point>> unique_shapes;
    for (int f = 0; f < 2; ++f) {
        for (int r = 0; r < 4; ++r) {
            Shape s = transform(poly.initial_cells, r, f);
            normalize(s);
            if (unique_shapes.find(s.cells) == unique_shapes.end()) {
                poly.orientations.push_back(s);
                unique_shapes.insert(s.cells);
            }
        }
    }
}

bool can_place(const Shape& shape, int x, int y, int w, int h, const std::vector<std::vector<bool>>& grid) {
    for (const auto& cell : shape.cells) {
        if (grid[y + cell.y][x + cell.x]) {
            return false;
        }
    }
    return true;
}

void place_piece(const Shape& shape, int x, int y, std::vector<std::vector<bool>>& grid) {
    for (const auto& cell : shape.cells) {
        grid[y + cell.y][x + cell.x] = true;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<Polyomino> polyominoes_input(n);
    long long total_cells = 0;
    std::map<std::vector<Point>, std::vector<Shape>> canonical_forms;

    for (int i = 0; i < n; ++i) {
        polyominoes_input[i].id = i;
        std::cin >> polyominoes_input[i].k;
        polyominoes_input[i].initial_cells.resize(polyominoes_input[i].k);
        for (int j = 0; j < polyominoes_input[i].k; ++j) {
            std::cin >> polyominoes_input[i].initial_cells[j].x >> polyominoes_input[i].initial_cells[j].y;
        }
        total_cells += polyominoes_input[i].k;
        
        Shape s;
        s.cells = polyominoes_input[i].initial_cells;
        normalize(s);
        
        if (canonical_forms.find(s.cells) == canonical_forms.end()) {
            generate_orientations(polyominoes_input[i]);
            canonical_forms[s.cells] = polyominoes_input[i].orientations;
        } else {
            polyominoes_input[i].orientations = canonical_forms[s.cells];
        }
    }

    std::sort(polyominoes_input.rbegin(), polyominoes_input.rend(), [](const Polyomino& a, const Polyomino& b) {
        return a.k < b.k;
    });

    long long best_area = -1;
    int best_w = -1, best_h = -1;
    std::vector<Placement> best_placements;

    int min_w_sqrt = std::max(1, static_cast<int>(sqrt(total_cells * 0.85)));
    int max_w_sqrt = static_cast<int>(sqrt(total_cells * 1.35)) + 1;
    
    std::set<int> widths_to_try;
    for (int w = min_w_sqrt; w <= max_w_sqrt; ++w) {
        widths_to_try.insert(w);
    }
    if (widths_to_try.empty()) widths_to_try.insert(1);
    
    for (int w : widths_to_try) {
        if (w <= 0) continue;
        int h_ub = (total_cells / w) * 1.5 + 20;
        if(n > 2000) h_ub = (total_cells / w) * 1.3 + 20;


        std::vector<std::vector<bool>> grid(h_ub, std::vector<bool>(w, false));
        std::vector<Placement> current_placements;
        int max_y_coord = 0;
        bool possible = true;
        
        for (const auto& poly : polyominoes_input) {
            int final_y = -1, final_x = -1;
            const Shape* final_shape = nullptr;

            for (const auto& shape : poly.orientations) {
                if (shape.w > w) continue;

                for (int y = 0; y <= h_ub - shape.h; ++y) {
                    for (int x = 0; x <= w - shape.w; ++x) {
                        if (can_place(shape, x, y, w, h_ub, grid)) {
                            if (final_y == -1 || y < final_y || (y == final_y && x < final_x)) {
                                final_y = y;
                                final_x = x;
                                final_shape = &shape;
                            }
                            goto next_orient;
                        }
                    }
                }
                next_orient:;
            }

            if (final_y == -1) {
                possible = false;
                break;
            }

            place_piece(*final_shape, final_x, final_y, grid);
            current_placements.push_back({poly.id, final_x, final_y, final_shape->r, final_shape->f});
            max_y_coord = std::max(max_y_coord, final_y + final_shape->h);
        }

        if (possible) {
            long long area = (long long)w * max_y_coord;
            if (best_area == -1 || area < best_area ||
                (area == best_area && max_y_coord < best_h) ||
                (area == best_area && max_y_coord == best_h && w < best_w)) {
                best_area = area;
                best_w = w;
                best_h = max_y_coord;
                best_placements = current_placements;
            }
        }
    }

    std::cout << best_w << " " << best_h << std::endl;
    std::vector<Placement> final_placements(n);
    for (const auto& p : best_placements) {
        final_placements[p.id] = p;
    }
    
    for (int i = 0; i < n; ++i) {
        const auto& p_info = final_placements[i];
        
        Shape s = transform(polyominoes_input[i].initial_cells, p_info.r, p_info.f);
        
        int min_x = 0, min_y = 0;
        if (!s.cells.empty()) {
            min_x = s.cells[0].x;
            min_y = s.cells[0].y;
            for (size_t j = 1; j < s.cells.size(); ++j) {
                min_x = std::min(min_x, s.cells[j].x);
                min_y = std::min(min_y, s.cells[j].y);
            }
        }
        
        std::cout << p_info.x - min_x << " " << p_info.y - min_y << " " << p_info.r << " " << p_info.f << std::endl;
    }

    return 0;
}