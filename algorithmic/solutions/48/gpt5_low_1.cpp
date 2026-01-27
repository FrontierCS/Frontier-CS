#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;

    // Balanced cubic grid: a x b x c with a*b*c >= n and a, b as small as possible (near cubic)
    long long a = ceil(cbrt((long double)n));
    long long b = a;
    long long c = (n + a*b - 1) / (a*b); // ceil(n / (a*b))

    cout.setf(std::ios::fixed);
    cout << setprecision(12);

    long long count = 0;
    for (long long k = 0; k < c && count < n; ++k) {
        for (long long j = 0; j < b && count < n; ++j) {
            for (long long i = 0; i < a && count < n; ++i) {
                double x = (i + 0.5) / (double)a;
                double y = (j + 0.5) / (double)b;
                double z = (k + 0.5) / (double)c;
                cout << x << " " << y << " " << z << "\n";
                ++count;
            }
        }
    }
    return 0;
}