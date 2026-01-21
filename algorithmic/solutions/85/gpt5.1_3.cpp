#include <bits/stdc++.h>
using namespace std;

int move_color(int c) {
    cout << "move " << c << endl;
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int query_depth() {
    cout << "query" << endl;
    int d;
    if (!(cin >> d)) exit(0);
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int depth;
    if (!(cin >> depth)) return 0;
    if (depth == 0) return 0;  // already at exit

    while (true) {
        for (int c = 0; c < 3; ++c) {
            int isExit = move_color(c);
            if (isExit == 1) {
                return 0;  // reached exit
            }

            int newDepth = query_depth();

            if (newDepth == depth - 1) {
                // Moved towards exit
                depth = newDepth;
                break;
            } else {
                // Must have moved away: go back
                isExit = move_color(c);
                if (isExit == 1) {
                    // Should not happen, but exit safely if it does
                    return 0;
                }
                // Back to previous node; depth unchanged
            }
        }
    }

    return 0;
}