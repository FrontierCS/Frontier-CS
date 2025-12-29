#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Constants
const int GRID_SIZE = 800;
const int CENTER = 400;
const int N_ORDERS = 1000;
const int N_SELECT = 50;

// Data structures
struct Order {
    int id;
    int a, b, c, d;
};
Order orders[N_ORDERS];
bool selected[N_ORDERS];

// Helper functions
inline int get_dist(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

inline void get_point_coords(int pid, int &x, int &y) {
    int oid = pid % 1000;
    if (pid < 1000) {
        x = orders[oid].a;
        y = orders[oid].b;
    } else {
        x = orders[oid].c;
        y = orders[oid].d;
    }
}

int calculate_total_dist(const vector<int>& route) {
    int dist = 0;
    int cur_x = CENTER, cur_y = CENTER;
    for (int pid : route) {
        int nx, ny;
        get_point_coords(pid, nx, ny);
        dist += get_dist(cur_x, cur_y, nx, ny);
        cur_x = nx;
        cur_y = ny;
    }
    dist += get_dist(cur_x, cur_y, CENTER, CENTER);
    return dist;
}

// Calculate the increase in distance if point `pid` is inserted at `idx` in `route`
// Assumes route currently starts at CENTER and ends at CENTER implicitly
int get_insertion_cost(const vector<int>& route, int pid, int idx) {
    int px, py;
    get_point_coords(pid, px, py);
    
    int prev_x = CENTER, prev_y = CENTER;
    if (idx > 0) get_point_coords(route[idx-1], prev_x, prev_y);
    
    int next_x = CENTER, next_y = CENTER;
    if (idx < (int)route.size()) get_point_coords(route[idx], next_x, next_y);
    
    int current_segment = get_dist(prev_x, prev_y, next_x, next_y);
    int new_segment = get_dist(prev_x, prev_y, px, py) + get_dist(px, py, next_x, next_y);
    
    return new_segment - current_segment;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Input
    for (int i = 0; i < N_ORDERS; ++i) {
        orders[i].id = i;
        cin >> orders[i].a >> orders[i].b >> orders[i].c >> orders[i].d;
        selected[i] = false;
    }

    // RNG
    mt19937 rng(12345);

    // Initial Selection: Random 50 orders
    vector<int> current_route;
    vector<int> p(N_ORDERS);
    iota(p.begin(), p.end(), 0);
    shuffle(p.begin(), p.end(), rng);
    
    for(int i=0; i<N_SELECT; ++i) {
        selected[p[i]] = true;
        // Simple valid route construction: Pickup followed immediately by Delivery
        current_route.push_back(p[i]);
        current_route.push_back(p[i] + 1000);
    }

    int current_dist = calculate_total_dist(current_route);
    
    // Simulated Annealing
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; // seconds
    double start_temp = 150.0;
    double end_temp = 0.1;
    
    int iter = 0;
    while(true) {
        iter++;
        // Check time every 128 iterations
        if ((iter & 127) == 0) {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
            if (elapsed > time_limit) break;
        }
        
        // Compute current temperature
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
        double temp = start_temp + (end_temp - start_temp) * (elapsed / time_limit);
        
        int move_type = rng() % 100;
        
        // Move Probabilities:
        // 50% Modify Set (Swap Order + Greedy Insert)
        // 40% Greedy Shift (Optimize Route)
        // 10% Random Shift (Perturbation)
        
        if (move_type < 50) { 
            // --- Modify Set: Swap one selected order with an unselected one ---
            
            // Pick an order to remove from current selection
            int idx_remove = rng() % N_SELECT;
            int old_oid = -1;
            int c = 0;
            for(int i=0; i<N_ORDERS; ++i) {
                if(selected[i]) {
                    if(c == idx_remove) { old_oid = i; break; }
                    c++;
                }
            }
            
            // Pick an order to add from unselected
            int new_oid = -1;
            do { new_oid = rng() % N_ORDERS; } while(selected[new_oid]);
            
            // Build candidate route by removing old order
            vector<int> next_route;
            next_route.reserve(current_route.size());
            for(int pid : current_route) if (pid % 1000 != old_oid) next_route.push_back(pid);
            
            // Insert Pickup of new order at best valid position
            int best_p = -1, min_cost_p = 1e9;
            for(int i=0; i<= (int)next_route.size(); ++i) {
                int cost = get_insertion_cost(next_route, new_oid, i);
                if (cost < min_cost_p) { min_cost_p = cost; best_p = i; }
            }
            next_route.insert(next_route.begin() + best_p, new_oid);
            
            // Insert Delivery of new order at best valid position (must be after pickup)
            int best_d = -1, min_cost_d = 1e9;
            for(int i=best_p+1; i<= (int)next_route.size(); ++i) {
                int cost = get_insertion_cost(next_route, new_oid + 1000, i);
                if (cost < min_cost_d) { min_cost_d = cost; best_d = i; }
            }
            next_route.insert(next_route.begin() + best_d, new_oid + 1000);
            
            int new_dist = calculate_total_dist(next_route);
            int delta = new_dist - current_dist;
            
            if (delta <= 0 || bernoulli_distribution(exp(-delta / temp))(rng)) {
                current_route = next_route;
                current_dist = new_dist;
                selected[old_oid] = false;
                selected[new_oid] = true;
            }
        } else if (move_type < 90) { 
            // --- Greedy Shift: Move a point to its optimal valid position ---
            
            int pick_idx = rng() % current_route.size();
            int pid = current_route[pick_idx];
            int oid = pid % 1000;
            bool is_p = (pid < 1000);
            
            vector<int> temp = current_route;
            temp.erase(temp.begin() + pick_idx);
            
            // Find partner index to determine valid range
            int partner_pos = -1;
            int partner = is_p ? (oid + 1000) : oid;
            for(int i=0; i<(int)temp.size(); ++i) if(temp[i] == partner) { partner_pos = i; break; }
            
            int l = is_p ? 0 : partner_pos + 1;
            int r = is_p ? partner_pos : (int)temp.size();
            
            int best_pos = -1, min_cost = 1e9;
            for(int i=l; i<=r; ++i) {
                int cost = get_insertion_cost(temp, pid, i);
                if (cost < min_cost) { min_cost = cost; best_pos = i; }
            }
            
            temp.insert(temp.begin() + best_pos, pid);
            int new_dist = calculate_total_dist(temp);
            
            // Always accept greedy improvements (or neutral)
            // Even if slightly worse (due to remove/insert heuristic approximation), we accept to explore
            if (new_dist <= current_dist) {
                current_route = temp;
                current_dist = new_dist;
            } else {
                // Should technically be <= since original pos was a candidate
                // But just in case, accept to maintain validity
                current_route = temp;
                current_dist = new_dist;
            }
        } else { 
            // --- Random Shift: Move a point to a random valid position ---
            
            int pick_idx = rng() % current_route.size();
            int pid = current_route[pick_idx];
            int oid = pid % 1000;
            bool is_p = (pid < 1000);
            
            vector<int> temp = current_route;
            temp.erase(temp.begin() + pick_idx);
            
            int partner_pos = -1;
            int partner = is_p ? (oid + 1000) : oid;
            for(int i=0; i<(int)temp.size(); ++i) if(temp[i] == partner) { partner_pos = i; break; }
            
            int l = is_p ? 0 : partner_pos + 1;
            int r = is_p ? partner_pos : (int)temp.size();
            
            if (l > r) continue; 
            
            int new_idx = l + (rng() % (r - l + 1));
            temp.insert(temp.begin() + new_idx, pid);
            
            int new_dist = calculate_total_dist(temp);
            int delta = new_dist - current_dist;
            if (delta <= 0 || bernoulli_distribution(exp(-delta / temp))(rng)) {
                current_route = temp;
                current_dist = new_dist;
            }
        }
    }
    
    // Output
    vector<int> final_sel;
    for(int i=0; i<N_ORDERS; ++i) if(selected[i]) final_sel.push_back(i+1);
    
    cout << final_sel.size();
    for(int x : final_sel) cout << " " << x;
    cout << "\n";
    
    cout << current_route.size() + 2 << " " << CENTER << " " << CENTER;
    for(int pid : current_route) {
        int x, y;
        get_point_coords(pid, x, y);
        cout << " " << x << " " << y;
    }
    cout << " " << CENTER << " " << CENTER << "\n";

    return 0;
}