#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int cur_d;
    cin >> cur_d;
    while (cur_d > 0) {
        // Try color 0
        cout << "move 0" << endl;
        cout.flush();
        int r;
        cin >> r;
        if (r == 1) return 0;
        cout << "query" << endl;
        cout.flush();
        int new_d;
        cin >> new_d;
        bool good = (new_d == cur_d - 1);
        if (good) {
            cur_d = new_d;
            continue;
        } else {
            cout << "move 0" << endl;
            cout.flush();
            int r2;
            cin >> r2;
        }
        // Try color 1
        cout << "move 1" << endl;
        cout.flush();
        cin >> r;
        if (r == 1) return 0;
        cout << "query" << endl;
        cout.flush();
        cin >> new_d;
        good = (new_d == cur_d - 1);
        if (good) {
            cur_d = new_d;
            continue;
        } else {
            cout << "move 1" << endl;
            cout.flush();
            int r22;
            cin >> r22;
        }
        // Try color 2, no query
        cout << "move 2" << endl;
        cout.flush();
        int r3;
        cin >> r3;
        if (r3 == 1) return 0;
        // Assume success
        cur_d--;
    }
    return 0;
}