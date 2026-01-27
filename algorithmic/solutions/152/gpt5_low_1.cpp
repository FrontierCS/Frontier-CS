#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int N = 1000;
    const int M = 50;
    const int OX = 400, OY = 400;
    struct Order {
        int idx;
        int a,b,c,d;
        long long cycCost;
    };
    vector<Order> orders;
    orders.reserve(N);
    for (int i = 0; i < N; ++i) {
        int a,b,c,d;
        if(!(cin >> a >> b >> c >> d)) return 0;
        long long cost = llabs(OX - a) + llabs(OY - b) + llabs(a - c) + llabs(b - d) + llabs(c - OX) + llabs(d - OY);
        orders.push_back({i+1, a,b,c,d, cost});
    }
    // Select 50 orders with smallest cycle cost via office
    nth_element(orders.begin(), orders.begin()+M, orders.end(), [](const Order& x, const Order& y){
        return x.cycCost < y.cycCost;
    });
    vector<Order> chosen(orders.begin(), orders.begin()+M);
    
    // Build route using greedy nearest neighbor on pickup points
    vector<bool> used(M, false);
    vector<int> route_x, route_y;
    route_x.push_back(OX);
    route_y.push_back(OY);
    int curx = OX, cury = OY;
    for (int it = 0; it < M; ++it) {
        int best = -1;
        long long bestDist = (1LL<<60);
        for (int i = 0; i < M; ++i) {
            if (used[i]) continue;
            long long d = llabs(curx - chosen[i].a) + llabs(cury - chosen[i].b);
            if (d < bestDist) {
                bestDist = d;
                best = i;
            }
        }
        used[best] = true;
        // go to pickup
        route_x.push_back(chosen[best].a);
        route_y.push_back(chosen[best].b);
        // then to delivery
        route_x.push_back(chosen[best].c);
        route_y.push_back(chosen[best].d);
        curx = chosen[best].c;
        cury = chosen[best].d;
    }
    // return to office
    route_x.push_back(OX);
    route_y.push_back(OY);
    
    // Output
    cout << M;
    for (int i = 0; i < M; ++i) {
        cout << " " << chosen[i].idx;
    }
    cout << "\n";
    int n = (int)route_x.size();
    cout << n;
    for (int i = 0; i < n; ++i) {
        cout << " " << route_x[i] << " " << route_y[i];
    }
    cout << "\n";
    return 0;
}