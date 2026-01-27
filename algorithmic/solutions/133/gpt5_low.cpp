#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<pair<double,double>> pts(n+1);
    for(int i=1;i<=n;i++){
        cin >> pts[i].first >> pts[i].second;
    }
    int m;
    cin >> m;
    vector<pair<int,int>> segs(m);
    for(int i=0;i<m;i++){
        int a,b;
        cin >> a >> b;
        segs[i] = {a,b};
    }
    double r;
    cin >> r;
    double p1,p2,p3,p4;
    cin >> p1 >> p2 >> p3 >> p4;
    
    const double PI = acos(-1.0);
    long double total = 0.0L;
    for(auto &e: segs){
        int a = e.first, b = e.second;
        double dx = pts[a].first - pts[b].first;
        double dy = pts[a].second - pts[b].second;
        double L = sqrt(dx*dx + dy*dy);
        total += 2.0L * r * L + PI * r * r;
    }
    cout.setf(std::ios::fixed); 
    cout << setprecision(7) << (double)total << "\n";
    return 0;
}