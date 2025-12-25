#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <set>
#include <map>
#include <deque>

struct Point {
    int x, y;
    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
};

struct Piece {
    int id;
    int k;
    std::vector<Point> cells;
};

struct TransformedPiece {
    int R, F;
    std::vector<Point> cells;
    int width, height;
};

struct Placement {
    int id = -1;
    int X, Y, R, F;
};

std::vector<Point> reflect(const std::vector<Point>& cells) {
    std::vector<Point> reflected_cells;
    reflected_cells.reserve(cells.size());
    for (const auto& p : cells) {
        reflected_cells.push_back({-p.x, p.y});
    }
    return reflected_cells;
}

std::vector<Point> rotate(const std::vector<Point>& cells) {
    std::vector<Point> rotated_cells;
    rotated_cells.reserve(cells.size());
    for (const auto& p : cells) {
        rotated_cells.push_back({p.y, -p.x});
    }
    return rotated_cells;
}

void normalize(std::vector<Point>& cells, int& width, int& height) {
    if (cells.empty()) {
        width = 0;
        height = 0;
        return;
    }
    int min_x = cells[0].x, max_x = cells[0].x;
    int min_y = cells[0].y, max_y = cells[0].y;
    for (size_t i = 1; i < cells.size(); ++i) {
        min_x = std::min(min_x, cells[i].x);
        max_x = std::max(max_x, cells[i].x);
        min_y = std::min(min_y, cells[i].y);
        max_y = std::max(max_y, cells[i].y);
    }
    for (auto& p : cells) {
        p.x -= min_x;
        p.y -= min_y;
    }
    width = max_x - min_x + 1;
    height = max_y - min_y + 1;
    std::sort(cells.begin(), cells.end());
}

