#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>

using namespace std;

// Constants
const int N_ORDERS = 1000;
const int K_SELECT = 50;
const int GRID_SIZE = 800;
const int CENTER = 400;

// Data Structures
struct Order {
    int id;
    int a, b, c, d;
};

Order orders[N_ORDERS];

// Distance Function
inline int dist(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

// Global RNG
mt19937 rng(12345);

// Solution State
struct Solution {
    vector<int> selected_orders; // IDs of selected orders
    vector<int> route; // Nodes in the route (value < 1000: Pickup, >= 1000: Delivery)
    int total_dist;

    // Calculate total distance of the route
    void calc_dist() {
        total_dist = 0;
        int cx = CENTER, cy = CENTER;
        for (int node : route) {
            int tx, ty;
            int oid = (node >= 1000) ? node - 1000 : node;
            if (node < 1000) { 
                tx = orders[oid].a;
                ty = orders[oid].b;
            } else { 
                tx = orders[oid].c;
                ty = orders[oid].d;
            }
            total_dist += dist(cx, cy, tx, ty);
            cx = tx;
            cy = ty;
        }
        total_dist += dist(cx, cy, CENTER, CENTER);
    }
};

Solution best_sol;

// Helper to get coordinates of a node
void get_coords(int node, int& x, int& y) {
    int oid = (node >= 1000) ? node - 1000 : node;
    if (node < 1000) { x = orders[oid].a; y = orders[oid].b; }
    else { x = orders[oid].c; y = orders[oid].d; }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Input Reading
    for (int i = 0; i < N_ORDERS; ++i) {
        orders[i].id = i;
        cin >> orders[i].a >> orders[i].b >> orders[i].c >> orders[i].d;
    }

    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.95; // Seconds

    // Initial Heuristic Selection
    // Select orders based on independent round-trip distance from center
    vector<pair<int, int>> initial_candidates;
    for (int i = 0; i < N_ORDERS; ++i) {
        int d = dist(CENTER, CENTER, orders[i].a, orders[i].b) +
                dist(orders[i].a, orders[i].b, orders[i].c, orders[i].d) +
                dist(orders[i].c, orders[i].d, CENTER, CENTER);
        initial_candidates.push_back({d, i});
    }
    sort(initial_candidates.begin(), initial_candidates.end());

    Solution curr_sol;
    vector<bool> is_selected(N_ORDERS, false);
    
    // Construct Initial Solution
    for (int i = 0; i < K_SELECT; ++i) {
        int oid = initial_candidates[i].second;
        curr_sol.selected_orders.push_back(oid);
        is_selected[oid] = true;
        curr_sol.route.push_back(oid);
        curr_sol.route.push_back(oid + 1000);
    }
    
    curr_sol.calc_dist();
    best_sol = curr_sol;

    // Simulated Annealing Parameters
    double T0 = 200.0;
    double T1 = 0.1;
    double T = T0;
    
    int iter = 0;
    
    // Static buffer for 2-opt check
    static bool seen[N_ORDERS];

    while (true) {
        iter++;
        if ((iter & 255) == 0) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
            T = T0 + (T1 - T0) * (elapsed / time_limit);
        }

        int type = rng() % 100;
        
        if (type < 40) { // Route Swap (Swap two nodes)
            int i = rng() % curr_sol.route.size();
            int j = rng() % curr_sol.route.size();
            if (i == j) continue;
            
            int u = curr_sol.route[i];
            int v = curr_sol.route[j];
            int u_ord = (u >= 1000 ? u - 1000 : u);
            int v_ord = (v >= 1000 ? v - 1000 : v);
            
            bool valid = true;
            if (u_ord == v_ord) {
                valid = false; // Cannot swap P and D of same order without violating precedence in most cases
            } else {
                // Check precedence for u
                int u_other_idx = -1;
                for(int k=0; k<curr_sol.route.size(); ++k) {
                    if (k == i || k == j) continue;
                    int node = curr_sol.route[k];
                    int ord = (node >= 1000 ? node - 1000 : node);
                    if (ord == u_ord) u_other_idx = k;
                }
                
                if (u < 1000) { if (j > u_other_idx) valid = false; }
                else { if (j < u_other_idx) valid = false; }
                
                if (valid) {
                    // Check precedence for v
                    int v_other_idx = -1;
                    for(int k=0; k<curr_sol.route.size(); ++k) {
                        if (k == i || k == j) continue;
                        int node = curr_sol.route[k];
                        int ord = (node >= 1000 ? node - 1000 : node);
                        if (ord == v_ord) v_other_idx = k;
                    }
                    if (v < 1000) { if (i > v_other_idx) valid = false; }
                    else { if (i < v_other_idx) valid = false; }
                }
            }
            
            if (!valid) continue;
            
            // Apply Move
            swap(curr_sol.route[i], curr_sol.route[j]);
            int old_dist = curr_sol.total_dist;
            curr_sol.calc_dist();
            int new_dist = curr_sol.total_dist;
            
            if (new_dist < old_dist || bernoulli_distribution(exp((old_dist - new_dist) / T))(rng)) {
                if (new_dist < best_sol.total_dist) best_sol = curr_sol;
            } else {
                swap(curr_sol.route[i], curr_sol.route[j]);
                curr_sol.total_dist = old_dist;
            }

        } else if (type < 70) { // 2-opt (Reverse Subsegment)
             int i = rng() % curr_sol.route.size();
             int j = rng() % curr_sol.route.size();
             if (i > j) swap(i, j);
             if (i == j) continue;
             
             // Check validity: No order can have both P and D within [i, j]
             bool possible = true;
             vector<int> in_range;
             for (int k = i; k <= j; ++k) in_range.push_back(curr_sol.route[k]);
             
             for(int val : in_range) {
                 int oid = (val >= 1000 ? val - 1000 : val);
                 if (seen[oid]) { possible = false; }
                 seen[oid] = true;
             }
             for(int val : in_range) {
                 int oid = (val >= 1000 ? val - 1000 : val);
                 seen[oid] = false; // Reset
             }
             if (!possible) continue;
             
             reverse(curr_sol.route.begin() + i, curr_sol.route.begin() + j + 1);
             int old_dist = curr_sol.total_dist;
             curr_sol.calc_dist();
             int new_dist = curr_sol.total_dist;
             
             if (new_dist < old_dist || bernoulli_distribution(exp((old_dist - new_dist) / T))(rng)) {
                 if (new_dist < best_sol.total_dist) best_sol = curr_sol;
             } else {
                 reverse(curr_sol.route.begin() + i, curr_sol.route.begin() + j + 1);
                 curr_sol.total_dist = old_dist;
             }

        } else if (type < 80) { // Shift (Move node to new position)
            int i = rng() % curr_sol.route.size();
            int k = rng() % curr_sol.route.size(); 
            if (i == k) continue; 
            
            int val = curr_sol.route[i];
            int other_idx = -1;
            int oid = (val >= 1000 ? val - 1000 : val);
            for(int idx=0; idx<curr_sol.route.size(); ++idx) {
                if (idx == i) continue;
                int node = curr_sol.route[idx];
                int node_oid = (node >= 1000 ? node - 1000 : node);
                if (node_oid == oid) { other_idx = idx; break; }
            }
            
            // Adjust index as i will be removed
            int eff_other = (other_idx > i) ? other_idx - 1 : other_idx;
            
            bool valid = true;
            if (val < 1000) { if (k > eff_other) valid = false; } 
            else { if (k <= eff_other) valid = false; }
            
            if (!valid) continue;
            
            curr_sol.route.erase(curr_sol.route.begin() + i);
            curr_sol.route.insert(curr_sol.route.begin() + k, val);
            
            int old_dist = curr_sol.total_dist;
            curr_sol.calc_dist();
            int new_dist = curr_sol.total_dist;
            
             if (new_dist < old_dist || bernoulli_distribution(exp((old_dist - new_dist) / T))(rng)) {
                if (new_dist < best_sol.total_dist) best_sol = curr_sol;
            } else {
                curr_sol.route.erase(curr_sol.route.begin() + k);
                curr_sol.route.insert(curr_sol.route.begin() + i, val);
                curr_sol.total_dist = old_dist;
            }

        } else { // Swap Order (Change Subset)
            int rem_idx = rng() % K_SELECT;
            int rem_oid = curr_sol.selected_orders[rem_idx];
            
            int add_oid = rng() % N_ORDERS;
            if (is_selected[add_oid]) continue;
            
            // Construct route without removed order
            vector<int> new_route;
            new_route.reserve(100);
            for(int val : curr_sol.route) {
                int oid = (val >= 1000 ? val - 1000 : val);
                if (oid != rem_oid) new_route.push_back(val);
            }
            
            // Prepare points for cost calculation
            vector<pair<int,int>> pts;
            pts.push_back({CENTER, CENTER});
            for(int val : new_route) {
                int x, y;
                get_coords(val, x, y);
                pts.push_back({x, y});
            }
            pts.push_back({CENTER, CENTER});
            
            int P_val = add_oid;
            int D_val = add_oid + 1000;
            int Px = orders[add_oid].a, Py = orders[add_oid].b;
            int Dx = orders[add_oid].c, Dy = orders[add_oid].d;
            
            int sz = new_route.size();
            int best_incr = 1e9;
            int best_i = -1, best_j = -1;

            // Find best insertion spots for P and D
            for (int i = 0; i <= sz; ++i) {
                int cost_P = dist(pts[i].first, pts[i].second, Px, Py) + 
                             dist(Px, Py, pts[i+1].first, pts[i+1].second) -
                             dist(pts[i].first, pts[i].second, pts[i+1].first, pts[i+1].second);
                
                for (int k = i; k <= sz; ++k) {
                    int current_delta;
                    if (k == i) {
                        current_delta = dist(pts[i].first, pts[i].second, Px, Py) +
                                        dist(Px, Py, Dx, Dy) +
                                        dist(Dx, Dy, pts[i+1].first, pts[i+1].second) -
                                        dist(pts[i].first, pts[i].second, pts[i+1].first, pts[i+1].second);
                    } else {
                        int cost_D = dist(pts[k].first, pts[k].second, Dx, Dy) +
                                     dist(Dx, Dy, pts[k+1].first, pts[k+1].second) -
                                     dist(pts[k].first, pts[k].second, pts[k+1].first, pts[k+1].second);
                        current_delta = cost_P + cost_D;
                    }
                    
                    if (current_delta < best_incr) {
                        best_incr = current_delta;
                        best_i = i;
                        best_j = k;
                    }
                }
            }
            
            // Recalculate base distance
            int mid_dist = 0;
            int cx = CENTER, cy = CENTER;
            for(int val : new_route) {
                int tx, ty; get_coords(val, tx, ty);
                mid_dist += dist(cx, cy, tx, ty);
                cx = tx; cy = ty;
            }
            mid_dist += dist(cx, cy, CENTER, CENTER);
            
            int new_dist = mid_dist + best_incr;
            int old_dist = curr_sol.total_dist;
            
            if (new_dist < old_dist || bernoulli_distribution(exp((old_dist - new_dist) / T))(rng)) {
                curr_sol.route = new_route;
                curr_sol.route.insert(curr_sol.route.begin() + best_i, P_val);
                curr_sol.route.insert(curr_sol.route.begin() + best_j + 1, D_val);
                
                curr_sol.selected_orders[rem_idx] = add_oid;
                is_selected[rem_oid] = false;
                is_selected[add_oid] = true;
                curr_sol.total_dist = new_dist;
                
                if (new_dist < best_sol.total_dist) best_sol = curr_sol;
            }
        }
    }

    // Final Output
    cout << K_SELECT;
    for (int oid : best_sol.selected_orders) {
        cout << " " << oid + 1;
    }
    cout << endl;
    
    cout << best_sol.route.size() + 2;
    cout << " " << CENTER << " " << CENTER;
    for (int val : best_sol.route) {
        int x, y;
        get_coords(val, x, y);
        cout << " " << x << " " << y;
    }
    cout << " " << CENTER << " " << CENTER;
    cout << endl;

    return 0;
}