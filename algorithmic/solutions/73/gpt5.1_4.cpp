#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2005;

static unsigned char S[MAXN][MAXN];
static unsigned char Xinv[MAXN][MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n <= 0) return 0;

    // Query all intervals [l, r] with l < r
    for (int l = 1; l <= n; ++l) {
        for (int r = l + 1; r <= n; ++r) {
            cout << 0 << " " << l << " " << r << endl;
            int res;
            if (!(cin >> res)) return 0;
            if (res < 0) return 0; // in case of interactor error
            S[l][r] = static_cast<unsigned char>(res & 1);
        }
    }

    // Recover pairwise inversion bits Xinv[i][j] = [p_i > p_j] for i < j
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            if (j == i + 1) {
                Xinv[i][j] = S[i][j];
            } else {
                int s1 = S[i][j];
                int s2 = S[i + 1][j];
                int s3 = S[i][j - 1];
                int s4 = S[i + 1][j - 1]; // 0 on diagonal, or queried if i+1 < j-1
                Xinv[i][j] = static_cast<unsigned char>(s1 ^ s2 ^ s3 ^ s4);
            }
        }
    }

    // Reconstruct permutation values
    vector<int> p(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        int cntSmaller = 0;
        for (int j = 1; j <= n; ++j) {
            if (j == i) continue;
            if (i < j) {
                if (Xinv[i][j]) ++cntSmaller; // p_i > p_j
            } else { // i > j
                if (!Xinv[j][i]) ++cntSmaller; // p_i > p_j if not (p_j > p_i)
            }
        }
        p[i] = cntSmaller + 1;
    }

    cout << 1;
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;

    return 0;
}