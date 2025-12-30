#include <bits/stdc++.h>
using namespace std;
typedef pair<int,int> pii;
int manh(int x1,int y1, int x2, int y2){
    return abs(x1-x2) + abs(y1-y2);
}
int main(){
    const int ox=400, oy=400;
    vector<int> pa(1000), pb(1000), pc(1000), pd(1000);
    vector<tuple<int, int>> cand;
    for(int i=0; i<1000; i++){
        int a,b,c,d;
        cin>>a>>b>>c>>d;
        pa[i]=a; pb[i]=b; pc[i]=c; pd[i]=d;
        int cost = manh(ox,oy, a,b) + manh(a,b, c,d) + manh(ox,oy, c,d);
        cand.emplace_back(cost, i);
    }
    sort(cand.begin(), cand.end());
    vector<int> selected;
    for(int j=0; j<50; j++){
        selected.push_back( get<1>(cand[j]) );
    }
    vector<int> remaining = selected;
    vector<int> order_seq;
    vector<pii> route;
    route.emplace_back(ox, oy);
    int curx = ox, cury = oy;
    while(!remaining.empty()){
        int best_j = -1;
        int min_d = INT_MAX;
        for(int j=0; j<remaining.size(); j++){
            int id = remaining[j];
            int dd = manh(curx, cury, pa[id], pb[id]);
            if(dd < min_d){
                min_d = dd;
                best_j = j;
            }
        }
        int id = remaining[best_j];
        order_seq.push_back(id);
        route.emplace_back(pa[id], pb[id]);
        route.emplace_back(pc[id], pd[id]);
        curx = pc[id];
        cury = pd[id];
        remaining.erase(remaining.begin() + best_j);
    }
    route.emplace_back(ox, oy);
    auto compute_T = [](const vector<pii>& r) -> int {
        int t=0;
        for(size_t i=0; i+1 < r.size(); i++){
            t += manh( r[i].first, r[i].second, r[i+1].first, r[i+1].second );
        }
        return t;
    };
    int T = compute_T(route);
    vector<pii> route_rev;
    route_rev.emplace_back(ox, oy);
    for(int k=49; k>=0; k--){
        int id = order_seq[k];
        route_rev.emplace_back(pa[id], pb[id]);
        route_rev.emplace_back(pc[id], pd[id]);
    }
    route_rev.emplace_back(ox, oy);
    int T_rev = compute_T(route_rev);
    vector<pii> final_route = (T <= T_rev ? route : route_rev);
    vector<int> chosen = selected;
    sort(chosen.begin(), chosen.end());
    cout << 50;
    for(int id: chosen) cout << " " << (id+1);
    cout << endl;
    cout << final_route.size();
    for(auto& pt: final_route){
        cout << " " << pt.first << " " << pt.second;
    }
    cout << endl;
    return 0;
}