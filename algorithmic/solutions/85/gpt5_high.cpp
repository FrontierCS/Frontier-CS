#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    int lastColor = -1; // color of the edge leading back to the child we came from
    while (d > 0) {
        // Prepare candidate colors excluding the one leading back
        vector<int> cand;
        for (int c = 0; c < 3; ++c) if (c != lastColor) cand.push_back(c);

        bool movedUp = false;
        int tested1 = -1, tested2 = -1;

        // Test up to two candidates
        for (int idx = 0; idx < 2 && !movedUp; ++idx) {
            int c = cand[idx];
            if (idx == 0) tested1 = c;
            else tested2 = c;

            cout << "move " << c << endl;
            int ok;
            if (!(cin >> ok)) return 0;
            if (ok == 1) return 0; // reached exit

            cout << "query" << endl;
            cout.flush();
            int d2;
            if (!(cin >> d2)) return 0;

            if (d2 == d - 1) {
                // moved to parent
                d = d2;
                lastColor = c;
                movedUp = true;
            } else {
                // moved to child, go back
                cout << "move " << c << endl;
                if (!(cin >> ok)) return 0;
                if (ok == 1) return 0; // should not happen here
            }
        }

        if (!movedUp) {
            // The remaining color must be the parent
            int c3 = 0;
            while (c3 == lastColor || c3 == tested1 || c3 == tested2) ++c3;
            cout << "move " << c3 << endl;
            int ok;
            if (!(cin >> ok)) return 0;
            if (ok == 1) return 0; // reached exit
            d -= 1;
            lastColor = c3;
        }
    }

    return 0;
}