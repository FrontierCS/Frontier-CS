#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdlib>
#include <ctime>
#include <cmath>

using namespace std;

struct Point {
    int x, y;
};

struct Order {
    int id;
    Point p, d;
    int cost_o; // dist(center,p)+dist(p,d)+dist(d,center)
};

struct Node {
    int order_id;
    bool is_pickup;
    Point pt;
};

const Point CENTER = {400, 400};

int manhattan(const Point& a, const Point& b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

int totalDistance(const vector<Node>& route) {
    if (route.empty()) return 0;
    int dist = manhattan(CENTER, route[0].pt);
    for (size_t i = 0; i + 1 < route.size(); ++i) {
        dist += manhattan(route[i].pt, route[i+1].pt);
    }
    dist += manhattan(route.back().pt, CENTER);
    return dist;
}

int totalDistanceWithInsertion(const vector<Node>& route, int pos_p, int pos_d, const Point& p, const Point& d) {
    // pos_p and pos_d are positions in the new sequence (length = route.size()+2), 0 <= pos_p < pos_d <= route.size()+1
    vector<Point> seq;
    seq.push_back(CENTER);
    int idx = 0;
    for (int pos = 0; pos < (int)route.size() + 2; ++pos) {
        if (pos == pos_p) {
            seq.push_back(p);
        } else if (pos == pos_d) {
            seq.push_back(d);
        } else {
            seq.push_back(route[idx].pt);
            ++idx;
        }
    }
    seq.push_back(CENTER);
    int dist = 0;
    for (size_t i = 0; i + 1 < seq.size(); ++i) {
        dist += manhattan(seq[i], seq[i+1]);
    }
    return dist;
}

vector<Node> greedyInsertion(const vector<Order>& orders) {
    vector<Node> route;
    for (const Order& ord : orders) {
        if (route.empty()) {
            route.push_back({ord.id, true, ord.p});
            route.push_back({ord.id, false, ord.d});
        } else {
            int n = route.size();
            int best_cost = 1e9;
            int best_i = -1, best_j = -1;
            for (int i = 0; i <= n; ++i) {
                for (int j = i + 1; j <= n + 1; ++j) {
                    int cost = totalDistanceWithInsertion(route, i, j, ord.p, ord.d);
                    if (cost < best_cost) {
                        best_cost = cost;
                        best_i = i;
                        best_j = j;
                    }
                }
            }
            vector<Node> new_route;
            for (int k = 0; k < best_i; ++k) new_route.push_back(route[k]);
            new_route.push_back({ord.id, true, ord.p});
            for (int k = best_i; k < best_j - 1; ++k) new_route.push_back(route[k]);
            new_route.push_back({ord.id, false, ord.d});
            for (int k = best_j - 1; k < n; ++k) new_route.push_back(route[k]);
            route = new_route;
        }
    }
    return route;
}

void localSwapOptimization(vector<Node>& route) {
    int n = route.size();
    vector<int> pickup_idx(1001, -1), delivery_idx(1001, -1);
    auto updateIndices = [&]() {
        fill(pickup_idx.begin(), pickup_idx.end(), -1);
        fill(delivery_idx.begin(), delivery_idx.end(), -1);
        for (int i = 0; i < n; ++i) {
            const Node& node = route[i];
            if (node.is_pickup) pickup_idx[node.order_id] = i;
            else delivery_idx[node.order_id] = i;
        }
    };
    updateIndices();

    bool improved = true;
    while (improved) {
        improved = false;
        for (int a = 0; a + 1 < n; ++a) {
            int id1 = route[a].order_id;
            bool is_p1 = route[a].is_pickup;
            int id2 = route[a+1].order_id;
            bool is_p2 = route[a+1].is_pickup;
            if (id1 == id2) continue;

            int p1 = pickup_idx[id1], d1 = delivery_idx[id1];
            int p2 = pickup_idx[id2], d2 = delivery_idx[id2];

            int new_p1 = (p1 == a) ? a+1 : (p1 == a+1) ? a : p1;
            int new_d1 = (d1 == a) ? a+1 : (d1 == a+1) ? a : d1;
            int new_p2 = (p2 == a) ? a+1 : (p2 == a+1) ? a : p2;
            int new_d2 = (d2 == a) ? a+1 : (d2 == a+1) ? a : d2;

            if (new_p1 >= new_d1) continue;
            if (new_p2 >= new_d2) continue;

            // compute delta
            Point prev = (a == 0) ? CENTER : route[a-1].pt;
            Point cur_a = route[a].pt;
            Point cur_b = route[a+1].pt;
            Point next = (a+2 < n) ? route[a+2].pt : CENTER;

            int old_dist = manhattan(prev, cur_a) + manhattan(cur_a, cur_b) + manhattan(cur_b, next);
            int new_dist = manhattan(prev, cur_b) + manhattan(cur_b, cur_a) + manhattan(cur_a, next);
            int delta = new_dist - old_dist;

            if (delta < 0) {
                swap(route[a], route[a+1]);
                updateIndices();
                improved = true;
                break;
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    vector<Order> orders(1000);
    for (int i = 0; i < 1000; ++i) {
        int a, b, c, d;
        cin >> a >> b >> c >> d;
        orders[i].id = i + 1;
        orders[i].p = {a, b};
        orders[i].d = {c, d};
        orders[i].cost_o = manhattan(CENTER, orders[i].p) + manhattan(orders[i].p, orders[i].d) + manhattan(orders[i].d, CENTER);
    }

    sort(orders.begin(), orders.end(), [](const Order& x, const Order& y) {
        return x.cost_o < y.cost_o;
    });

    vector<Order> selected(orders.begin(), orders.begin() + 50);
    vector<int> selected_ids;
    for (const Order& ord : selected) selected_ids.push_back(ord.id);

    srand(time(0));
    int best_dist = 1e9;
    vector<Node> best_route;

    for (int iter = 0; iter < 5; ++iter) {
        vector<Order> cur_orders = selected;
        if (iter > 0) random_shuffle(cur_orders.begin(), cur_orders.end());
        vector<Node> route = greedyInsertion(cur_orders);
        localSwapOptimization(route);
        int d = totalDistance(route);
        if (d < best_dist) {
            best_dist = d;
            best_route = route;
        }
    }

    // output
    cout << 50;
    for (int id : selected_ids) cout << " " << id;
    cout << "\n";

    cout << best_route.size() + 2;
    cout << " " << CENTER.x << " " << CENTER.y;
    for (const Node& node : best_route) {
        cout << " " << node.pt.x << " " << node.pt.y;
    }
    cout << " " << CENTER.x << " " << CENTER.y;
    cout << endl;

    return 0;
}