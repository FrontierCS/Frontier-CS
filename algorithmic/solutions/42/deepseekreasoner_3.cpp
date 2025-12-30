#include <iostream>
#include <cmath>
#include <iomanip>

using namespace std;

int main() {
    int n;
    cin >> n;
    double L = ceil(sqrt(n));
    int k = (int)L;
    cout << fixed << setprecision(6) << L << endl;
    for (int i = 0; i < n; ++i) {
        int row = i / k;
        int col = i % k;
        double x = col + 0.5;
        double y = row + 0.5;
        double angle = 0.0;
        cout << fixed << setprecision(6) << x << " " << y << " " << angle << endl;
    }
    return 0;
}