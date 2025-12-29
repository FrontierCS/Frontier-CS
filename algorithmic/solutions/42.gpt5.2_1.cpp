#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int k = (int)ceil(sqrt((double)n) - 1e-12);
    double L = (double)k;

    cout.setf(std::ios::fixed);
    cout << setprecision(6) << L << "\n";

    for (int i = 0; i < n; i++) {
        int x = i % k;
        int y = i / k;
        double cx = 0.5 + x;
        double cy = 0.5 + y;
        cout << cx << " " << cy << " " << 0.0 << "\n";
    }

    return 0;
}