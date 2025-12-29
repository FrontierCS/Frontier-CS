#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <numeric>

const int N = 20;

int h[N][N];
int truck_r, truck_c;
int truck_load;
std::vector<std::string> operations;

struct Pos {
    int r, c;
};

struct Source {
    Pos pos;
    int amount;
};

struct Sink {
    Pos pos;
    int amount;
};

int dist(Pos a, Pos b) {
    return std::abs(a.r - b.r) + std::abs(a.c - b.c);
}

void move_to(Pos target) {
    while (truck_r < target.r) {
        operations.push_back("D");
        truck_r++;
    }
    while (truck_r > target.r) {
        operations.push_back("U");
        truck_r--;
    }
    while (truck_c < target.c) {
        operations.push_back("R");
        truck_c++;
    }
    while (truck_c > target.c) {
        operations.push_back("L");
        truck_c--;
    }
}

void do_load(int amount) {
    operations.push_back("+" + std::to_string(amount));
    truck_load += amount;
}

void do_unload(int amount) {
    operations.push_back("-" + std::to_string(amount));
    truck_load -= amount;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n_dummy;
    std::cin >> n_dummy;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            std::cin >> h[i][j];
        }
    }

    truck_r = 0;
    truck_c = 0;
    truck_load = 0;

    while (true) {
        std::vector<Source> sources;
        std::vector<Sink> sinks;
        
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (h[i][j] > 0) {
                    sources.push_back({{i, j}, h[i][j]});
                } else if (h[i][j] < 0) {
                    sinks.push_back({{i, j}, h[i][j]});
                }
            }
        }

        if (sources.empty()) break;

        int best_s_idx = -1;
        long long min_cost_metric = -1;

        for (int i = 0; i < sources.size(); ++i) {
            Pos s_pos = sources[i].pos;
            int s_amount = sources[i].amount;

            int min_dist_st = 1e9;
            if (!sinks.empty()) {
                for (int j = 0; j < sinks.size(); ++j) {
                    min_dist_st = std::min(min_dist_st, dist(s_pos, sinks[j].pos));
                }
            } else {
                 min_dist_st = 0; // Should not happen
            }

            long long dist_truck_s = dist({truck_r, truck_c}, s_pos);
            long long current_cost_metric = dist_truck_s * 100 + (long long)min_dist_st * (100 + s_amount);

            if (best_s_idx == -1 || current_cost_metric < min_cost_metric) {
                min_cost_metric = current_cost_metric;
                best_s_idx = i;
            }
        }
        
        Pos best_s_pos = sources[best_s_idx].pos;
        int best_s_amount = sources[best_s_idx].amount;

        move_to(best_s_pos);
        do_load(best_s_amount);
        h[best_s_pos.r][best_s_pos.c] = 0;

        while (truck_load > 0) {
            if (sinks.empty()) break;
            
            int best_t_idx = -1;
            int min_dist_truck_t = 1e9;

            for (int i = 0; i < sinks.size(); ++i) {
                int d = dist({truck_r, truck_c}, sinks[i].pos);
                if (d < min_dist_truck_t) {
                    min_dist_truck_t = d;
                    best_t_idx = i;
                }
            }
            
            Pos t_pos = sinks[best_t_idx].pos;
            move_to(t_pos);
            
            int unload_amount = std::min(truck_load, -sinks[best_t_idx].amount);
            do_unload(unload_amount);
            h[t_pos.r][t_pos.c] += unload_amount;
            sinks[best_t_idx].amount += unload_amount;

            if (sinks[best_t_idx].amount == 0) {
                sinks.erase(sinks.begin() + best_t_idx);
            }
        }
    }

    for (const auto& op : operations) {
        std::cout << op << "\n";
    }

    return 0;
}