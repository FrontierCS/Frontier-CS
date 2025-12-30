#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    vector<int> I(M), J(M);
    for (int k = 0; k < M; k++) {
        cin >> I[k] >> J[k];
    }
    for (int k = 0; k < M - 1; k++) {
        int ci = I[k], cj = J[k];
        int ti = I[k + 1], tj = J[k + 1];
        int dx = ti - ci;
        int dy = tj - cj;

        // Vertical first: change row to ti, keep column cj
        char vdir;
        bool vslide = false;
        if (dx < 0) {
            vdir = 'U';
            if (ti == 0) vslide = true;
        } else if (dx > 0) {
            vdir = 'D';
            if (ti == N - 1) vslide = true;
        }
        if (dx != 0) {
            if (vslide) {
                cout << "S " << vdir << endl;
            } else {
                int steps = abs(dx);
                for (int s = 0; s < steps; s++) {
                    cout << "M " << vdir << endl;
                }
            }
        }

        // Now horizontal: change column to tj, keep row ti
        char hdir;
        bool hslide = false;
        if (dy < 0) {
            hdir = 'L';
            if (tj == 0) hslide = true;
        } else if (dy > 0) {
            hdir = 'R';
            if (tj == N - 1) hslide = true;
        }
        if (dy != 0) {
            if (hslide) {
                cout << "S " << hdir << endl;
            } else {
                int steps = abs(dy);
                for (int s = 0; s < steps; s++) {
                    cout << "M " << hdir << endl;
                }
            }
        }
    }
    return 0;
}