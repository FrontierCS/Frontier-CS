#include <bits/stdc++.h>
using namespace std;

struct Order {
    int id;
    int a,b,c,d;
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 1000;
    vector<Order> orders;
    orders.reserve(N);
    for(int i=1;i<=N;i++){
        int a,b,c,d;
        if(!(cin>>a>>b>>c>>d)) return 0;
        orders.push_back({i,a,b,c,d});
    }
    auto manh = [](int x1,int y1,int x2,int y2){
        return abs(x1-x2)+abs(y1-y2);
    };
    // Score orders by estimated independent tour cost
    struct Scored { long long score; int idx; };
    vector<Scored> scored;
    scored.reserve(N);
    for(int i=0;i<N;i++){
        long long s = 0;
        s += manh(400,400,orders[i].a,orders[i].b);
        s += manh(orders[i].a,orders[i].b,orders[i].c,orders[i].d);
        s += manh(orders[i].c,orders[i].d,400,400);
        scored.push_back({s,i});
    }
    nth_element(scored.begin(), scored.begin()+50, scored.end(), [](const Scored& x, const Scored& y){
        if(x.score!=y.score) return x.score<y.score;
        return x.idx<y.idx;
    });
    scored.resize(50);
    // Extract selected orders
    vector<Order> sel;
    sel.reserve(50);
    for(auto &s: scored) sel.push_back(orders[s.idx]);
    // Nearest neighbor order for pickups starting from office
    int curx=400, cury=400;
    vector<int> used(sel.size(),0);
    vector<int> pick_order; pick_order.reserve(sel.size());
    for(size_t k=0;k<sel.size();k++){
        int best=-1; int bestd=INT_MAX;
        for(size_t i=0;i<sel.size();i++){
            if(used[i]) continue;
            int d = manh(curx,cury,sel[i].a,sel[i].b);
            if(d<bestd){
                bestd=d; best=(int)i;
            }
        }
        used[best]=1;
        pick_order.push_back(best);
        curx=sel[best].a; cury=sel[best].b;
    }
    // Waypoints: start at (400,400)
    vector<pair<int,int>> route;
    route.emplace_back(400,400);
    // Visit all pickups
    for(int idx: pick_order){
        route.emplace_back(sel[idx].a, sel[idx].b);
    }
    // Deliveries: nearest neighbor from last position
    vector<int> del_used(sel.size(),0);
    for(size_t k=0;k<sel.size();k++){
        int best=-1; int bestd=INT_MAX;
        for(size_t i=0;i<sel.size();i++){
            if(del_used[i]) continue;
            int d = manh(curx,cury,sel[i].c,sel[i].d);
            if(d<bestd){
                bestd=d; best=(int)i;
            }
        }
        del_used[best]=1;
        route.emplace_back(sel[best].c, sel[best].d);
        curx=sel[best].c; cury=sel[best].d;
    }
    // Return to office if not already there
    if(!(curx==400 && cury==400)) route.emplace_back(400,400);

    // Output
    cout<<50;
    for(auto &o: sel) cout<<" "<<o.id;
    cout<<"\n";
    cout<<route.size();
    for(auto &p: route) cout<<" "<<p.first<<" "<<p.second;
    cout<<"\n";
    return 0;
}