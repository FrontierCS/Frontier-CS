#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

const int N_ORDERS = 1000;
const int N_TO_DELIVER = 50;
const int OFFICE_X = 400;
const int OFFICE_Y = 400;

struct Point {
    int x, y;
};

struct Order {
    int id;
    Point p, d;
};

struct PathNode {
    Point pt;
    int order_id;
    bool is_pickup;
};

int manhattan(const Point& a, const Point& b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

long long calculate_total_dist(const vector<PathNode>& path) {
    long long total_dist = 0;
    for (size_t i = 0; i < path.size() - 1; ++i) {
        total_dist += manhattan(path[i].pt, path[i+1].pt);
    }
    return total_dist;
}

void print_solution(const vector<int>& s, const vector<PathNode>& path) {
    vector<int> sorted_s = s;
    sort(sorted_s.begin(), sorted_s.end());
    cout << sorted_s.size();
    for (int id : sorted_s) {
        cout << " " << id;
    }
    cout << endl;
    cout << path.size();
    for (const auto& node : path) {
        cout << " " << node.pt.x << " " << node.pt.y;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<Order> all_orders(N_ORDERS + 1);
    for (int i = 1; i <= N_ORDERS; ++i) {
        all_orders[i].id = i;
        cin >> all_orders[i].p.x >> all_orders[i].p.y >> all_orders[i].d.x >> all_orders[i].d.y;
    }

    Point office = {OFFICE_X, OFFICE_Y};

    // --- Greedy Construction ---
    vector<int> S;
    S.reserve(N_TO_DELIVER);
    vector<bool> used_orders(N_ORDERS + 1, false);
    vector<PathNode> path;
    path.push_back({office, 0, false});
    path.push_back({office, 0, false});

    for (int k = 0; k < N_TO_DELIVER; ++k) {
        long long min_cost_increase = -1;
        int best_order_id = -1;
        int best_p_insert_pos = -1;
        int best_d_insert_pos = -1;

        for (int i = 1; i <= N_ORDERS; ++i) {
            if (used_orders[i]) continue;
            
            Point P = all_orders[i].p;
            Point D = all_orders[i].d;

            long long current_min_increase_for_i = -1;
            int current_p_best_pos = -1;
            int current_d_best_pos = -1;

            for (size_t p_pos = 1; p_pos < path.size(); ++p_pos) {
                // Case 1: P and D in same edge
                long long increase1 = manhattan(path[p_pos-1].pt, P) + manhattan(P, D) + manhattan(D, path[p_pos].pt) - manhattan(path[p_pos-1].pt, path[p_pos].pt);
                if (current_min_increase_for_i == -1 || increase1 < current_min_increase_for_i) {
                    current_min_increase_for_i = increase1;
                    current_p_best_pos = p_pos;
                    current_d_best_pos = p_pos;
                }
                // Case 2: P and D in different edges
                long long p_increase = manhattan(path[p_pos-1].pt, P) + manhattan(P, path[p_pos].pt) - manhattan(path[p_pos-1].pt, path[p_pos].pt);
                for (size_t d_pos = p_pos + 1; d_pos < path.size(); ++d_pos) {
                    long long d_increase = manhattan(path[d_pos-1].pt, D) + manhattan(D, path[d_pos].pt) - manhattan(path[d_pos-1].pt, path[d_pos].pt);
                    long long total_increase = p_increase + d_increase;
                    if (current_min_increase_for_i == -1 || total_increase < current_min_increase_for_i) {
                        current_min_increase_for_i = total_increase;
                        current_p_best_pos = p_pos;
                        current_d_best_pos = d_pos;
                    }
                }
            }
            
            if (min_cost_increase == -1 || current_min_increase_for_i < min_cost_increase) {
                min_cost_increase = current_min_increase_for_i;
                best_order_id = i;
                best_p_insert_pos = current_p_best_pos;
                best_d_insert_pos = current_d_best_pos;
            }
        }

        S.push_back(best_order_id);
        used_orders[best_order_id] = true;
        
        Point P = all_orders[best_order_id].p;
        Point D = all_orders[best_order_id].d;

        if (best_p_insert_pos == best_d_insert_pos) {
            path.insert(path.begin() + best_p_insert_pos, {D, best_order_id, false});
            path.insert(path.begin() + best_p_insert_pos, {P, best_order_id, true});
        } else {
            path.insert(path.begin() + best_d_insert_pos, {D, best_order_id, false});
            path.insert(path.begin() + best_p_insert_pos, {P, best_order_id, true});
        }
    }

    long long current_score = calculate_total_dist(path);
    vector<int> best_S = S;
    vector<PathNode> best_path = path;
    long long best_score = current_score;

    vector<int> p_pos(N_ORDERS + 1), d_pos(N_ORDERS + 1);
    auto update_pos_maps = [&](const vector<PathNode>& p) {
        for (size_t i = 0; i < p.size(); ++i) {
            if (p[i].order_id == 0) continue;
            if (p[i].is_pickup) p_pos[p[i].order_id] = i;
            else d_pos[p[i].order_id] = i;
        }
    };
    update_pos_maps(path);

    int time_limit_ms = 2800;
    while (chrono::duration_cast<chrono::milliseconds>(chrono::high_resolution_clock::now() - start_time).count() < time_limit_ms) {
        
        int move_type = uniform_int_distribution<int>(0, 3)(rng);

        if (move_type == 0) { // 2-opt
            if (path.size() <= 4) continue;
            int i = uniform_int_distribution<int>(1, path.size() - 3)(rng);
            int j = uniform_int_distribution<int>(i + 1, path.size() - 2)(rng);

            bool ok = true;
            for (int order_id : S) {
                if (p_pos[order_id] >= i && p_pos[order_id] <= j && d_pos[order_id] >= i && d_pos[order_id] <= j) {
                    ok = false;
                    break;
                }
            }
            if (!ok) continue;

            vector<PathNode> next_path = path;
            reverse(next_path.begin() + i, next_path.begin() + j + 1);
            long long next_score = calculate_total_dist(next_path);

            if (next_score < current_score) {
                path = next_path;
                current_score = next_score;
                update_pos_maps(path);
            }
        } else if (move_type == 1) { // relocate P
            int order_to_move = S[uniform_int_distribution<int>(0, S.size() - 1)(rng)];
            int current_p = p_pos[order_to_move];
            int current_d = d_pos[order_to_move];
            if (current_d - current_p <= 1) continue;

            int new_p = uniform_int_distribution<int>(1, current_d)(rng);
            if (new_p == current_p) continue;
            
            vector<PathNode> next_path = path;
            PathNode node_p = next_path[current_p];
            next_path.erase(next_path.begin() + current_p);
            next_path.insert(next_path.begin() + new_p, node_p);
            long long next_score = calculate_total_dist(next_path);

            if (next_score < current_score) {
                path = next_path;
                current_score = next_score;
                update_pos_maps(path);
            }
        } else if (move_type == 2) { // relocate D
            int order_to_move = S[uniform_int_distribution<int>(0, S.size() - 1)(rng)];
            int current_p = p_pos[order_to_move];
            int current_d = d_pos[order_to_move];
            if ((int)path.size() - 1 <= current_p + 1) continue;
            
            int new_d = uniform_int_distribution<int>(current_p + 1, path.size() - 1)(rng);
            if (new_d == current_d) continue;

            vector<PathNode> next_path = path;
            PathNode node_d = next_path[current_d];
            next_path.erase(next_path.begin() + current_d);
            next_path.insert(next_path.begin() + new_d, node_d);
            long long next_score = calculate_total_dist(next_path);

            if (next_score < current_score) {
                path = next_path;
                current_score = next_score;
                update_pos_maps(path);
            }
        } else { // swap order
            int s_idx = uniform_int_distribution<int>(0, S.size() - 1)(rng);
            int order_out_id = S[s_idx];
            int order_in_id;
            do {
                order_in_id = uniform_int_distribution<int>(1, N_ORDERS)(rng);
            } while (used_orders[order_in_id]);
            
            vector<PathNode> temp_path = path;
            int pos_p = p_pos[order_out_id];
            int pos_d = d_pos[order_out_id];
            
            temp_path.erase(temp_path.begin() + max(pos_p, pos_d));
            temp_path.erase(temp_path.begin() + min(pos_p, pos_d));
            
            Point P_in = all_orders[order_in_id].p;
            Point D_in = all_orders[order_in_id].d;
            long long min_increase = -1;
            int best_p_pos = -1, best_d_pos = -1;

            for (size_t p_pos_ = 1; p_pos_ < temp_path.size(); ++p_pos_) {
                long long increase1 = manhattan(temp_path[p_pos_-1].pt, P_in) + manhattan(P_in, D_in) + manhattan(D_in, temp_path[p_pos_].pt) - manhattan(temp_path[p_pos_-1].pt, temp_path[p_pos_].pt);
                if (min_increase == -1 || increase1 < min_increase) {
                    min_increase = increase1;
                    best_p_pos = p_pos_;
                    best_d_pos = p_pos_;
                }
                long long p_increase = manhattan(temp_path[p_pos_-1].pt, P_in) + manhattan(P_in, temp_path[p_pos_].pt) - manhattan(temp_path[p_pos_-1].pt, temp_path[p_pos_].pt);
                for (size_t d_pos_ = p_pos_ + 1; d_pos_ < temp_path.size(); ++d_pos_) {
                    long long d_increase = manhattan(temp_path[d_pos_-1].pt, D_in) + manhattan(D_in, temp_path[d_pos_].pt) - manhattan(temp_path[d_pos_-1].pt, temp_path[d_pos_].pt);
                    if (min_increase == -1 || p_increase + d_increase < min_increase) {
                        min_increase = p_increase + d_increase;
                        best_p_pos = p_pos_;
                        best_d_pos = d_pos_;
                    }
                }
            }
            
            long long next_score = calculate_total_dist(temp_path) + min_increase;

            if (next_score < current_score) {
                path = temp_path;
                if (best_p_pos == best_d_pos) {
                    path.insert(path.begin() + best_p_pos, {D_in, order_in_id, false});
                    path.insert(path.begin() + best_p_pos, {P_in, order_in_id, true});
                } else {
                    path.insert(path.begin() + best_d_pos, {D_in, order_in_id, false});
                    path.insert(path.begin() + best_p_pos, {P_in, order_in_id, true});
                }
                S[s_idx] = order_in_id;
                used_orders[order_out_id] = false;
                used_orders[order_in_id] = true;
                update_pos_maps(path);
                current_score = next_score;
            }
        }

        if (current_score < best_score) {
            best_score = current_score;
            best_S = S;
            best_path = path;
        }
    }
    
    print_solution(best_S, best_path);

    return 0;
}