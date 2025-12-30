#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <climits>

using namespace std;

struct Point {
    int x, y;
    Point(int x=0, int y=0) : x(x), y(y) {}
};

int manhattan(const Point& a, const Point& b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

int main() {
    // Read input
    vector<Point> a(1000), b(1000); // pickup and delivery
    for (int i = 0; i < 1000; i++) {
        int ax, ay, cx, cy;
        cin >> ax >> ay >> cx >> cy;
        a[i] = Point(ax, ay);
        b[i] = Point(cx, cy);
    }

    Point depot(400, 400);

    // Compute standalone cost for each order
    vector<pair<int, int>> costs; // (cost, index)
    for (int i = 0; i < 1000; i++) {
        int cost = manhattan(depot, a[i]) + manhattan(a[i], b[i]) + manhattan(b[i], depot);
        costs.push_back({cost, i});
    }

    // Select 50 orders with smallest cost
    sort(costs.begin(), costs.end());
    vector<int> selected;
    for (int i = 0; i < 50; i++) {
        selected.push_back(costs[i].second);
    }

    // Build pickup and delivery points for selected orders
    vector<Point> pickups(50), deliveries(50);
    for (int i = 0; i < 50; i++) {
        int idx = selected[i];
        pickups[i] = a[idx];
        deliveries[i] = b[idx];
    }

    // Helper function to compute total cost given sequences
    auto total_cost = [&](const vector<int>& p_seq, const vector<int>& d_seq) -> int {
        int cost = 0;
        // depot -> first pickup
        cost += manhattan(depot, pickups[p_seq[0]]);
        // between pickups
        for (int i = 0; i < 49; i++) {
            cost += manhattan(pickups[p_seq[i]], pickups[p_seq[i+1]]);
        }
        // last pickup -> first delivery
        cost += manhattan(pickups[p_seq[49]], deliveries[d_seq[0]]);
        // between deliveries
        for (int i = 0; i < 49; i++) {
            cost += manhattan(deliveries[d_seq[i]], deliveries[d_seq[i+1]]);
        }
        // last delivery -> depot
        cost += manhattan(deliveries[d_seq[49]], depot);
        return cost;
    };

    // ----- Initial pickup sequence by nearest neighbor from depot -----
    vector<int> p_seq;
    vector<bool> used_p(50, false);
    Point current = depot;
    for (int step = 0; step < 50; step++) {
        int best = -1;
        int best_dist = INT_MAX;
        for (int i = 0; i < 50; i++) {
            if (!used_p[i]) {
                int d = manhattan(current, pickups[i]);
                if (d < best_dist) {
                    best_dist = d;
                    best = i;
                }
            }
        }
        p_seq.push_back(best);
        used_p[best] = true;
        current = pickups[best];
    }
    Point last_pickup = pickups[p_seq.back()];

    // ----- Initial delivery sequence: choose start delivery closest to last_pickup, then nearest neighbor -----
    vector<int> d_seq;
    vector<bool> used_d(50, false);
    // choose first delivery
    int first_d = -1;
    int best_first_dist = INT_MAX;
    for (int i = 0; i < 50; i++) {
        int d = manhattan(last_pickup, deliveries[i]);
        if (d < best_first_dist) {
            best_first_dist = d;
            first_d = i;
        }
    }
    d_seq.push_back(first_d);
    used_d[first_d] = true;
    current = deliveries[first_d];
    for (int step = 1; step < 50; step++) {
        int best = -1;
        int best_dist = INT_MAX;
        for (int i = 0; i < 50; i++) {
            if (!used_d[i]) {
                int d = manhattan(current, deliveries[i]);
                if (d < best_dist) {
                    best_dist = d;
                    best = i;
                }
            }
        }
        d_seq.push_back(best);
        used_d[best] = true;
        current = deliveries[best];
    }

    // ----- Local improvement using 2-opt -----
    // Function to try 2-opt on a sequence (pickup or delivery)
    auto improve_seq = [&](vector<int>& seq, bool is_pickup) -> bool {
        // seq is a permutation of 0..49
        int best_gain = 0;
        int best_l = -1, best_r = -1;
        int current_cost = total_cost(p_seq, d_seq);
        for (int l = 0; l < 50; l++) {
            for (int r = l+1; r < 50; r++) {
                // Reverse segment [l, r]
                vector<int> new_seq = seq;
                reverse(new_seq.begin() + l, new_seq.begin() + r + 1);
                int new_cost;
                if (is_pickup) {
                    new_cost = total_cost(new_seq, d_seq);
                } else {
                    new_cost = total_cost(p_seq, new_seq);
                }
                int gain = current_cost - new_cost;
                if (gain > best_gain) {
                    best_gain = gain;
                    best_l = l;
                    best_r = r;
                }
            }
        }
        if (best_gain > 0) {
            reverse(seq.begin() + best_l, seq.begin() + best_r + 1);
            return true;
        }
        return false;
    };

    // Repeat improvements a few times
    for (int iter = 0; iter < 10; iter++) {
        bool improved = false;
        while (improve_seq(p_seq, true)) improved = true;
        while (improve_seq(d_seq, false)) improved = true;
        if (!improved) break;
    }

    // ----- Output -----
    // Output selected orders (1-based)
    cout << 50;
    for (int i = 0; i < 50; i++) {
        cout << " " << selected[i] + 1;
    }
    cout << endl;

    // Output route
    vector<Point> route;
    route.push_back(depot);
    for (int i = 0; i < 50; i++) {
        route.push_back(pickups[p_seq[i]]);
    }
    for (int i = 0; i < 50; i++) {
        route.push_back(deliveries[d_seq[i]]);
    }
    route.push_back(depot);

    cout << route.size();
    for (const Point& p : route) {
        cout << " " << p.x << " " << p.y;
    }
    cout << endl;

    return 0;
}