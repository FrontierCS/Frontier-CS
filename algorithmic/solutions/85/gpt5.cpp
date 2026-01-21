#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto do_move = [&](int c)->int{
        cout << "move " << c << endl;
        cout.flush();
        int res;
        if(!(cin >> res)) exit(0);
        return res;
    };
    auto do_query = [&]()->int{
        cout << "query" << endl;
        cout.flush();
        int res;
        if(!(cin >> res)) exit(0);
        return res;
    };

    int d;
    if(!(cin >> d)) return 0;
    if(d == 0) return 0;

    int prev = -1;

    while (d > 0) {
        if (prev == -1) {
            // Initial step: try colors 0,1,2 until we find the one that decreases distance
            for (int c = 0; c < 3; ++c) {
                int mv = do_move(c);
                if (mv == 1) return 0; // reached exit
                int nd = do_query();
                if (nd < d) {
                    d = nd;
                    prev = c;
                    break;
                } else {
                    do_move(c); // move back
                }
            }
        } else {
            int c1 = (prev + 1) % 3;
            int c2 = (prev + 2) % 3;

            int mv1 = do_move(c1);
            if (mv1 == 1) return 0; // reached exit

            int nd = do_query();
            if (nd < d) {
                d = nd;
                prev = c1;
            } else {
                do_move(c1); // back to current
                int mv2 = do_move(c2);
                if (mv2 == 1) return 0; // reached exit
                // This move must be correct (towards exit)
                d -= 1;
                prev = c2;
            }
        }
    }

    return 0;
}