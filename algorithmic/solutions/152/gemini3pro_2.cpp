#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <chrono>
#include <random>

using namespace std;

// Constants
const int NUM_ORDERS = 1000;
const int TARGET_ORDERS = 50;
const int CENTER = 400;

struct Point {
    int x, y;
};

struct Order {
    int id;
    Point pickup;
    Point delivery;
};

Point points[2000]; // 0-999: Pickups, 1000-1999: Deliveries
Order orders[1000];

int dist(const Point& p1, const Point& p2) {
    return abs(p1.x - p2.x) + abs(p1.y - p2.y);
}

int dist(int idx1, int idx2) {
    Point p1 = (idx1 == -1) ? Point{CENTER, CENTER} : points[idx1];
    Point p2 = (idx2 == -1) ? Point{CENTER, CENTER} : points[idx2];
    return dist(p1, p2);
}

// Global random engine
mt19937 rng(12345);

struct Solution {
    vector<int> route; // Stores point indices (0-1999)
    bool in_solution[1000];
    int total_dist;

    Solution() {
        fill(in_solution, in_solution + 1000, false);
        total_dist = 0;
    }

    void calc_dist() {
        total_dist = 0;
        if (route.empty()) return;
        total_dist += dist(-1, route[0]);
        for (size_t i = 0; i < route.size() - 1; ++i) {
            total_dist += dist(route[i], route[i+1]);
        }
        total_dist += dist(route.back(), -1);
    }
    
    // Check if the route is valid (P before D)
    bool is_valid() const {
        if (route.size() != TARGET_ORDERS * 2) return false;
        int pos[2000];
        fill(pos, pos + 2000, -1);
        for(int i=0; i<route.size(); ++i) pos[route[i]] = i;
        
        for(int i=0; i<1000; ++i) {
            if (in_solution[i]) {
                if (pos[i] == -1 || pos[i+1000] == -1) return false;
                if (pos[i] > pos[i+1000]) return false;
            } else {
                if (pos[i] != -1 || pos[i+1000] != -1) return false;
            }
        }
        return true;
    }
};

// O(N^2) greedy insertion to add an order to the route optimally
void add_order_better(Solution& sol, int order_idx) {
    int n = sol.route.size();
    int best_increase = 1e9;
    int best_i = -1, best_j = -1;

    for (int i = 0; i <= n; ++i) {
        int prev_p = (i == 0) ? -1 : sol.route[i-1];
        int next_p = (i == n) ? -1 : sol.route[i];
        int cost_p = dist(prev_p, order_idx) + dist(order_idx, next_p) - dist(prev_p, next_p);
        
        // Case 1: D inserted immediately after P
        {
            int cost = dist(prev_p, order_idx) + dist(order_idx, order_idx+1000) + dist(order_idx+1000, next_p) - dist(prev_p, next_p);
            if (cost < best_increase) {
                best_increase = cost;
                best_i = i;
                best_j = i; // Special marker
            }
        }
        
        // Case 2: D inserted at some k > i (index in original route)
        for (int k = i + 1; k <= n; ++k) {
            int prev_d = sol.route[k-1];
            int next_d = (k == n) ? -1 : sol.route[k];
            int cost_d = dist(prev_d, order_idx + 1000) + dist(order_idx + 1000, next_d) - dist(prev_d, next_d);
            
            if (cost_p + cost_d < best_increase) {
                best_increase = cost_p + cost_d;
                best_i = i;
                best_j = k;
            }
        }
    }
    
    // Apply best
    if (best_i == best_j) {
        // P at i, D at i+1
        sol.route.insert(sol.route.begin() + best_i, order_idx);
        sol.route.insert(sol.route.begin() + best_i + 1, order_idx + 1000);
    } else {
        // P at best_i, D at best_j (which becomes best_j+1)
        sol.route.insert(sol.route.begin() + best_i, order_idx);
        sol.route.insert(sol.route.begin() + best_j + 1, order_idx + 1000);
    }
    sol.in_solution[order_idx] = true;
    sol.total_dist += best_increase;
}

