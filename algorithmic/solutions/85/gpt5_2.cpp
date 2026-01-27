#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    vector<int> colors = {0, 1, 2};

    while (true) {
        bool movedToParent = false;
        for (int c : colors) {
            cout << "move " << c << endl;
            cout.flush();
            int r;
            if (!(cin >> r)) return 0;
            if (r == 1) return 0;

            cout << "query" << endl;
            cout.flush();
            int d2;
            if (!(cin >> d2)) return 0;

            if (d2 == d - 1) {
                d = d2;
                movedToParent = true;
                break;
            } else {
                cout << "move " << c << endl;
                cout.flush();
                if (!(cin >> r)) return 0;
            }
        }

        if (!movedToParent) {
            cout << "query" << endl;
            cout.flush();
            if (!(cin >> d)) return 0;
            if (d == 0) return 0;
        }
    }

    return 0;
}