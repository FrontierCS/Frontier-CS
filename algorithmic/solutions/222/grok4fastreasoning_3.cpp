#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    for (int test = 0; test < n; ++test) {
        cout << "? 1 1" << endl;
        cout.flush();
        int u;
        cin >> u;
        map<int, int> baby;
        baby[u] = 0;
        const int MM = 501;
        bool found = false;
        for (int k = 1; k <= MM; ++k) {
            long long xx = k;
            cout << "? " << u << " " << xx << endl;
            cout.flush();
            int pos;
            cin >> pos;
            auto it = baby.find(pos);
            if (it != baby.end()) {
                int j = it->second;
                long long cand = (long long)k - j;
                if (cand >= 3) {
                    cout << "! " << cand << endl;
                    cout.flush();
                    int ver;
                    cin >> ver;
                    if (ver == -1) {
                        return 0;
                    }
                    found = true;
                    break;
                }
            }
            if (!found) {
                baby[pos] = k;
            }
        }
        if (!found) {
            long long cur_i = 1;
            while (true) {
                long long steps = cur_i * (long long)MM;
                cout << "? " << u << " " << steps << endl;
                cout.flush();
                int pos;
                cin >> pos;
                auto it = baby.find(pos);
                if (it != baby.end()) {
                    int j = it->second;
                    long long cand = steps - j;
                    cout << "! " << cand << endl;
                    cout.flush();
                    int ver;
                    cin >> ver;
                    if (ver == -1) {
                        return 0;
                    }
                    found = true;
                    break;
                }
                ++cur_i;
            }
        }
    }
    return 0;
}