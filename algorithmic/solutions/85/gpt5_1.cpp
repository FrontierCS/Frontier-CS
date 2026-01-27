#include <bits/stdc++.h>
using namespace std;

static inline bool do_move(int c) {
    cout << "move " << c << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res == 1;
}

static inline int do_query() {
    cout << "query" << endl;
    cout.flush();
    int d;
    if (!(cin >> d)) exit(0);
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int D;
    if (!(cin >> D)) return 0;
    if (D == 0) return 0;

    int prev_color = -1;

    while (D > 0) {
        vector<int> choices;
        for (int c = 0; c < 3; ++c) if (c != prev_color) choices.push_back(c);

        bool progressed = false;

        for (int attempt = 0; attempt < (int)choices.size() - 1; ++attempt) {
            int c = choices[attempt];
            if (do_move(c)) return 0; // reached exit
            int newD = do_query();
            if (newD == D - 1) {
                D = newD;
                prev_color = c;
                progressed = true;
                break;
            } else {
                // must be D + 1, go back
                if (do_move(c)) return 0; // should not happen
                // D remains unchanged
            }
        }

        if (!progressed) {
            int c = choices.back();
            if (do_move(c)) return 0; // reached exit
            --D;
            prev_color = c;
        }
    }

    return 0;
}