#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <chrono>
#include <random>
#include <iomanip>

using namespace std;

const int N_ORDERS = 1000;
const int N_SELECT = 50;
const int OFFICE_X = 400;
const int OFFICE_Y = 400;

auto start_time = chrono::high_resolution_clock::now();
double TIME_LIMIT_SEC = 2.8;

struct Point {
    int x, y;
};

struct Order {
    int id;
    Point p, d;
    double angle;
};

vector<Order> all_orders(N_ORDERS);
Point office = {OFFICE_X, OFFICE_Y};

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

int manhattan_dist(Point p1, Point p2) {
    return abs(p1.x - p2.x) + abs(p1.y - p2.y);
}

long long calculate_path_dist(const vector<int>& path, const vector<Point>& locations) {
    long long total_dist = 0;
    total_dist += manhattan_dist(office, locations[path[0]]);
    for (size_t i = 0; i < path.size() - 1; ++i) {
        total_dist += manhattan_dist(locations[path[i]], locations[path[i+1]]);
    }
    total_dist += manhattan_dist(locations[path.back()], office);
    return total_dist;
}

struct Solution {
    vector<int> selection;
    vector<int> path;
    long long dist;

    void update_dist(const vector<Point>& locations) {
        dist = calculate_path_dist(path, locations);
    }
};

void build_locations_and_partners(const vector<int>& selection, vector<Point>& locations, vector<int>& partners) {
    locations.assign(2 * N_SELECT + 1, {0,0});
    partners.assign(2 * N_SELECT + 1, 0);
    locations[0] = office;
    for (int i = 0; i < N_SELECT; ++i) {
        locations[i + 1] = all_orders[selection[i]].p;
        locations[i + 1 + N_SELECT] = all_orders[selection[i]].d;
        partners[i + 1] = i + 1 + N_SELECT;
        partners[i + 1 + N_SELECT] = i + 1;
    }
}

vector<int> construct_simple_greedy_path(const vector<Point>& locations) {
    vector<int> p_path, d_path;
    vector<bool> p_visited(N_SELECT + 1, false), d_visited(N_SELECT + 1, false);

    int current_p_idx = 0;
    for(int i = 0; i < N_SELECT; ++i) {
        int best_next = -1;
        int min_dist = 1e9;
        for (int j = 1; j <= N_SELECT; ++j) {
            if (!p_visited[j]) {
                int d = manhattan_dist(locations[current_p_idx], locations[j]);
                if (d < min_dist) {
                    min_dist = d;
                    best_next = j;
                }
            }
        }
        p_path.push_back(best_next);
        p_visited[best_next] = true;
        current_p_idx = best_next;
    }

    int current_d_idx = p_path.back();
    for(int i = 0; i < N_SELECT; ++i) {
        int best_next = -1;
        int min_dist = 1e9;
        for (int j = 1; j <= N_SELECT; ++j) {
            if (!d_visited[j]) {
                int d = manhattan_dist(locations[current_d_idx], locations[j + N_SELECT]);
                if (d < min_dist) {
                    min_dist = d;
                    best_next = j;
                }
            }
        }
        d_path.push_back(best_next + N_SELECT);
        d_visited[best_next] = true;
        current_d_idx = best_next + N_SELECT;
    }

    vector<int> full_path = p_path;
    full_path.insert(full_path.end(), d_path.begin(), d_path.end());
    return full_path;
}

