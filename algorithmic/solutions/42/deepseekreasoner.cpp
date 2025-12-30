#include <iostream>
#include <cmath>
#include <iomanip>

using namespace std;

int main() {
    int n;
    cin >> n;
    int L = ceil(sqrt(n));
    cout << fixed << setprecision(6) << (double)L << "\n";
    for (int i = 0; i < n; ++i) {
        int row = i / L;
        int col = i % L;
        double x = col + 0.5;
        double y = row + 0.5;
        cout << x << " " << y << " " << 0.0 << "\n";
    }
    return 0;
}