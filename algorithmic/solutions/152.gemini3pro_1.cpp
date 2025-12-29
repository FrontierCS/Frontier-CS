#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>

using namespace std;

// Problem Constants
const int N = 1000;
const int K = 50;
const int CENTER_COORD = 400;

struct Order {
    int id;
    int a, b, c, d;
};

struct Point {
    int x, y;
};

// Global Data
Order orders[N];
const Point OFFICE = {CENTER_COORD, CENTER_COORD};

// Utility Functions
inline int dist(const Point& p1, const Point& p2) {
    return abs(p1.x - p2.x) + abs(p1.y - p2.y);
}

inline bool is_pickup(int node) { return node < 1000; }
inline int get_order_id(int node) { return node < 1000 ? node : node - 1000; }
inline Point get_point(int node) {
    if (node < 1000) return {orders[node].a, orders[node].b};
    else return {orders[node - 1000].c, orders[node - 1000].d};
}

// Random Number Generator
mt19937 rng(12345);

int get_rand(int l, int r) {
    return uniform_int_distribution<int>(l, r)(rng);
}

double get_rand_double() {
    return uniform_real_distribution<double>(0.0, 1.0)(rng);
}

// Solution Structure
struct Solution {
    vector<int> selected_orders; // Indices 0..999
    vector<int> route; // Nodes: 0..999 (P), 1000..1999 (D)
    int total_dist;

    void calc_dist() {
        total_dist = 0;
        Point curr = OFFICE;
        for (int node : route) {
            Point next_p = get_point(node);
            total_dist += dist(curr, next_p);
            curr = next_p;
        }
        total_dist += dist(curr, OFFICE);
    }
};

// Position Lookup
int pos_in_route[N][2]; // [order_id][0=P, 1=D]

void update_pos(const vector<int>& route) {
    for (int i = 0; i < (int)route.size(); ++i) {
        int node = route[i];
        if (node < 1000) pos_in_route[node][0] = i;
        else pos_in_route[node - 1000][1] = i;
    }
}

