#include <iostream>
#include <iomanip>
#include <cmath>

using namespace std;

int main() {
    int n;
    cin >> n;
    int m = (int)sqrt(n);
    if (m * m < n) m++;
    double L = m;
    cout << fixed << setprecision(6) << L << endl;
    for (int i = 0; i < n; ++i) {
        int row = i / m;
        int col = i % m;
        double x = col + 0.5;
        double y = row + 0.5;
        cout << x << " " << y << " 0.000000" << endl;
    }
    return 0;
}