bool is_2opt_move_valid(const vector<int>& path, int i, int j, const vector<int>& partners) {
    vector<bool> in_segment(2 * N_SELECT + 1, false);
    for (int k = i; k <= j; ++k) {
        in_segment[path[k]] = true;
    }
    for (int k = i; k <= j; ++k) {
        if (in_segment[partners[path[k]]]) {
            return false;
        }
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    for (int i = 0; i < N_ORDERS; ++i) {
        all_orders[i].id = i + 1;
        cin >> all_orders[i].p.x >> all_orders[i].p.y >> all_orders[i].d.x >> all_orders[i].d.y;
        all_orders[i].angle = atan2(all_orders[i].p.y - OFFICE_Y, all_orders[i].p.x - OFFICE_X);
    }
    
    vector<Order> sorted_orders = all_orders;
    sort(sorted_orders.begin(), sorted_orders.end(), [](const Order& a, const Order& b){
        return a.angle < b.angle;
    });

    Solution best_sol;
    best_sol.dist = -1;

    int initial_candidates = 200;
    for(int i = 0; i < initial_candidates; ++i) {
        int start_idx = i * (N_ORDERS / initial_candidates);
        Solution current_sol;
        for (int j = 0; j < N_SELECT; ++j) {
            current_sol.selection.push_back(sorted_orders[(start_idx + j) % N_ORDERS].id - 1);
        }

        vector<Point> locations;
        vector<int> partners;
        build_locations_and_partners(current_sol.selection, locations, partners);
        
        current_sol.path = construct_simple_greedy_path(locations);
        current_sol.update_dist(locations);
        
        if (best_sol.dist == -1 || current_sol.dist < best_sol.dist) {
            best_sol = current_sol;
        }
    }

    Solution current_sol = best_sol;
    
    double T_start = 5000;
    double T_end = 1;
    double T = T_start;

    int path_len = 2 * N_SELECT;
    vector<Point> locations;
    vector<int> partners;

    uniform_int_distribution<> path_idx_dist(0, path_len - 1);
    uniform_int_distribution<> order_dist(0, N_ORDERS - 1);
    uniform_int_distribution<> sel_idx_dist(0, N_SELECT - 1);
    uniform_real_distribution<> prob_dist(0.0, 1.0);

    vector<bool> in_selection(N_ORDERS, false);
    for(int s : current_sol.selection) in_selection[s] = true;

    build_locations_and_partners(current_sol.selection, locations, partners);
    
    while(true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration_cast<chrono::duration<double>>(now - start_time).count();
        if (elapsed > TIME_LIMIT_SEC) break;

        T = T_start * pow(T_end / T_start, elapsed / TIME_LIMIT_SEC);

        if (prob_dist(rng) < 0.2) {
            int sel_idx_to_swap = sel_idx_dist(rng);
            int order_out_idx = current_sol.selection[sel_idx_to_swap];

            int order_in_idx;
            do {
                order_in_idx = order_dist(rng);
            } while (in_selection[order_in_idx]);

            long long old_dist = current_sol.dist;
            
            int p_loc_idx = sel_idx_to_swap + 1;
            int d_loc_idx = sel_idx_to_swap + N_SELECT + 1;
            
            Point old_p = locations[p_loc_idx];
            Point old_d = locations[d_loc_idx];
            
            locations[p_loc_idx] = all_orders[order_in_idx].p;
            locations[d_loc_idx] = all_orders[order_in_idx].d;
            
            long long new_dist = calculate_path_dist(current_sol.path, locations);
            
            double delta = new_dist - old_dist;
            if (delta < 0 || prob_dist(rng) < exp(-delta / T)) {
                current_sol.selection[sel_idx_to_swap] = order_in_idx;
                in_selection[order_out_idx] = false;
                in_selection[order_in_idx] = true;
                current_sol.dist = new_dist;

                if (current_sol.dist < best_sol.dist) {
                    best_sol = current_sol;
                }
            } else {
                locations[p_loc_idx] = old_p;
                locations[d_loc_idx] = old_d;
            }

        } else {
            int i = path_idx_dist(rng);
            int j = path_idx_dist(rng);
            if (i == j) continue;
            if (i > j) swap(i, j);

            if (!is_2opt_move_valid(current_sol.path, i, j, partners)) {
                continue;
            }

            Point p_i_before = (i == 0) ? office : locations[current_sol.path[i-1]];
            Point p_i = locations[current_sol.path[i]];
            Point p_j = locations[current_sol.path[j]];
            Point p_j_after = (j == path_len-1) ? office : locations[current_sol.path[j+1]];
            
            long long delta = 0;
            delta -= manhattan_dist(p_i_before, p_i);
            delta -= manhattan_dist(p_j, p_j_after);
            delta += manhattan_dist(p_i_before, p_j);
            delta += manhattan_dist(p_i, p_j_after);
            
            if (delta < 0 || prob_dist(rng) < exp(-delta / T)) {
                reverse(current_sol.path.begin() + i, current_sol.path.begin() + j + 1);
                current_sol.dist += delta;

                if (current_sol.dist < best_sol.dist) {
                    best_sol = current_sol;
                }
            }
        }
    }
    
    cout << N_SELECT;
    for (int s : best_sol.selection) {
        cout << " " << s + 1;
    }
    cout << endl;

    vector<Point> final_locations;
    vector<int> final_partners;
    build_locations_and_partners(best_sol.selection, final_locations, final_partners);

    vector<Point> final_path_coords;
    final_path_coords.push_back(office);
    for (int loc_idx : best_sol.path) {
        final_path_coords.push_back(final_locations[loc_idx]);
    }
    final_path_coords.push_back(office);
    
    cout << final_path_coords.size();
    for(const auto& p : final_path_coords) {
        cout << " " << p.x << " " << p.y;
    }
    cout << endl;

    return 0;
}