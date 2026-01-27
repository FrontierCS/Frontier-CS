#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    while (d > 0) {
        int bad1 = -1, bad2 = -1;
        bool progressed = false;

        for (int c = 0; c < 3; ++c) {
            if (c == bad1 || c == bad2) continue;

            cout << "move " << c << endl;
            cout.flush();
            int reach;
            if (!(cin >> reach)) return 0;
            if (reach == 1) return 0;

            cout << "query" << endl;
            cout.flush();
            int d2;
            if (!(cin >> d2)) return 0;

            if (d2 == d - 1) {
                d = d2;
                progressed = true;
                break;
            } else if (d2 == d + 1) {
                // Move back
                cout << "move " << c << endl;
                cout.flush();
                int back;
                if (!(cin >> back)) return 0;
                if (back == 1) return 0; // should not happen

                if (bad1 == -1) bad1 = c;
                else bad2 = c;

                if (bad1 != -1 && bad2 != -1) {
                    int last = 3 - bad1 - bad2;
                    cout << "move " << last << endl;
                    cout.flush();
                    int reach2;
                    if (!(cin >> reach2)) return 0;
                    if (reach2 == 1) return 0;
                    d--; // moved towards exit
                    progressed = true;
                    break;
                }
            } else {
                // Unexpected; adjust and continue
                d = d2;
                progressed = true;
                break;
            }
        }

        if (!progressed) break; // Safety, though should not occur
    }

    return 0;
}