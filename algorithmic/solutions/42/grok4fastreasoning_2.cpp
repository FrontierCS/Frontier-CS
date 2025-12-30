#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cout << fixed << setprecision(6);
    int n;
    cin >> n;
    double sqr = sqrt(n);
    int k = (int) sqr;
    if (1LL * k * k < n) k++;
    double L = k;
    cout << L << "\n";
    int placed = 0;
    for(int j = 0; j < k && placed < n; ++j) {
        for(int i = 0; i < k && placed < n; ++i) {
            double x = 0.5 + i;
            double y = 0.5 + j;
            cout << x << " " << y << " " << 0.0 << "\n";
            ++placed;
        }
    }
    return 0;
}