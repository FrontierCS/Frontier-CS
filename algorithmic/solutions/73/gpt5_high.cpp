#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<unsigned char>> inv(n + 2, vector<unsigned char>(n + 2, 0));

    // Query all intervals of length >= 2
    for (int l = 1; l <= n; ++l) {
        for (int r = l + 1; r <= n; ++r) {
            cout << "0 " << l << " " << r << endl;
            int x;
            if (!(cin >> x)) return 0;
            if (x < 0) return 0;
            inv[l][r] = (unsigned char)(x & 1);
        }
    }

    auto getInv = [&](int l, int r) -> unsigned char {
        if (l >= r) return 0;
        return inv[l][r];
    };

    // Precompute pairwise comparisons: gt[i][j] = [p_i > p_j] for i < j
    vector<vector<unsigned char>> gt(n + 2, vector<unsigned char>(n + 2, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            unsigned char v = getInv(i, j) ^ getInv(i + 1, j) ^ getInv(i, j - 1) ^ getInv(i + 1, j - 1);
            gt[i][j] = v;
        }
    }

    vector<int> p(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        int lessCnt = 0;
        for (int j = 1; j < i; ++j) {
            // gt[j][i] = [p_j > p_i], so if it's 0, p_j < p_i
            if (gt[j][i] == 0) ++lessCnt;
        }
        for (int j = i + 1; j <= n; ++j) {
            // gt[i][j] = [p_i > p_j]
            if (gt[i][j]) ++lessCnt;
        }
        p[i] = lessCnt + 1;
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;
    return 0;
}