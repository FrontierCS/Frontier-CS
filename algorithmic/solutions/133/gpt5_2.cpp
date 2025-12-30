#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<double> x(n + 1), y(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> x[i] >> y[i];
    }
    int m;
    cin >> m;
    double sumLen = 0.0;
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        double dx = x[a] - x[b];
        double dy = y[a] - y[b];
        sumLen += sqrt(dx*dx + dy*dy);
    }
    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;
    const double PI = acos(-1.0);
    double area = 2.0 * r * sumLen + (double)m * PI * r * r;
    cout.setf(std::ios::fixed); 
    cout << setprecision(7) << area << "\n";
    return 0;
}