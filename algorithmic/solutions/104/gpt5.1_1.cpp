#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;

        // First guess: student 1
        cout << "! 1\n";
        cout.flush();
        int y1;
        if (!(cin >> y1)) return 0;
        if (y1 == 1) {
            cout << "#\n";
            cout.flush();
            continue;
        }

        // Second guess: student 2
        cout << "! 2\n";
        cout.flush();
        int y2;
        if (!(cin >> y2)) return 0;

        cout << "#\n";
        cout.flush();
    }
    return 0;
}