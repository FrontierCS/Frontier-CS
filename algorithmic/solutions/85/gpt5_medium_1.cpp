#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int D;
    if (!(cin >> D)) return 0;
    if (D == 0) return 0;

    while (D > 0) {
        for (int c = 0; c < 3; ++c) {
            cout << "move " << c << endl;
            cout.flush();
            int reached;
            if (!(cin >> reached)) return 0;
            if (reached == 1) return 0;

            cout << "query" << endl;
            cout.flush();
            int D2;
            if (!(cin >> D2)) return 0;

            if (D2 == D - 1) {
                D = D2;
                break;
            } else {
                // Go back along the same edge
                cout << "move " << c << endl;
                cout.flush();
                if (!(cin >> reached)) return 0;
                if (reached == 1) return 0; // should not happen here
            }
        }
    }

    return 0;
}