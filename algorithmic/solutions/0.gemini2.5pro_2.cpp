#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

struct Point {
    int x, y;

    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
};

struct Placement {
    int x, y, r, f;
};

struct Piece {
    int shape_id;
    vector<Point> cells;
    int w, h;
    int r, f;
};

map<vector<Point>, int> canonical_forms;
vector<vector<Piece>> unique_shapes;
vector<pair<int, int>> polyominoes;
vector<int> p_indices;

vector<Point> normalize(vector<Point> cells) {
    if (cells.empty()) return {};
    int min_x = cells[0].x, min_y = cells[0].y;
    for (size_t i = 1; i < cells.size(); ++i) {
        min_x = min(min_x, cells[i].x);
        min_y = min(min_y, cells[i].y);
    }
    for (auto& p : cells) {
        p.x -= min_x;
        p.y -= min_y;
    }
    sort(cells.begin(), cells.end());
    return cells;
}

void generate_transformations(const vector<Point>& base_cells, int shape_id) {
    unique_shapes[shape_id].resize(8);
    vector<Point> current_cells = base_cells;

    for (int f = 0; f < 2; ++f) {
        if (f == 1) {
            for (auto& p : current_cells) p.x = -p.x;
        } else {
            current_cells = base_cells;
        }

        for (int r = 0; r < 4; ++r) {
            if (r > 0) {
                for (auto& p : current_cells) {
                    int temp_x = p.x;
                    p.x = p.y;
                    p.y = -temp_x;
                }
            }
            vector<Point> normalized_cells = normalize(current_cells);
            int max_x = 0, max_y = 0;
            for (const auto& p : normalized_cells) {
                max_x = max(max_x, p.x);
                max_y = max(max_y, p.y);
            }
            unique_shapes[shape_id][f * 4 + r] = {
                shape_id, normalized_cells, max_x + 1, max_y + 1, r, f
            };
        }
    }
}

bool can_place(int W, int H, const vector<vector<bool>>& grid, const Piece& piece, int place_x, int place_y) {
    if (place_x < 0 || place_y < 0 || place_x + piece.w > W || place_y + piece.h > H) {
        return false;
    }
    for (const auto& cell : piece.cells) {
        if (grid[place_y + cell.y][place_x + cell.x]) {
            return false;
        }
    }
    return true;
}

void place(vector<vector<bool>>& grid, const Piece& piece, int place_x, int place_y) {
    for (const auto& cell : piece.cells) {
        grid[place_y + cell.y][place_x + cell.x] = true;
    }
}

bool try_pack(int W, int H, int n, vector<Placement>& placements) {
    vector<vector<bool>> grid(H, vector<bool>(W, false));
    placements.resize(n);

    int current_y = 0, current_x = 0;

    for (int poly_idx : p_indices) {
        if (current_y >= H) return false; // Ran out of space
        while (grid[current_y][current_x]) {
            current_x++;
            if (current_x == W) {
                current_x = 0;
                current_y++;
            }
            if (current_y == H) return false;
        }

        int first_empty_y = current_y;
        int first_empty_x = current_x;

        int best_place_y = H, best_place_x = W;
        int best_transform_idx = -1;
        
        int shape_id = polyominoes[poly_idx].second;
        
        for (int i = 0; i < 8; ++i) {
            const auto& piece = unique_shapes[shape_id][i];
            for (const auto& cell : piece.cells) {
                int place_x = first_empty_x - cell.x;
                int place_y = first_empty_y - cell.y;
                if (can_place(W, H, grid, piece, place_x, place_y)) {
                    if (place_y < best_place_y || (place_y == best_place_y && place_x < best_place_x)) {
                        best_place_y = place_y;
                        best_place_x = place_x;
                        best_transform_idx = i;
                    }
                }
            }
        }

        if (best_transform_idx != -1) {
            const auto& best_piece = unique_shapes[shape_id][best_transform_idx];
            place(grid, best_piece, best_place_x, best_place_y);
            placements[poly_idx] = {best_place_x, best_place_y, best_piece.r, best_piece.f};
        } else {
            return false;
        }
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    long long total_cells = 0;
    polyominoes.resize(n);

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        total_cells += k;
        vector<Point> cells(k);
        for (int j = 0; j < k; ++j) cin >> cells[j].x >> cells[j].y;

        vector<Point> canonical;
        vector<Point> temp_cells = cells;

        for (int f = 0; f < 2; ++f) {
            if (f == 1) for (auto& p : temp_cells) p.x = -p.x; else temp_cells = cells;
            for (int r = 0; r < 4; ++r) {
                if (r > 0) for (auto& p : temp_cells) { int temp_x = p.x; p.x = p.y; p.y = -temp_x; }
                vector<Point> normalized = normalize(temp_cells);
                if (canonical.empty() || normalized < canonical) canonical = normalized;
            }
        }
        
        if (canonical_forms.find(canonical) == canonical_forms.end()) {
            int new_shape_id = unique_shapes.size();
            canonical_forms[canonical] = new_shape_id;
            unique_shapes.emplace_back();
            generate_transformations(canonical, new_shape_id);
        }
        polyominoes[i] = {k, canonical_forms[canonical]};
    }
    
    p_indices.resize(n);
    iota(p_indices.begin(), p_indices.end(), 0);
    sort(p_indices.begin(), p_indices.end(), [&](int a, int b) {
        return polyominoes[a].first > polyominoes[b].first;
    });

    long long best_A = -1;
    int best_W = 0, best_H = 0;
    vector<Placement> best_placements;
    
    int max_piece_dim = 0;
    for(const auto& shape_vec : unique_shapes) {
        for(const auto& piece : shape_vec) max_piece_dim = max({max_piece_dim, piece.w, piece.h});
    }

    for (long long A = total_cells; A <= total_cells * 1.2 + 100 ; ++A) {
        vector<pair<int, int>> dimensions;
        for (long long W = sqrt(A); W >= 1; --W) {
            if (A % W == 0) {
                long long H = A / W;
                if (W >= max_piece_dim && H >= max_piece_dim) dimensions.push_back({(int)W, (int)H});
            }
        }

        sort(dimensions.begin(), dimensions.end(), [](auto a, auto b) { return a.second < b.second; });

        for (auto p : dimensions) {
            int W = p.first, H = p.second;
            vector<Placement> placements;
            if (try_pack(W, H, n, placements)) {
                 best_A = A; best_W = W; best_H = H; best_placements = placements;
                 goto found_solution;
            }
            if (W != H) {
                if (try_pack(H, W, n, placements)) {
                    best_A = A; best_W = H; best_H = W; best_placements = placements;
                    goto found_solution;
                }
            }
        }
    }

found_solution:
    if(best_A == -1) {
        int side = sqrt(total_cells * 1.5) + max_piece_dim + 1;
        vector<Placement> placements;
        while(!try_pack(side, side, n, placements)) side++;
        best_W = side; best_H = side; best_placements = placements;
    }

    cout << best_W << " " << best_H << endl;
    for (int i = 0; i < n; ++i) {
        cout << best_placements[i].x << " " << best_placements[i].y << " " << best_placements[i].r << " " << best_placements[i].f << endl;
    }

    return 0;
}