#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    int cols = ceil(sqrt(n));
    int rows = ceil((double)n / cols);
    double L = cols; // cols >= rows always holds
    cout << fixed << setprecision(6) << L << endl;
    for (int i = 0; i < n; ++i) {
        int x = i % cols;
        int y = i / cols;
        double cx = x + 0.5;
        double cy = y + 0.5;
        cout << fixed << setprecision(6) << cx << " " << cy << " " << 0.0 << endl;
    }
    return 0;
}