std::pair<int, std::vector<Placement>> try_packing(int W, int n, const std::vector<Piece>& pieces, const std::map<int, std::vector<TransformedPiece>>& variants_map) {
    long long total_k = 0;
    for(const auto& p : pieces) total_k += p.k;
    std::vector<int> skyline(W, 0);
    int H_max_guess = (int)(total_k / (double)W * 1.5) + 20;
    std::vector<std::vector<int>> grid(H_max_guess, std::vector<int>(W, -1));
    std::vector<Placement> placements(n);

    for (const auto& piece : pieces) {
        int best_score = 1e9;
        int best_x = -1, best_y = -1;
        const TransformedPiece* best_variant = nullptr;

        const auto& variants = variants_map.at(piece.id);
        for (const auto& variant : variants) {
            if (variant.width > W || variant.width == 0) continue;

            // O(W) sliding window to find best x_offset
            std::deque<int> dq;
            int min_h_val = 1e9;
            int best_x_for_variant = 0;

            for (int i = 0; i < W; ++i) {
                if (!dq.empty() && dq.front() <= i - variant.width) {
                    dq.pop_front();
                }
                while (!dq.empty() && skyline[dq.back()] <= skyline[i]) {
                    dq.pop_back();
                }
                dq.push_back(i);
                if (i >= variant.width - 1) {
                    int current_max_h = skyline[dq.front()];
                    if (current_max_h < min_h_val) {
                        min_h_val = current_max_h;
                        best_x_for_variant = i - variant.width + 1;
                    }
                }
            }
            int x_offset = best_x_for_variant;

            int y_offset = 0;
            for (const auto& cell : variant.cells) {
                y_offset = std::max(y_offset, skyline[x_offset + cell.x] - cell.y);
            }
            y_offset = std::max(0, y_offset);
            
            while (true) {
                bool collision = false;
                int jump_y = y_offset + 1;
                for (const auto& cell : variant.cells) {
                    int gx = x_offset + cell.x;
                    int gy = y_offset + cell.y;
                    if (gy >= grid.size()) {
                        grid.resize(gy + H_max_guess, std::vector<int>(W, -1));
                    }
                    if (grid[gy][gx] != -1) {
                        collision = true;
                        jump_y = std::max(jump_y, skyline[gx] - cell.y);
                    }
                }

                if (!collision) break;
                y_offset = std::max(y_offset + 1, jump_y);
            }

            int score = y_offset + variant.height;
            if (score < best_score) {
                best_score = score;
                best_x = x_offset;
                best_y = y_offset;
                best_variant = &variant;
            }
        }

        if (best_x == -1) {
            return {-1, {}};
        }

        placements[piece.id] = {piece.id, best_x, best_y, best_variant->R, best_variant->F};
        for (const auto& cell : best_variant->cells) {
            int gx = best_x + cell.x;
            int gy = best_y + cell.y;
            if (gy >= grid.size()) {
                grid.resize(gy + 1, std::vector<int>(W, -1));
            }
            grid[gy][gx] = piece.id;
            skyline[gx] = std::max(skyline[gx], gy + 1);
        }
    }

    int H = 0;
    for (int h : skyline) H = std::max(H, h);
    return {H, placements};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<Piece> pieces(n);
    long long total_cells = 0;
    for (int i = 0; i < n; ++i) {
        pieces[i].id = i;
        std::cin >> pieces[i].k;
        pieces[i].cells.resize(pieces[i].k);
        for (int j = 0; j < pieces[i].k; ++j) {
            std::cin >> pieces[i].cells[j].x >> pieces[i].cells[j].y;
        }
        total_cells += pieces[i].k;
    }

    std::map<int, std::vector<TransformedPiece>> variants_map;
    for (const auto& piece : pieces) {
        std::set<std::vector<Point>> unique_forms;
        for (int F = 0; F < 2; ++F) {
            std::vector<Point> current_cells = piece.cells;
            if (F == 1) current_cells = reflect(current_cells);
            for (int R = 0; R < 4; ++R) {
                int w, h;
                normalize(current_cells, w, h);
                if (unique_forms.find(current_cells) == unique_forms.end()) {
                    unique_forms.insert(current_cells);
                    variants_map[piece.id].push_back({R, F, current_cells, w, h});
                }
                current_cells = rotate(current_cells);
            }
        }
    }

    std::sort(pieces.begin(), pieces.end(), [](const Piece& a, const Piece& b) {
        if (a.k != b.k) return a.k > b.k;
        return a.id < b.id;
    });

    long long min_area = -1;
    int best_W = -1, best_H = -1;
    std::vector<Placement> best_placements;

    int max_piece_dim = 0;
    for(const auto& p_var : variants_map){
        for(const auto& var : p_var.second){
            max_piece_dim = std::max({max_piece_dim, var.width, var.height});
        }
    }

    int W_start = std::max(max_piece_dim, (int)sqrt(total_cells * 0.9));
    int W_end = std::max(W_start, (int)sqrt(total_cells * 1.4));

    int num_tries = std::min(40, W_end - W_start + 1);
    if(n >= 5000) num_tries = std::min(20, W_end - W_start + 1);

    for (int i = 0; i < num_tries; ++i) {
        int W = W_start + (long long)i * (W_end - W_start) / std::max(1, num_tries - 1);
        if (W <= 0) continue;
        
        auto result = try_packing(W, n, pieces, variants_map);
        int H = result.first;
        if (H != -1) {
            long long area = (long long)W * H;
            if (min_area == -1 || area < min_area || (area == min_area && H < best_H)) {
                min_area = area;
                best_W = W;
                best_H = H;
                best_placements = result.second;
            }
        }
    }

    std::vector<Placement> final_placements(n);
    for(const auto& p : best_placements) {
        if(p.id != -1) final_placements[p.id] = p;
    }

    std::cout << best_W << " " << best_H << std::endl;
    for (int i = 0; i < n; ++i) {
        std::cout << final_placements[i].X << " " << final_placements[i].Y << " " << final_placements[i].R << " " << final_placements[i].F << std::endl;
    }

    return 0;
}