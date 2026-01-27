#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;

    long long Lint = ceil(sqrt((long double)n));
    double L = (double)Lint;

    cout.setf(std::ios::fixed);
    cout << setprecision(6) << L << "\n";

    long long cnt = 0;
    for (long long y = 0; y < Lint && cnt < n; ++y) {
        for (long long x = 0; x < Lint && cnt < n; ++x) {
            double cx = x + 0.5;
            double cy = y + 0.5;
            double a = 0.0;
            cout << setprecision(6) << cx << " " << cy << " " << a << "\n";
            ++cnt;
        }
    }

    return 0;
}