#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
};

int dist(const Point& a, const Point& b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

const Point DEPOT = {400, 400};

struct Order {
    int id;                 // 0-indexed
    Point pickup;
    Point delivery;
    int standalone_cost;
};

struct RouteNode {
    Point p;
    int order_id;          // -1 for depot
    bool is_pickup;        // true for pickup, false for delivery
};

int compute_total_distance(const vector<RouteNode>& route) {
    int total = 0;
    for (size_t i = 0; i + 1 < route.size(); ++i) {
        total += dist(route[i].p, route[i+1].p);
    }
    return total;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<Order> orders(1000);
    for (int i = 0; i < 1000; ++i) {
        int a, b, c, d;
        cin >> a >> b >> c >> d;
        orders[i].id = i;
        orders[i].pickup = {a, b};
        orders[i].delivery = {c, d};
        orders[i].standalone_cost = dist(DEPOT, orders[i].pickup) +
                                    dist(orders[i].pickup, orders[i].delivery) +
                                    dist(orders[i].delivery, DEPOT);
    }

    // Sort by standalone cost
    sort(orders.begin(), orders.end(),
         [](const Order& o1, const Order& o2) {
             return o1.standalone_cost < o2.standalone_cost;
         });

    // Take top 200 as candidates
    const int CANDIDATE_LIMIT = 200;
    vector<Order> candidates;
    for (int i = 0; i < CANDIDATE_LIMIT; ++i) {
        candidates.push_back(orders[i]);
    }
    // Restore original order for later reference
    sort(orders.begin(), orders.end(),
         [](const Order& o1, const Order& o2) {
             return o1.id < o2.id;
         });

    vector<bool> selected(1000, false);
    vector<Order> selected_orders;
    vector<RouteNode> route;
    route.push_back({DEPOT, -1, false});
    route.push_back({DEPOT, -1, false});

    // Greedy selection with fast insertion
    for (int step = 0; step < 50; ++step) {
        int best_cost = 1e9;
        int best_order_id = -1;
        int best_u = -1, best_v = -1;

        for (const Order& ord : candidates) {
            if (selected[ord.id]) continue;
            int L = route.size();
            // Step 1: best pickup insertion
            int best_u_loc = -1;
            int min_cost_p = 1e9;
            for (int u = 0; u < L - 1; ++u) {
                int cost_p = dist(route[u].p, ord.pickup) +
                             dist(ord.pickup, route[u+1].p) -
                             dist(route[u].p, route[u+1].p);
                if (cost_p < min_cost_p) {
                    min_cost_p = cost_p;
                    best_u_loc = u;
                }
            }
            // Step 2: best delivery insertion after that pickup
            int pos_p = best_u_loc + 1; // where pickup would be in intermediate route
            int best_v_loc = -1;
            int min_cost_d = 1e9;
            for (int v = pos_p; v < L; ++v) {
                Point left, right;
                if (v == pos_p) {
                    left = ord.pickup;
                    right = route[best_u_loc + 1].p;
                } else {
                    left = route[v - 1].p;
                    right = route[v].p;
                }
                int cost_d = dist(left, ord.delivery) +
                             dist(ord.delivery, right) -
                             dist(left, right);
                if (cost_d < min_cost_d) {
                    min_cost_d = cost_d;
                    best_v_loc = v;
                }
            }
            int total_cost = min_cost_p + min_cost_d;
            if (total_cost < best_cost) {
                best_cost = total_cost;
                best_order_id = ord.id;
                best_u = best_u_loc;
                best_v = best_v_loc;
            }
        }

        // Insert the best order
        Order& ord = orders[best_order_id];
        // Insert pickup
        route.insert(route.begin() + best_u + 1, {ord.pickup, ord.id, true});
        // Insert delivery at index best_v + 1 (see derivation)
        int insert_idx_d = best_v + 1;
        route.insert(route.begin() + insert_idx_d, {ord.delivery, ord.id, false});

        selected[ord.id] = true;
        selected_orders.push_back(ord);
    }

    // Local improvement
    int T = compute_total_distance(route);
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    const int PASSES = 10;
    for (int pass = 0; pass < PASSES; ++pass) {
        shuffle(selected_orders.begin(), selected_orders.end(), rng);
        for (const Order& ord : selected_orders) {
            // Find current positions
            int p_idx = -1, d_idx = -1;
            for (size_t i = 0; i < route.size(); ++i) {
                if (route[i].order_id == ord.id) {
                    if (route[i].is_pickup) p_idx = i;
                    else d_idx = i;
                }
            }
            if (p_idx == -1 || d_idx == -1) continue;
            if (p_idx > d_idx) swap(p_idx, d_idx);
            // Remove this order
            vector<RouteNode> new_route;
            new_route.reserve(route.size() - 2);
            for (size_t i = 0; i < route.size(); ++i) {
                if ((int)i == p_idx || (int)i == d_idx) continue;
                new_route.push_back(route[i]);
            }
            int T_removed = compute_total_distance(new_route);
            // Greedy reinsertion
            int L2 = new_route.size();
            // Pickup insertion
            int best_u = -1;
            int min_cost_p = 1e9;
            for (int u = 0; u < L2 - 1; ++u) {
                int cost_p = dist(new_route[u].p, ord.pickup) +
                             dist(ord.pickup, new_route[u+1].p) -
                             dist(new_route[u].p, new_route[u+1].p);
                if (cost_p < min_cost_p) {
                    min_cost_p = cost_p;
                    best_u = u;
                }
            }
            // Delivery insertion after pickup
            int pos_p = best_u + 1;
            int best_v = -1;
            int min_cost_d = 1e9;
            for (int v = pos_p; v < L2; ++v) {
                Point left, right;
                if (v == pos_p) {
                    left = ord.pickup;
                    right = new_route[best_u + 1].p;
                } else {
                    left = new_route[v - 1].p;
                    right = new_route[v].p;
                }
                int cost_d = dist(left, ord.delivery) +
                             dist(ord.delivery, right) -
                             dist(left, right);
                if (cost_d < min_cost_d) {
                    min_cost_d = cost_d;
                    best_v = v;
                }
            }
            int cost_ins = min_cost_p + min_cost_d;
            int T_new = T_removed + cost_ins;
            if (T_new < T) {
                // Build updated route
                vector<RouteNode> updated_route;
                updated_route.reserve(L2 + 2);
                // Insert pickup
                for (int i = 0; i <= best_u; ++i) updated_route.push_back(new_route[i]);
                updated_route.push_back({ord.pickup, ord.id, true});
                for (int i = best_u + 1; i < L2; ++i) updated_route.push_back(new_route[i]);
                // Insert delivery at index best_v + 1
                int insert_idx_d = best_v + 1;
                updated_route.insert(updated_route.begin() + insert_idx_d, {ord.delivery, ord.id, false});
                route = updated_route;
                T = T_new;
            }
        }
    }

    // Output
    cout << 50;
    for (const Order& ord : selected_orders) {
        cout << ' ' << ord.id + 1;
    }
    cout << '\n';
    cout << route.size();
    for (const RouteNode& node : route) {
        cout << ' ' << node.p.x << ' ' << node.p.y;
    }
    cout << endl;

    return 0;
}