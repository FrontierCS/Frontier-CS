#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    vector<double> x(n), y(n);
    for(int i = 0; i < n; i++) {
        scanf("%lf %lf", &x[i], &y[i]);
    }
    int m;
    scanf("%d", &m);
    double sum_L = 0.0;
    for(int i = 0; i < m; i++) {
        int a, b;
        scanf("%d %d", &a, &b);
        a--; b--;
        double dx = x[a] - x[b];
        double dy = y[a] - y[b];
        double L = sqrt(dx * dx + dy * dy);
        sum_L += L;
    }
    double r;
    scanf("%lf", &r);
    double pi = acos(-1.0);
    double total = 2.0 * r * sum_L + (double)m * pi * r * r;
    double p1, p2, p3, p4;
    scanf("%lf %lf %lf %lf", &p1, &p2, &p3, &p4);
    printf("%.7f\n", total);
    return 0;
}