#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
};

int manh(Point a, Point b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

struct Order {
    Point a, b;
    int id, cost;
};

int main() {
    Point O = {400, 400};
    vector<Order> orders(1001);
    for(int i = 1; i <= 1000; i++) {
        cin >> orders[i].a.x >> orders[i].a.y >> orders[i].b.x >> orders[i].b.y;
        orders[i].id = i;
        orders[i].cost = manh(O, orders[i].a) + manh(orders[i].a, orders[i].b) + manh(orders[i].b, O);
    }
    sort(orders.begin() + 1, orders.begin() + 1001, [](const Order& p, const Order& q) {
        return p.cost < q.cost;
    });
    vector<Order> sel;
    for(int i = 1; i <= 50; i++) {
        sel.push_back(orders[i]);
    }
    int N = 50;
    vector<bool> used(N, false);
    vector<int> seq;
    Point cur = O;
    for(int st = 0; st < N; st++) {
        int best = -1;
        int md = INT_MAX;
        for(int j = 0; j < N; j++) {
            if(!used[j]) {
                int d = manh(cur, sel[j].a);
                if(d < md || (d == md && sel[j].cost < sel[best].cost)) {
                    md = d;
                    best = j;
                }
            }
        }
        assert(best != -1);
        used[best] = true;
        seq.push_back(best);
        cur = sel[best].b;
    }
    cout << N;
    for(int k : seq) {
        cout << " " << sel[k].id;
    }
    cout << endl;
    vector<Point> route;
    route.push_back(O);
    for(int k : seq) {
        route.push_back(sel[k].a);
        route.push_back(sel[k].b);
    }
    route.push_back(O);
    cout << route.size();
    for(Point p : route) {
        cout << " " << p.x << " " << p.y;
    }
    cout << endl;
    return 0;
}