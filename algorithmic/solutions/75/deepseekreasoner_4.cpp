#include <iostream>
#include <algorithm>
using namespace std;

int main() {
    int b, w, x, y;
    cin >> b >> w >> x >> y;
    int w_top = w - 1;
    int b_bot = b - 1;
    int C = max(2 * w_top + 1, 2 * b_bot + 1);
    int r = 4;
    cout << r << " " << C << "\n";
    // row1
    for (int i = 0; i < C; ++i) {
        if (i % 2 == 1 && i < 2 * w_top) cout << '.';
        else cout << '@';
    }
    cout << "\n";
    // row2
    for (int i = 0; i < C; ++i) cout << '@';
    cout << "\n";
    // row3
    for (int i = 0; i < C; ++i) cout << '.';
    cout << "\n";
    // row4
    for (int i = 0; i < C; ++i) {
        if (i % 2 == 1 && i < 2 * b_bot) cout << '@';
        else cout << '.';
    }
    cout << "\n";
    return 0;
}