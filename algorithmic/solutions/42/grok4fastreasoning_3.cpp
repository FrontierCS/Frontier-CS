#include <bits/stdc++.h>

using namespace std;

int main() {
    int n;
    cin >> n;
    int k = (int) sqrt(n);
    if (k * 1LL * k < n) k++;
    double L = k;
    cout << fixed << setprecision(6) << L << endl;
    int placed = 0;
    for (int row = 0; row < k; row++) {
        for (int col = 0; col < k; col++) {
            if (placed < n) {
                double x = 0.5 + col;
                double y = 0.5 + row;
                double angle = 0.0;
                cout << fixed << setprecision(6) << x << " " << y << " " << angle << endl;
                placed++;
            }
        }
    }
    return 0;
}