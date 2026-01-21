#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<unsigned char>> F(n + 1, vector<unsigned char>(n + 1, 0));

    // Query all intervals [l, r] with l < r
    for (int r = 2; r <= n; ++r) {
        for (int l = 1; l < r; ++l) {
            cout << "0 " << l << " " << r << endl;
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans < 0) return 0;
            F[l][r] = (unsigned char)(ans & 1);
        }
    }

    // greater[i][j] = 1 iff p_i > p_j for i < j
    vector<vector<unsigned char>> greater(n + 1, vector<unsigned char>(n + 1, 0));

    // Reconstruct pairwise comparisons
    for (int r = 2; r <= n; ++r) {
        vector<unsigned char> s(r);
        for (int l = 1; l <= r - 1; ++l) {
            s[l] = F[l][r] ^ F[l][r - 1];
        }
        unsigned char suff = 0;
        for (int j = r - 1; j >= 1; --j) {
            unsigned char x = s[j] ^ suff;
            greater[j][r] = x;
            suff ^= x;
        }
    }

    // Compute permutation values
    vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) {
        int cnt_less = 0;
        for (int j = 1; j <= n; ++j) {
            if (j == i) continue;
            if (j < i) {
                cnt_less += 1 - greater[j][i];
            } else {
                cnt_less += greater[i][j];
            }
        }
        p[i] = cnt_less + 1;
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}