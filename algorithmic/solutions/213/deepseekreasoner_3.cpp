#include <iostream>
#include <vector>
#include <tuple>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }
    int x = 2;
    vector<tuple<int, int, int>> ops;
    // Bubble sort using adjacent swaps (shift left on segments of length 2)
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n - 1 - i; ++j) {
            if (a[j] > a[j+1]) {
                // swap a[j] and a[j+1] with a left shift on [j, j+1]
                ops.push_back({j+1, j+2, 0});
                swap(a[j], a[j+1]);
            }
        }
    }
    int m = ops.size();
    cout << x << " " << m << "\n";
    for (auto [l, r, d] : ops) {
        cout << l << " " << r << " " << d << "\n";
    }
    return 0;
}