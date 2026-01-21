#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "1 1" << endl;
        return 0;
    }

    vector<vector<unsigned char>> inv(n + 2, vector<unsigned char>(n + 2, 0));

    // Query all intervals of length >= 2
    for (int l = 1; l <= n - 1; ++l) {
        for (int r = l + 1; r <= n; ++r) {
            cout << "0 " << l << " " << r << endl;
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0; // in case of interactor error
            inv[l][r] = (unsigned char)(ans & 1);
        }
    }

    vector<int> lessCnt(n + 1, 0);

    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            int w;
            if (j == i + 1) {
                // Adjacent pair: inversion parity directly gives comparison
                w = inv[i][j];
            } else {
                int a = inv[i][j];
                int b = inv[i + 1][j];
                int c = inv[i][j - 1];
                int d = 0;
                if (j > i + 2) d = inv[i + 1][j - 1];
                w = a ^ b ^ c ^ d;
            }

            if (w) {
                // pi > pj
                lessCnt[i]++;
            } else {
                // pi < pj
                lessCnt[j]++;
            }
        }
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << (lessCnt[i] + 1);
    }
    cout << endl;

    return 0;
}