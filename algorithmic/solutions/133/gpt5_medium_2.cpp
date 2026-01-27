#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<pair<double,double>> pts(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> pts[i].first >> pts[i].second;
    }
    int m;
    cin >> m;
    long double sumL = 0.0L;
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        long double dx = (long double)pts[a].first - (long double)pts[b].first;
        long double dy = (long double)pts[a].second - (long double)pts[b].second;
        sumL += sqrtl(dx*dx + dy*dy);
    }
    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4; // read but not used
    
    long double pi = acosl(-1.0L);
    long double area = (long double)m * pi * (long double)r * (long double)r + 2.0L * (long double)r * sumL;
    cout.setf(std::ios::fixed); 
    cout << setprecision(7) << (double)area << "\n";
    return 0;
}