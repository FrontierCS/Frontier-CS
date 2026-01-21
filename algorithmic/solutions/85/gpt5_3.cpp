#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    auto move_op = [&](int c)->int {
        cout << "move " << c << endl;
        cout.flush();
        int res;
        if (!(cin >> res)) exit(0);
        return res;
    };

    auto query_op = [&]()->int {
        cout << "query" << endl;
        cout.flush();
        int res;
        if (!(cin >> res)) exit(0);
        return res;
    };

    int back_color = -1; // color of the edge back to the previous node
    bool tried[3] = {false, false, false}; // tried candidate colors at current node (excluding back_color)

    while (d > 0) {
        int cand = -1;
        for (int c = 0; c < 3; ++c) {
            if (c != back_color && !tried[c]) {
                cand = c;
                break;
            }
        }
        if (cand == -1) {
            // Should not happen; choose any color not equal to back_color
            for (int c = 0; c < 3; ++c) {
                if (c != back_color) { cand = c; break; }
            }
        }

        int ret = move_op(cand);
        if (ret == 1) return 0;

        int nd = query_op();
        if (nd == d - 1) {
            // Moved towards exit
            d = nd;
            back_color = cand;
            tried[0] = tried[1] = tried[2] = false;
            continue;
        } else {
            // Moved away (to a child)
            move_op(cand); // move back
            tried[cand] = true;

            int untestedCount = 0, rest = -1;
            for (int c = 0; c < 3; ++c) {
                if (c != back_color && !tried[c]) {
                    ++untestedCount;
                    rest = c;
                }
            }
            if (untestedCount == 1) {
                int ret2 = move_op(rest);
                if (ret2 == 1) return 0;
                // We moved to parent without querying
                --d;
                back_color = rest;
                tried[0] = tried[1] = tried[2] = false;
                continue;
            } else {
                // Need to test another candidate (initial step case)
                continue;
            }
        }
    }

    return 0;
}