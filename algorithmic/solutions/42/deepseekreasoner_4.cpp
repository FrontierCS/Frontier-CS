#include <iostream>
#include <iomanip>

using namespace std;

int main() {
    int n;
    cin >> n;
    int k = 0;
    while (k * k < n) ++k;
    double L = k;
    cout << fixed << setprecision(6) << L << endl;
    for (int i = 0; i < n; ++i) {
        int row = i / k;
        int col = i % k;
        double x = col + 0.5;
        double y = row + 0.5;
        cout << x << " " << y << " " << 0.0 << endl;
    }
    return 0;
}