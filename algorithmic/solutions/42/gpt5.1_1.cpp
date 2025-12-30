#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long double rt = sqrt((long double)n);
    long long k = (long long)rt;
    if (k * k < n) ++k;

    cout.setf(ios::fixed);
    cout << setprecision(6);
    cout << (double)k << "\n";

    long long cnt = 0;
    for (long long y = 0; y < k && cnt < n; ++y) {
        for (long long x = 0; x < k && cnt < n; ++x) {
            double cx = x + 0.5;
            double cy = y + 0.5;
            double angle = 0.0;
            cout << cx << " " << cy << " " << angle << "\n";
            ++cnt;
        }
    }

    return 0;
}