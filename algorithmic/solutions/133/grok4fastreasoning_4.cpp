#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<double> x(n), y(n);
    for(int i = 0; i < n; i++) cin >> x[i] >> y[i];
    int m;
    cin >> m;
    double total_L = 0.0;
    for(int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b; a--; b--;
        double dx = x[a] - x[b];
        double dy = y[a] - y[b];
        total_L += sqrt(dx * dx + dy * dy);
    }
    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;
    double pi = acos(-1.0);
    double area = (double)m * pi * r * r + 2.0 * r * total_L;
    printf("%.7f\n", area);
    return 0;
}