int estimate_insertion_cost(const Solution& sol, int order_idx) {
    // O(N) heuristic: best P, then best D
    int n = sol.route.size();
    int min_p_cost = 1e9;
    int best_p_pos = -1;
    
    for (int i = 0; i <= n; ++i) {
        int prev = (i == 0) ? -1 : sol.route[i-1];
        int next = (i == n) ? -1 : sol.route[i];
        int cost = dist(prev, order_idx) + dist(order_idx, next) - dist(prev, next);
        if (cost < min_p_cost) {
            min_p_cost = cost;
            best_p_pos = i;
        }
    }
    
    int min_d_cost = 1e9;
    
    // Check immediate after P
    int prev_at_p = order_idx;
    int next_at_p = (best_p_pos == n) ? -1 : sol.route[best_p_pos];
    int cost_immediate = dist(prev_at_p, order_idx+1000) + dist(order_idx+1000, next_at_p) - dist(prev_at_p, next_at_p);
    if (cost_immediate < min_d_cost) min_d_cost = cost_immediate;
    
    // Check subsequent positions
    for (int i = best_p_pos + 1; i <= n; ++i) {
        int prev = sol.route[i-1];
        int next = (i == n) ? -1 : sol.route[i];
        int cost = dist(prev, order_idx + 1000) + dist(order_idx + 1000, next) - dist(prev, next);
        if (cost < min_d_cost) min_d_cost = cost;
    }
    
    return min_p_cost + min_d_cost;
}

