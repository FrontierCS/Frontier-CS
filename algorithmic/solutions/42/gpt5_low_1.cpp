#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if (!(cin >> n)) return 0;
    long long m = ceil(sqrt((long double)n));
    cout.setf(std::ios::fixed); cout << setprecision(6);
    cout << (double)m << "\n";
    long long printed = 0;
    for (long long y = 0; y < m && printed < n; ++y) {
        for (long long x = 0; x < m && printed < n; ++x) {
            double cx = 0.5 + x;
            double cy = 0.5 + y;
            double a = 0.0;
            cout << cx << " " << cy << " " << a << "\n";
            ++printed;
        }
    }
    return 0;
}