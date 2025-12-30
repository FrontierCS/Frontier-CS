#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <numeric>

// Using (r, c) for (row, column) to be clear.
// The problem statement uses (i, j) where i is down, j is right.
// So i corresponds to row, j to column.
// My (r, c) is consistent with this.
// Truck position: (cr, cc) for (current_row, current_column)

const int N = 20;
int initial_h[N][N];
int h[N][N];
int cr, cc;
long long load;
std::vector<std::string> ops;

struct PosCell {
    int r, c, initial_h_val;
};

struct NegCell {
    int r, c;
};

int dist(int r1, int c1, int r2, int c2) {
    return std::abs(r1 - r2) + std::abs(c1 - c2);
}

void move_to(int tr, int tc) {
    while (cr < tr) {
        ops.push_back("D");
        cr++;
    }
    while (cr > tr) {
        ops.push_back("U");
        cr--;
    }
    while (cc < tc) {
        ops.push_back("R");
        cc++;
    }
    while (cc > tc) {
        ops.push_back("L");
        cc--;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n_dummy;
    std::cin >> n_dummy; // N is fixed at 20

    std::vector<PosCell> pos_cells;
    std::vector<NegCell> neg_cells;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            std::cin >> initial_h[i][j];
            h[i][j] = initial_h[i][j];
            if (h[i][j] > 0) {
                pos_cells.push_back({i, j, h[i][j]});
            } else if (h[i][j] < 0) {
                neg_cells.push_back({i, j});
            }
        }
    }

    cr = 0;
    cc = 0;
    load = 0;

    int num_pos_cells_processed = 0;
    while (num_pos_cells_processed < pos_cells.size()) {
        // Select best source cell to visit next
        int best_s_idx = -1;
        double min_score = 1e18;

        for (int i = num_pos_cells_processed; i < pos_cells.size(); ++i) {
            auto& s = pos_cells[i];
            int dist_truck_s = dist(cr, cc, s.r, s.c);
            
            int min_dist_s_k = 1e9;
            bool any_sinks_left = false;
            for (const auto& k : neg_cells) {
                if (h[k.r][k.c] < 0) {
                    any_sinks_left = true;
                    min_dist_s_k = std::min(min_dist_s_k, dist(s.r, s.c, k.r, k.c));
                }
            }
            if (!any_sinks_left) {
                min_dist_s_k = 0;
            }

            double score = 100.0 * dist_truck_s + (100.0 + s.initial_h_val) * min_dist_s_k;
            if (score < min_score) {
                min_score = score;
                best_s_idx = i;
            }
        }
        
        std::swap(pos_cells[num_pos_cells_processed], pos_cells[best_s_idx]);
        auto& s = pos_cells[num_pos_cells_processed];
        
        move_to(s.r, s.c);

        int amount_to_load = s.initial_h_val;
        ops.push_back("+" + std::to_string(amount_to_load));
        load += amount_to_load;
        h[s.r][s.c] -= amount_to_load;
        
        num_pos_cells_processed++;

        while (load > 0) {
            int best_k_r = -1, best_k_c = -1;
            int min_dist_k = 1e9;
            
            bool sinks_available = false;
            for(const auto& k : neg_cells) {
                if (h[k.r][k.c] < 0) {
                    sinks_available = true;
                    int d = dist(cr, cc, k.r, k.c);
                    if (d < min_dist_k) {
                        min_dist_k = d;
                        best_k_r = k.r;
                        best_k_c = k.c;
                    }
                }
            }

            if (!sinks_available) {
                break;
            }
            
            move_to(best_k_r, best_k_c);
            
            int needed = -h[cr][cc];
            int amount_to_unload = std::min((long long)needed, load);
            
            ops.push_back("-" + std::to_string(amount_to_unload));
            load -= amount_to_unload;
            h[cr][cc] += amount_to_unload;
        }
    }

    for (const auto& op : ops) {
        std::cout << op << "\n";
    }

    return 0;
}