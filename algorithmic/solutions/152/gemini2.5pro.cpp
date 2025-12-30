#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <chrono>

using namespace std;

const int OFFICE_X = 400;
const int OFFICE_Y = 400;
const int NUM_ORDERS = 1000;
const int QUOTA = 50;

struct Point {
    int x, y;
};

int manhattan_dist(Point p1, Point p2) {
    return abs(p1.x - p2.x) + abs(p1.y - p2.y);
}

struct Order {
    int id;
    Point rest;
    Point dest;
};

struct TourNode {
    int point_idx;
    int order_id; // 1-indexed
    bool is_rest;
};

vector<Order> all_orders(NUM_ORDERS);
vector<Point> all_points;

vector<int> selected_order_ids;
vector<TourNode> tour;

void read_input() {
    all_points.push_back({OFFICE_X, OFFICE_Y}); // idx 0
    for (int i = 0; i < NUM_ORDERS; ++i) {
        all_orders[i].id = i + 1;
        cin >> all_orders[i].rest.x >> all_orders[i].rest.y >> all_orders[i].dest.x >> all_orders[i].dest.y;
        all_points.push_back(all_orders[i].rest);
        all_points.push_back(all_orders[i].dest);
    }
}

void greedy_construction() {
    vector<bool> used(NUM_ORDERS + 1, false);
    tour.push_back({0, 0, false}); // Start at office
    tour.push_back({0, 0, false}); // End at office

    for (int i = 0; i < QUOTA; ++i) {
        int best_order_idx = -1;
        int best_rest_pos = -1, best_dest_pos = -1;
        long long min_cost_increase = -1;

        for (int j = 0; j < NUM_ORDERS; ++j) {
            if (used[j + 1]) continue;
            
            int rest_pidx = 2 * (j + 1) - 1;
            int dest_pidx = 2 * (j + 1);
            Point rest_pt = all_points[rest_pidx];
            Point dest_pt = all_points[dest_pidx];

            int tour_sz = tour.size();
            vector<long long> rest_insert_costs(tour_sz - 1);
            for (int k = 0; k < tour_sz - 1; ++k) {
                Point p_curr = all_points[tour[k].point_idx];
                Point p_next = all_points[tour[k+1].point_idx];
                rest_insert_costs[k] = manhattan_dist(p_curr, rest_pt) + manhattan_dist(rest_pt, p_next) - manhattan_dist(p_curr, p_next);
            }
            
            vector<long long> dest_insert_costs(tour_sz - 1);
             for (int k = 0; k < tour_sz - 1; ++k) {
                Point p_curr = all_points[tour[k].point_idx];
                Point p_next = all_points[tour[k+1].point_idx];
                dest_insert_costs[k] = manhattan_dist(p_curr, dest_pt) + manhattan_dist(dest_pt, p_next) - manhattan_dist(p_curr, p_next);
            }
            
            long long current_min_cost = -1;
            int current_rest_pos = -1, current_dest_pos = -1;
            
            vector<long long> min_suf_dest_cost = dest_insert_costs;
            for(int k = tour_sz - 3; k >=0; --k) {
                min_suf_dest_cost[k] = min(min_suf_dest_cost[k], min_suf_dest_cost[k+1]);
            }
            
            for (int k = 0; k < tour_sz - 1; ++k) {
                 // Case 1: insert separately
                long long cost1 = rest_insert_costs[k] + min_suf_dest_cost[k];
                if (current_min_cost == -1 || cost1 < current_min_cost) {
                    current_min_cost = cost1;
                    current_rest_pos = k + 1;
                    for(int l=k; l < tour_sz - 1; ++l) {
                        if (dest_insert_costs[l] == min_suf_dest_cost[k]) {
                            current_dest_pos = l + 2;
                            break;
                        }
                    }
                }
                 // Case 2: insert together
                Point p_prev = all_points[tour[k].point_idx];
                Point p_next = all_points[tour[k+1].point_idx];
                long long cost2 = manhattan_dist(p_prev, rest_pt) + manhattan_dist(rest_pt, dest_pt) + manhattan_dist(dest_pt, p_next) - manhattan_dist(p_prev, p_next);
                if (current_min_cost == -1 || cost2 < current_min_cost) {
                    current_min_cost = cost2;
                    current_rest_pos = k + 1;
                    current_dest_pos = k + 2;
                }
            }
            if (min_cost_increase == -1 || current_min_cost < min_cost_increase) {
                min_cost_increase = current_min_cost;
                best_order_idx = j;
                best_rest_pos = current_rest_pos;
                best_dest_pos = current_dest_pos;
            }
        }
        
        TourNode rest_node = {2 * (best_order_idx + 1) - 1, best_order_idx + 1, true};
        TourNode dest_node = {2 * (best_order_idx + 1), best_order_idx + 1, false};
        
        if (best_rest_pos < best_dest_pos) {
            tour.insert(tour.begin() + best_rest_pos, rest_node);
            tour.insert(tour.begin() + best_dest_pos, dest_node);
        } else {
            tour.insert(tour.begin() + best_rest_pos, dest_node);
            tour.insert(tour.begin() + best_rest_pos, rest_node);
        }
        
        selected_order_ids.push_back(best_order_idx + 1);
        used[best_order_idx + 1] = true;
    }
}