// Greedy Initialization Helper
Solution generate_greedy_solution(int target_x, int target_y) {
    vector<pair<int, int>> order_scores;
    Point target = {target_x, target_y};
    order_scores.reserve(N);
    for(int i=0; i<N; ++i) {
        int d = dist({orders[i].a, orders[i].b}, target) + dist({orders[i].c, orders[i].d}, target);
        order_scores.push_back({d, i});
    }
    sort(order_scores.begin(), order_scores.end());
    
    Solution sol;
    sol.selected_orders.reserve(K);
    vector<int> pending_pickups;
    vector<int> pending_deliveries;
    
    for(int i=0; i<K; ++i) {
        sol.selected_orders.push_back(order_scores[i].second);
        pending_pickups.push_back(order_scores[i].second);
    }
    
    Point curr = OFFICE;
    sol.route.reserve(2 * K);
    
    while(!pending_pickups.empty() || !pending_deliveries.empty()) {
        int best_idx = -1;
        int min_d = 2e9;
        bool is_p = true;
        
        for(int i=0; i<(int)pending_pickups.size(); ++i) {
            int d = dist(curr, {orders[pending_pickups[i]].a, orders[pending_pickups[i]].b});
            if(d < min_d) {
                min_d = d;
                best_idx = i;
                is_p = true;
            }
        }
        
        for(int i=0; i<(int)pending_deliveries.size(); ++i) {
            int d = dist(curr, {orders[pending_deliveries[i]].c, orders[pending_deliveries[i]].d});
            if(d < min_d) {
                min_d = d;
                best_idx = i;
                is_p = false;
            }
        }
        
        if(is_p) {
            int id = pending_pickups[best_idx];
            sol.route.push_back(id);
            curr = {orders[id].a, orders[id].b};
            pending_pickups.erase(pending_pickups.begin() + best_idx);
            pending_deliveries.push_back(id);
        } else {
            int id = pending_deliveries[best_idx];
            sol.route.push_back(id + 1000);
            curr = {orders[id].c, orders[id].d};
            pending_deliveries.erase(pending_deliveries.begin() + best_idx);
        }
    }
    sol.calc_dist();
    return sol;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    for (int i = 0; i < N; ++i) {
        orders[i].id = i;
        cin >> orders[i].a >> orders[i].b >> orders[i].c >> orders[i].d;
    }

    // Try various starting points for greedy initialization
    Solution best_sol;
    best_sol.total_dist = 2e9;

    for(int x=0; x<=800; x+=200) {
        for(int y=0; y<=800; y+=200) {
            Solution s = generate_greedy_solution(x, y);
            if(s.total_dist < best_sol.total_dist) best_sol = s;
        }
    }

    Solution curr_sol = best_sol;
    update_pos(curr_sol.route);
    
    vector<bool> in_sol(N, false);
    for(int id : curr_sol.selected_orders) in_sol[id] = true;

    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.95; 

    double T0 = 200.0; 
    double T1 = 0.1;
    double temp = T0;
    
    long long iter = 0;

    while (true) {
        iter++;
        if ((iter & 511) == 0) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
            double progress = elapsed / time_limit;
            temp = T0 * pow(T1 / T0, progress);
        }

        int type = get_rand(0, 100);
        
        if (type < 40) { // Shift (Move node)
            int idx_from = get_rand(0, (int)curr_sol.route.size() - 1);
            int idx_to = get_rand(0, (int)curr_sol.route.size());
            
            if (idx_from == idx_to || idx_to == idx_from + 1) continue;

            int node = curr_sol.route[idx_from];
            int order_id = get_order_id(node);
            bool is_p = is_pickup(node);
            
            int actual_insert_idx = idx_to;
            if (idx_to > idx_from) actual_insert_idx--;
            
            bool valid = true;
            if (is_p) {
                int d_pos = pos_in_route[order_id][1];
                if (idx_to > idx_from) {
                     if (d_pos < idx_to) valid = false; 
                } else {
                     // Moving left, P still before D
                }
            } else { // node is D
                int p_pos = pos_in_route[order_id][0];
                if (idx_to <= idx_from) {
                    if (p_pos >= idx_to) valid = false;
                } else {
                    // Moving right, D still after P
                }
            }
            
            if (!valid) continue;

            Point prev = (idx_from == 0) ? OFFICE : get_point(curr_sol.route[idx_from-1]);
            Point curr_p = get_point(node);
            Point next = (idx_from == (int)curr_sol.route.size()-1) ? OFFICE : get_point(curr_sol.route[idx_from+1]);
            int remove_cost = dist(prev, curr_p) + dist(curr_p, next) - dist(prev, next);
            
            Point ins_prev, ins_next;
            if (actual_insert_idx == 0) ins_prev = OFFICE;
            else {
                int old_idx = actual_insert_idx - 1;
                if (old_idx >= idx_from) old_idx++;
                ins_prev = get_point(curr_sol.route[old_idx]);
            }
            
            if (actual_insert_idx == (int)curr_sol.route.size()-1) ins_next = OFFICE;
            else {
                int old_idx = actual_insert_idx;
                if (old_idx >= idx_from) old_idx++;
                ins_next = get_point(curr_sol.route[old_idx]);
            }
            
            int insert_cost = dist(ins_prev, curr_p) + dist(curr_p, ins_next) - dist(ins_prev, ins_next);
            int delta = insert_cost - remove_cost;
            
            if (delta <= 0 || get_rand_double() < exp(-delta / temp)) {
                curr_sol.route.erase(curr_sol.route.begin() + idx_from);
                curr_sol.route.insert(curr_sol.route.begin() + actual_insert_idx, node);
                curr_sol.total_dist += delta;
                update_pos(curr_sol.route);
                if (curr_sol.total_dist < best_sol.total_dist) best_sol = curr_sol;
            }

        } else if (type < 50) { // Swap
             int i = get_rand(0, (int)curr_sol.route.size() - 1);
             int j = get_rand(0, (int)curr_sol.route.size() - 1);
             if (i == j) continue;
             if (i > j) swap(i, j);
             
             int u = curr_sol.route[i];
             int v = curr_sol.route[j];
             int uid = get_order_id(u);
             int vid = get_order_id(v);
             
             if (uid == vid) continue;
             
             bool valid = true;
             if (is_pickup(u)) {
                 if (pos_in_route[uid][1] <= j) valid = false;
             }
             if (!is_pickup(v)) {
                 if (pos_in_route[vid][0] >= i) valid = false;
             }
             
             if (!valid) continue;
             
             Point p_im1 = (i==0) ? OFFICE : get_point(curr_sol.route[i-1]);
             Point p_u = get_point(u);
             Point p_ip1 = get_point(curr_sol.route[i+1]);
             Point p_jm1 = get_point(curr_sol.route[j-1]);
             Point p_v = get_point(v);
             Point p_jp1 = (j==(int)curr_sol.route.size()-1) ? OFFICE : get_point(curr_sol.route[j+1]);

             int cost_old, cost_new;
             if (j == i + 1) { 
                 cost_old = dist(p_im1, p_u) + dist(p_u, p_v) + dist(p_v, p_jp1);
                 cost_new = dist(p_im1, p_v) + dist(p_v, p_u) + dist(p_u, p_jp1);
             } else {
                 cost_old = dist(p_im1, p_u) + dist(p_u, p_ip1) + dist(p_jm1, p_v) + dist(p_v, p_jp1);
                 cost_new = dist(p_im1, p_v) + dist(p_v, p_ip1) + dist(p_jm1, p_u) + dist(p_u, p_jp1);
             }
             
             int delta = cost_new - cost_old;
             if (delta <= 0 || get_rand_double() < exp(-delta / temp)) {
                 swap(curr_sol.route[i], curr_sol.route[j]);
                 curr_sol.total_dist += delta;
                 update_pos(curr_sol.route);
                 if (curr_sol.total_dist < best_sol.total_dist) best_sol = curr_sol;
             }
             
        } else { // Replace Order
             int rem_idx = get_rand(0, K-1);
             int old_id = curr_sol.selected_orders[rem_idx];
             
             int new_id = get_rand(0, N-1);
             while (in_sol[new_id]) new_id = get_rand(0, N-1);
             
             int p_idx = pos_in_route[old_id][0];
             int d_idx = pos_in_route[old_id][1];
             
             Point p_p_prev = (p_idx == 0) ? OFFICE : get_point(curr_sol.route[p_idx-1]);
             Point p_p = get_point(curr_sol.route[p_idx]);
             Point p_p_next = get_point(curr_sol.route[p_idx+1]); 
             
             bool adjacent = (d_idx == p_idx + 1);
             int rem_cost = 0;
             if (adjacent) {
                 Point p_d_next = (d_idx == (int)curr_sol.route.size()-1) ? OFFICE : get_point(curr_sol.route[d_idx+1]);
                 Point p_d = get_point(curr_sol.route[d_idx]);
                 rem_cost = dist(p_p_prev, p_p) + dist(p_p, p_d) + dist(p_d, p_d_next) - dist(p_p_prev, p_d_next);
             } else {
                 rem_cost += dist(p_p_prev, p_p) + dist(p_p, p_p_next) - dist(p_p_prev, p_p_next);
                 Point p_d_prev = get_point(curr_sol.route[d_idx-1]);
                 Point p_d = get_point(curr_sol.route[d_idx]);
                 Point p_d_next = (d_idx == (int)curr_sol.route.size()-1) ? OFFICE : get_point(curr_sol.route[d_idx+1]);
                 rem_cost += dist(p_d_prev, p_d) + dist(p_d, p_d_next) - dist(p_d_prev, p_d_next);
             }
             
             vector<int> temp_route = curr_sol.route;
             temp_route.erase(temp_route.begin() + d_idx);
             temp_route.erase(temp_route.begin() + p_idx);
             
             int L = temp_route.size(); 
             
             vector<int> costP(L + 1);
             Point P_pt = {orders[new_id].a, orders[new_id].b};
             Point D_pt = {orders[new_id].c, orders[new_id].d};
             
             for (int i = 0; i <= L; ++i) {
                 Point prev = (i == 0) ? OFFICE : get_point(temp_route[i-1]);
                 Point next = (i == L) ? OFFICE : get_point(temp_route[i]);
                 costP[i] = dist(prev, P_pt) + dist(P_pt, next) - dist(prev, next);
             }
             
             vector<int> costD(L + 1);
             for (int j = 0; j <= L; ++j) {
                 Point prev = (j == 0) ? OFFICE : get_point(temp_route[j-1]);
                 Point next = (j == L) ? OFFICE : get_point(temp_route[j]);
                 costD[j] = dist(prev, D_pt) + dist(D_pt, next) - dist(prev, next);
             }
             
             int best_add_cost = 2e9;
             int best_i = -1, best_j = -1;
             
             vector<pair<int, int>> minP(L + 2); 
             minP[0] = {2000000000, -1};
             for(int k=0; k<=L; ++k) {
                 if (costP[k] < minP[k].first) minP[k+1] = {costP[k], k};
                 else minP[k+1] = minP[k];
             }
             
             for (int j = 0; j <= L; ++j) {
                 if (j > 0) {
                     int val = minP[j].first + costD[j];
                     if (val < best_add_cost) {
                         best_add_cost = val;
                         best_i = minP[j].second;
                         best_j = j;
                     }
                 }
                 
                 Point prev = (j == 0) ? OFFICE : get_point(temp_route[j-1]);
                 Point next = (j == L) ? OFFICE : get_point(temp_route[j]);
                 int val = dist(prev, P_pt) + dist(P_pt, D_pt) + dist(D_pt, next) - dist(prev, next);
                 if (val < best_add_cost) {
                     best_add_cost = val;
                     best_i = j;
                     best_j = j; 
                 }
             }
             
             int delta = best_add_cost - rem_cost;
             
             if (delta <= 0 || get_rand_double() < exp(-delta / temp)) {
                 curr_sol.route = temp_route;
                 if (best_i == best_j) {
                     curr_sol.route.insert(curr_sol.route.begin() + best_i, new_id + 1000); 
                     curr_sol.route.insert(curr_sol.route.begin() + best_i, new_id); 
                 } else {
                     curr_sol.route.insert(curr_sol.route.begin() + best_j, new_id + 1000);
                     curr_sol.route.insert(curr_sol.route.begin() + best_i, new_id);
                 }
                 
                 curr_sol.selected_orders[rem_idx] = new_id;
                 in_sol[old_id] = false;
                 in_sol[new_id] = true;
                 
                 curr_sol.total_dist += delta; 
                 update_pos(curr_sol.route);
                 if (curr_sol.total_dist < best_sol.total_dist) best_sol = curr_sol;
             }
        }
    }
    
    cout << K;
    for (int id : best_sol.selected_orders) cout << " " << id + 1; 
    cout << endl;
    
    cout << best_sol.route.size() + 2 << " " << OFFICE.x << " " << OFFICE.y;
    for (int node : best_sol.route) {
        Point p = get_point(node);
        cout << " " << p.x << " " << p.y;
    }
    cout << " " << OFFICE.x << " " << OFFICE.y << endl;

    return 0;
}