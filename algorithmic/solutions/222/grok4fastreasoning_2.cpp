#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    const int BS = 1000;
    const long long GS = BS + 1LL;
    const long long MAX_STEPS = 2000000LL;
    for (int graph = 0; graph < n; ++graph) {
        cout << "? 1 1" << endl;
        int c;
        cin >> c;
        map<int, int> pos_to_k;
        pos_to_k[c] = 0;
        int s = -1;
        bool small_found = false;
        for (int k = 1; k <= BS; ++k) {
            long long steps = k;
            cout << "? " << c << " " << steps << endl;
            int p;
            cin >> p;
            if (p == c) {
                s = k;
                small_found = true;
                break;
            }
            pos_to_k[p] = k;
        }
        if (small_found) {
            cout << "! " << s << endl;
            int ver;
            cin >> ver;
            if (ver == -1) return 0;
            continue;
        }
        // giants
        bool giant_found = false;
        for (int m = 1; m <= 2000; ++m) {  // safe upper limit
            long long steps = (long long)m * GS;
            if (steps > MAX_STEPS) break;
            cout << "? " << c << " " << steps << endl;
            int p;
            cin >> p;
            auto it = pos_to_k.find(p);
            if (it != pos_to_k.end()) {
                int r = it->second;
                s = steps - r;
                cout << "! " << s << endl;
                int ver;
                cin >> ver;
                if (ver == -1) return 0;
                giant_found = true;
                break;
            }
        }
        if (!giant_found) {
            // Should not happen
            return 0;
        }
    }
    return 0;
}