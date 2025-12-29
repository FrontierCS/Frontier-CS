#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

// Problem Constants
const int N_ORDERS = 1000;
const int M_SELECT = 50;
const int CENTER = 400;

// Global Data
int A[N_ORDERS], B[N_ORDERS], C[N_ORDERS], D[N_ORDERS];

// Utils
struct Point {
    int x, y;
};

inline int dist(Point p1, Point p2) {
    return abs(p1.x - p2.x) + abs(p1.y - p2.y);
}

// Helper to get coordinates of a node in the route
// val: 0..49 (pickup for selection[val]), 50..99 (delivery for selection[val-50])
inline Point get_coords(int val, const vector<int>& selection) {
    int sel_idx = (val < M_SELECT) ? val : val - M_SELECT;
    int order_id = selection[sel_idx];
    if (val < M_SELECT) return {A[order_id], B[order_id]};
    else return {C[order_id], D[order_id]};
}

int calculate_score(const vector<int>& selection, const vector<int>& route) {
    Point curr = {CENTER, CENTER};
    int d = 0;
    for (int val : route) {
        Point next = get_coords(val, selection);
        d += dist(curr, next);
        curr = next;
    }
    d += dist(curr, {CENTER, CENTER});
    return d;
}

// Fast Random Number Generator
uint64_t rng_state = 123456789;
inline uint64_t xorshift() {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state;
}
inline int rand_int(int n) {
    return xorshift() % n;
}
inline double rand_double() {
    return (double)(xorshift()) * (1.0 / 18446744073709551615.0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Input
    for (int i = 0; i < N_ORDERS; ++i) {
        cin >> A[i] >> B[i] >> C[i] >> D[i];
    }

    // Initial Selection Strategy:
    // Pick 50 orders closest to the center to form a compact cluster initially.
    // Metric: dist(Home, Pickup) + dist(Pickup, Delivery)
    vector<pair<int, int>> candidates;
    candidates.reserve(N_ORDERS);
    for (int i = 0; i < N_ORDERS; ++i) {
        int cost = dist({CENTER, CENTER}, {A[i], B[i]}) + dist({A[i], B[i]}, {C[i], D[i]});
        candidates.push_back({cost, i});
    }
    sort(candidates.begin(), candidates.end());

    vector<int> selection(M_SELECT);
    vector<bool> is_selected(N_ORDERS, false);
    for (int i = 0; i < M_SELECT; ++i) {
        selection[i] = candidates[i].second;
        is_selected[selection[i]] = true;
    }

    // Initial Route: P0, D0, P1, D1, ...
    vector<int> route;
    route.reserve(2 * M_SELECT);
    for (int i = 0; i < M_SELECT; ++i) {
        route.push_back(i);
        route.push_back(i + M_SELECT);
    }

    int current_score = calculate_score(selection, route);
    int best_score = current_score;
    vector<int> best_selection = selection;
    vector<int> best_route = route;

    // Time Management
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; // seconds
    
    // SA Params
    double T0 = 200.0;
    double T1 = 0.1;
    double T = T0;

    int iter = 0;
    while (true) {
        iter++;
        // Update temperature and check time periodically
        if ((iter & 0x3FF) == 0) { 
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
            double progress = elapsed / time_limit;
            T = T0 * pow(T1 / T0, progress);
        }

        int type = rand_int(100);

        if (type < 50) { // Move 1: Shift a node in the route
            int u = rand_int(2 * M_SELECT);
            int v = rand_int(2 * M_SELECT);
            if (u == v) continue;

            int val = route[u];
            route.erase(route.begin() + u);
            route.insert(route.begin() + v, val);

            // Check Validity (Precedence Constraint)
            bool valid = true;
            int p_idx = -1, d_idx = -1;
            if (val < M_SELECT) { // Pickup
                p_idx = v;
                // Find corresponding Delivery
                for(int k=0; k<2*M_SELECT; ++k) if(route[k] == val + M_SELECT) { d_idx = k; break; }
            } else { // Delivery
                d_idx = v;
                // Find corresponding Pickup
                for(int k=0; k<2*M_SELECT; ++k) if(route[k] == val - M_SELECT) { p_idx = k; break; }
            }
            if (p_idx >= d_idx) valid = false;

            if (valid) {
                int new_score = calculate_score(selection, route);
                int delta = new_score - current_score;
                if (delta <= 0 || rand_double() < exp(-delta / T)) {
                    current_score = new_score;
                    if (current_score < best_score) {
                        best_score = current_score;
                        best_selection = selection;
                        best_route = route;
                    }
                } else {
                    // Revert
                    route.erase(route.begin() + v);
                    route.insert(route.begin() + u, val);
                }
            } else {
                // Revert
                route.erase(route.begin() + v);
                route.insert(route.begin() + u, val);
            }
        } else if (type < 80) { // Move 2: Swap two nodes in the route
            int u = rand_int(2 * M_SELECT);
            int v = rand_int(2 * M_SELECT);
            if (u == v) continue;
            
            swap(route[u], route[v]);
            
            bool valid = true;
            // Check constraint for node at u
            int val_u = route[u];
            int p_idx = -1, d_idx = -1;
            if (val_u < M_SELECT) {
                p_idx = u;
                for(int k=0; k<2*M_SELECT; ++k) if(route[k] == val_u + M_SELECT) { d_idx = k; break; }
            } else {
                d_idx = u;
                for(int k=0; k<2*M_SELECT; ++k) if(route[k] == val_u - M_SELECT) { p_idx = k; break; }
            }
            if (p_idx >= d_idx) valid = false;

            if (valid) {
                // Check constraint for node at v
                int val_v = route[v];
                p_idx = -1; d_idx = -1;
                if (val_v < M_SELECT) {
                    p_idx = v;
                    for(int k=0; k<2*M_SELECT; ++k) if(route[k] == val_v + M_SELECT) { d_idx = k; break; }
                } else {
                    d_idx = v;
                    for(int k=0; k<2*M_SELECT; ++k) if(route[k] == val_v - M_SELECT) { p_idx = k; break; }
                }
                if (p_idx >= d_idx) valid = false;
            }

            if (valid) {
                int new_score = calculate_score(selection, route);
                int delta = new_score - current_score;
                if (delta <= 0 || rand_double() < exp(-delta / T)) {
                    current_score = new_score;
                    if (current_score < best_score) {
                        best_score = current_score;
                        best_selection = selection;
                        best_route = route;
                    }
                } else {
                    swap(route[u], route[v]);
                }
            } else {
                swap(route[u], route[v]);
            }

        } else { // Move 3: Change Selected Order
            int sel_idx = rand_int(M_SELECT);
            int old_order = selection[sel_idx];
            int new_order = rand_int(N_ORDERS);
            
            while(is_selected[new_order]) {
                new_order = rand_int(N_ORDERS);
            }

            selection[sel_idx] = new_order;
            is_selected[old_order] = false;
            is_selected[new_order] = true;

            int new_score = calculate_score(selection, route);
            int delta = new_score - current_score;

            if (delta <= 0 || rand_double() < exp(-delta / T)) {
                current_score = new_score;
                if (current_score < best_score) {
                    best_score = current_score;
                    best_selection = selection;
                    best_route = route;
                }
            } else {
                // Revert
                selection[sel_idx] = old_order;
                is_selected[new_order] = false;
                is_selected[old_order] = true;
            }
        }
    }

    // Output
    cout << M_SELECT;
    for (int i = 0; i < M_SELECT; ++i) {
        cout << " " << best_selection[i] + 1;
    }
    cout << "\n";

    vector<Point> final_path;
    final_path.push_back({CENTER, CENTER});
    for (int val : best_route) {
        final_path.push_back(get_coords(val, best_selection));
    }
    final_path.push_back({CENTER, CENTER});

    cout << final_path.size();
    for (const auto& p : final_path) {
        cout << " " << p.x << " " << p.y;
    }
    cout << "\n";

    return 0;
}