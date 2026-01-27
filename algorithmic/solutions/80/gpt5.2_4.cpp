#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;

    string s;
    while (cin >> s) {
        if (s == "treasure") return 0;

        if (s == "center") {
            // Initialize a new chamber: mark some passage and take it.
            cout << 0 << " left " << 0 << endl;
        } else {
            // Rotor-router: advance the marker by 1 and take that passage.
            // (taking the same passage we move the stone to)
            cout << 1 << " left " << 1 << endl;
        }
    }
    return 0;
}