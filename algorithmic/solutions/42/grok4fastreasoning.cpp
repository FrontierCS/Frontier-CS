#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    int side = 0;
    while (side * side < n) side++;
    double L = side;
    printf("%.6f\n", L);
    for (int i = 0; i < n; i++) {
        int x = i % side;
        int y = i / side;
        double cx = 0.5 + x;
        double cy = 0.5 + y;
        double a = 0.0;
        printf("%.6f %.6f %.6f\n", cx, cy, a);
    }
    return 0;
}