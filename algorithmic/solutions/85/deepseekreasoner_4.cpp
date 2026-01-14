#include <iostream>
#include <cstdlib>
using namespace std;

int main() {
    int d;
    cin >> d; // initial distance
    if (d == 0) {
        return 0; // already at exit
    }

    int cur_d = d;

    while (true) {
        bool found = false;
        // test the first two colors (0 and 1)
        for (int c = 0; c <= 1; ++c) {
            cout << "move " << c << endl;
            cout.flush();
            int res;
            cin >> res;
            if (res == 1) {
                return 0; // reached exit
            }

            cout << "query" << endl;
            cout.flush();
            int new_d;
            cin >> new_d;
            if (new_d == 0) {
                return 0; // reached exit
            }

            if (new_d == cur_d - 1) {
                // moving towards exit
                cur_d = new_d;
                found = true;
                break;
            } else if (new_d == cur_d + 1) {
                // moving away, move back
                cout << "move " << c << endl;
                cout.flush();
                cin >> res;
                if (res == 1) {
                    return 0; // should not happen, but safe
                }
                // now back at original node, distance unchanged
            } else {
                // unexpected response, abort (should not occur)
                return 1;
            }
        }

        if (found) {
            continue;
        }

        // third color (2) must be correct
        int c = 2;
        cout << "move " << c << endl;
        cout.flush();
        int res;
        cin >> res;
        if (res == 1) {
            return 0;
        }

        if (cur_d == 1) {
            // we were one step away, so moving should have reached exit
            // but move returned 0, so query to confirm
            cout << "query" << endl;
            cout.flush();
            int new_d;
            cin >> new_d;
            if (new_d == 0) {
                return 0;
            }
            // unexpected
            return 1;
        } else {
            cur_d -= 1; // we assume we moved closer without querying
        }
    }

    return 0;
}