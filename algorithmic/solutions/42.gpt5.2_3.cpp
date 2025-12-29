#include <bits/stdc++.h>
using namespace std;

static int ceil_sqrt_int(int n) {
    int r = (int)floor(sqrt((double)n));
    while (1LL * r * r < n) ++r;
    while (r > 0 && 1LL * (r - 1) * (r - 1) >= n) --r;
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int m = ceil_sqrt_int(n);
    double L = (double)m;

    cout.setf(std::ios::fixed);
    cout << setprecision(6) << L << "\n";

    for (int i = 0; i < n; i++) {
        int x = i % m;
        int y = i / m;
        double cx = 0.5 + x;
        double cy = 0.5 + y;
        double a = 0.0;
        cout << cx << " " << cy << " " << a << "\n";
    }

    return 0;
}