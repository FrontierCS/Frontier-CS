#include <bits/stdc++.h>
using namespace std;

int main() {
    int cur_depth;
    cin >> cur_depth;
    while (cur_depth > 0) {
        for (int c = 0; c < 3; ++c) {
            cout << "move " << c << endl;
            cout.flush();
            int res;
            cin >> res;
            if (res == 1) {
                return 0;
            }
            cout << "query" << endl;
            cout.flush();
            int nd;
            cin >> nd;
            if (nd == cur_depth - 1) {
                cur_depth = nd;
                break;
            } else {
                cout << "move " << c << endl;
                cout.flush();
                int res2;
                cin >> res2;
            }
        }
    }
    return 0;
}