void local_search(chrono::high_resolution_clock::time_point start_time) {
    vector<pair<int, int>> order_locs(NUM_ORDERS + 1);

    auto recompute_locs = [&]() {
        for (size_t i = 1; i < tour.size() -1; ++i) {
            if (tour[i].is_rest) order_locs[tour[i].order_id].first = i;
            else order_locs[tour[i].order_id].second = i;
        }
    };
    
    recompute_locs();
    
    bool improved = true;
    while (chrono::duration_cast<chrono::milliseconds>(chrono::high_resolution_clock::now() - start_time).count() < 1900 && improved) {
        improved = false;

        // Relocation
        for (size_t i = 1; i < tour.size() - 1; ++i) {
            TourNode node_to_move = tour[i];
            Point p_i = all_points[node_to_move.point_idx];
            Point p_prev = all_points[tour[i - 1].point_idx];
            Point p_next = all_points[tour[i + 1].point_idx];
            
            long long dist_removed = manhattan_dist(p_prev, p_i) + manhattan_dist(p_i, p_next) - manhattan_dist(p_prev, p_next);
            
            for (size_t j = 0; j < tour.size() - 1; ++j) {
                if (i == j || i == j + 1) continue;
                
                int new_pos = (j < i) ? j + 1 : j;
                
                bool is_valid = true;
                if(node_to_move.is_rest) {
                    int dest_pos = order_locs[node_to_move.order_id].second;
                    int dest_pos_after_removal = (i < dest_pos) ? dest_pos - 1 : dest_pos;
                    if(new_pos > dest_pos_after_removal) is_valid = false;
                } else {
                    int rest_pos = order_locs[node_to_move.order_id].first;
                    int rest_pos_after_removal = (i < rest_pos) ? rest_pos - 1 : rest_pos;
                    if (new_pos <= rest_pos_after_removal) is_valid = false;
                }
                if (!is_valid) continue;

                Point p_j = all_points[tour[j].point_idx];
                Point p_j_next = all_points[tour[j + 1].point_idx];
                long long dist_added = manhattan_dist(p_j, p_i) + manhattan_dist(p_i, p_j_next) - manhattan_dist(p_j, p_j_next);

                if (dist_added < dist_removed) {
                    tour.erase(tour.begin() + i);
                    tour.insert(tour.begin() + j + 1, node_to_move);
                    recompute_locs();
                    improved = true;
                    goto next_iter_reloc;
                }
            }
        }
        next_iter_reloc:;
        if(improved) continue;
        
        // 2-opt
        for (size_t i = 0; i < tour.size() - 2; ++i) {
            for (size_t j = i + 2; j < tour.size() - 1; ++j) {
                
                bool is_valid = true;
                for (int oid : selected_order_ids) {
                    int p_rest = order_locs[oid].first;
                    int p_dest = order_locs[oid].second;
                    if (p_rest > p_dest) swap(p_rest, p_dest);
                    if (p_rest > (int)i && p_dest <= (int)j) {
                        is_valid = false;
                        break;
                    }
                }
                if (!is_valid) continue;

                Point pi = all_points[tour[i].point_idx];
                Point pi1 = all_points[tour[i + 1].point_idx];
                Point pj = all_points[tour[j].point_idx];
                Point pj1 = all_points[tour[j + 1].point_idx];
                
                long long old_dist = manhattan_dist(pi, pi1) + manhattan_dist(pj, pj1);
                long long new_dist = manhattan_dist(pi, pj) + manhattan_dist(pi1, pj1);

                if (new_dist < old_dist) {
                    reverse(tour.begin() + i + 1, tour.begin() + j + 1);
                    recompute_locs();
                    improved = true;
                    goto next_iter_2opt;
                }
            }
        }
        next_iter_2opt:;
    }
}

void output_solution() {
    cout << selected_order_ids.size();
    for (int id : selected_order_ids) {
        cout << " " << id;
    }
    cout << endl;

    cout << tour.size();
    for (const auto& node : tour) {
        cout << " " << all_points[node.point_idx].x << " " << all_points[node.point_idx].y;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    auto start_time = chrono::high_resolution_clock::now();
    
    read_input();
    
    greedy_construction();
    local_search(start_time);
    output_solution();

    return 0;
}