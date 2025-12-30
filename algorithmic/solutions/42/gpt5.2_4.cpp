#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int k = (int)ceil(sqrt((double)n));
    double L = (double)k;

    cout.setf(std::ios::fixed);
    cout << setprecision(6) << L << "\n";

    for (int i = 0; i < n; i++) {
        int r = i / k;
        int c = i % k;
        double x = c + 0.5;
        double y = r + 0.5;
        double a = 0.0;
        cout << setprecision(6) << x << " " << y << " " << a << "\n";
    }
    return 0;
}