Solution generate_initial_solution(double randomness = 0.0) {
    Solution sol;
    vector<int> candidates(NUM_ORDERS);
    iota(candidates.begin(), candidates.end(), 0);
    
    for (int k = 0; k < TARGET_ORDERS; ++k) {
        vector<pair<int, int>> best_candidates;
        
        for (int order_idx : candidates) {
            if (sol.in_solution[order_idx]) continue;
            int cost = estimate_insertion_cost(sol, order_idx);
            
            if (best_candidates.size() < 5) {
                best_candidates.push_back({cost, order_idx});
                sort(best_candidates.begin(), best_candidates.end());
            } else if (cost < best_candidates.back().first) {
                best_candidates.back() = {cost, order_idx};
                sort(best_candidates.begin(), best_candidates.end());
            }
        }
        
        int pick = 0;
        if (randomness > 0 && !best_candidates.empty()) {
            uniform_int_distribution<int> d(0, best_candidates.size() - 1);
            pick = d(rng);
        }
        int selected = best_candidates[pick].second;
        
        add_order_better(sol, selected);
    }
    sol.calc_dist(); 
    return sol;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    for (int i = 0; i < NUM_ORDERS; ++i) {
        int a, b, c, d;
        cin >> a >> b >> c >> d;
        points[i] = {a, b};
        points[i + 1000] = {c, d};
        orders[i] = {i, points[i], points[i+1000]};
    }
    
    auto start_time = chrono::high_resolution_clock::now();
    
    Solution best_sol;
    best_sol.total_dist = 2e9;
    
    // Generate initial solutions
    while (true) {
        auto curr = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(curr - start_time).count();
        if (elapsed > 0.2) break;
        
        Solution sol = generate_initial_solution(0.5);
        if (sol.total_dist < best_sol.total_dist) {
            best_sol = sol;
        }
        if (elapsed > 0.1 && best_sol.total_dist < 2e9) break;
    }
    
    Solution curr_sol = best_sol;
    
    double initial_temp = 50.0;
    
    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 255) == 0) {
             auto curr = chrono::high_resolution_clock::now();
             double elapsed = chrono::duration<double>(curr - start_time).count();
             if (elapsed > 1.95) break;
        }
        
        auto curr_time = chrono::high_resolution_clock::now();
        double time_ratio = chrono::duration<double>(curr_time - start_time).count() / 1.95;
        double temp = initial_temp * (1.0 - time_ratio);
        
        int move_type = uniform_int_distribution<int>(0, 10)(rng);
        
        if (move_type < 6) { 
            // SHIFT MOVE
            int n = curr_sol.route.size();
            int idx_from = uniform_int_distribution<int>(0, n - 1)(rng);
            int idx_to = uniform_int_distribution<int>(0, n - 1)(rng);
            if (idx_from == idx_to) continue;
            
            int point = curr_sol.route[idx_from];
            int partner = (point < 1000) ? (point + 1000) : (point - 1000);
            int partner_idx = -1;
            for(int i=0; i<n; ++i) if(curr_sol.route[i] == partner) { partner_idx = i; break; }
            
            bool possible = true;
            if (point < 1000) { // Pickup
                int eff_partner_idx = (partner_idx > idx_from) ? partner_idx - 1 : partner_idx;
                if (idx_to > eff_partner_idx) possible = false;
            } else { // Delivery
                int eff_partner_idx = (partner_idx > idx_from) ? partner_idx - 1 : partner_idx;
                if (idx_to <= eff_partner_idx) possible = false;
            }
            
            if (!possible) continue;
            
            int old_dist = curr_sol.total_dist;
            
            int val = curr_sol.route[idx_from];
            curr_sol.route.erase(curr_sol.route.begin() + idx_from);
            curr_sol.route.insert(curr_sol.route.begin() + idx_to, val);
            
            curr_sol.calc_dist();
            int new_dist = curr_sol.total_dist;
            int delta = new_dist - old_dist;
            
            if (delta <= 0 || bernoulli_distribution(exp(-delta / temp))(rng)) {
                if (new_dist < best_sol.total_dist) best_sol = curr_sol;
            } else {
                curr_sol.route.erase(curr_sol.route.begin() + idx_to);
                curr_sol.route.insert(curr_sol.route.begin() + idx_from, val);
                curr_sol.total_dist = old_dist;
            }

        } else {
            // REPLACE ORDER MOVE
            int n = curr_sol.route.size();
            int rem_idx_in_route = uniform_int_distribution<int>(0, n - 1)(rng);
            int pt = curr_sol.route[rem_idx_in_route];
            int order_rem = (pt >= 1000) ? pt - 1000 : pt;
            
            int p_pos = -1, d_pos = -1;
            for(int i=0; i<n; ++i) {
                if (curr_sol.route[i] == order_rem) p_pos = i;
                if (curr_sol.route[i] == order_rem + 1000) d_pos = i;
            }
            
            int old_dist = curr_sol.total_dist;
            
            if (p_pos > d_pos) swap(p_pos, d_pos); 
            
            curr_sol.route.erase(curr_sol.route.begin() + d_pos);
            curr_sol.route.erase(curr_sol.route.begin() + p_pos);
            curr_sol.in_solution[order_rem] = false;
            
            int order_add = -1;
            int attempts = 0;
            do {
                order_add = uniform_int_distribution<int>(0, NUM_ORDERS - 1)(rng);
                attempts++;
            } while (curr_sol.in_solution[order_add] && attempts < 100);
            
            if (curr_sol.in_solution[order_add]) {
                curr_sol.route.insert(curr_sol.route.begin() + p_pos, order_rem);
                curr_sol.route.insert(curr_sol.route.begin() + d_pos, order_rem + 1000);
                curr_sol.in_solution[order_rem] = true;
                continue; 
            }
            
            add_order_better(curr_sol, order_add); 
            
            int new_dist = curr_sol.total_dist;
            int delta = new_dist - old_dist;
            
            if (delta <= 0 || bernoulli_distribution(exp(-delta / temp))(rng)) {
                if (new_dist < best_sol.total_dist) best_sol = curr_sol;
            } else {
                int np_pos = -1, nd_pos = -1;
                for(int i=0; i<curr_sol.route.size(); ++i) {
                    if (curr_sol.route[i] == order_add) np_pos = i;
                    if (curr_sol.route[i] == order_add + 1000) nd_pos = i;
                }
                if (np_pos > nd_pos) swap(np_pos, nd_pos);
                curr_sol.route.erase(curr_sol.route.begin() + nd_pos);
                curr_sol.route.erase(curr_sol.route.begin() + np_pos);
                curr_sol.in_solution[order_add] = false;
                
                curr_sol.route.insert(curr_sol.route.begin() + p_pos, order_rem);
                curr_sol.route.insert(curr_sol.route.begin() + d_pos, order_rem + 1000);
                curr_sol.in_solution[order_rem] = true;
                curr_sol.total_dist = old_dist;
            }
        }
    }
    
    vector<int> final_orders;
    for(int i=0; i<NUM_ORDERS; ++i) if(best_sol.in_solution[i]) final_orders.push_back(i+1);
    
    cout << final_orders.size();
    for (int id : final_orders) cout << " " << id;
    cout << "\n";
    
    vector<Point> path;
    path.push_back({CENTER, CENTER});
    for (int idx : best_sol.route) {
        path.push_back(points[idx]);
    }
    path.push_back({CENTER, CENTER});
    
    cout << path.size();
    for (const auto& p : path) cout << " " << p.x << " " << p.y;
    cout << "\n";
    
    return 0;
}