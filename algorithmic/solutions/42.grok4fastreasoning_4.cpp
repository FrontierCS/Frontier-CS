#include <bits/stdc++.h>

using namespace std;

int main() {
    int n;
    cin >> n;
    int k = 0;
    while (k * 1LL * k < n) k++;
    double L = k;
    cout << fixed << setprecision(6) << L << endl;
    int cnt = 0;
    for (int j = 0; j < k; j++) {
        for (int i = 0; i < k; i++) {
            if (cnt >= n) break;
            double x = 0.5 + i;
            double y = 0.5 + j;
            double a = 0.0;
            cout << fixed << setprecision(6) << x << " " << y << " " << a << endl;
            cnt++;
        }
        if (cnt >= n) break;
    }
    return 0;
}