#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<double> X(n + 1), Y(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> X[i] >> Y[i];
    }
    int m;
    cin >> m;
    double sumL = 0.0;
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        double dx = X[a] - X[b];
        double dy = Y[a] - Y[b];
        sumL += sqrt(dx * dx + dy * dy);
    }
    double r;
    cin >> r;
    double p1, p2, p3, p4;
    cin >> p1 >> p2 >> p3 >> p4;
    double area = 2.0 * r * sumL + m * M_PI * r * r;
    printf("%.7f\n", area);
    return 0;
}